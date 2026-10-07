#!/bin/bash

# Configuration
INPUT_DIR="input"
BINARY_INPUT="./d8"
JSON_FILE="./selected.json"
MAX_PARALLEL=11
PYTHON_SCRIPT="main.py"
LOG_DIR="logs"
ERROR_LOG="error.txt"

# Verify that necessary files exist
if [ ! -f "$BINARY_INPUT" ]; then
    echo "Error: Binary $BINARY_INPUT not found"
    exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file $JSON_FILE not found"
    exit 1
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT not found"
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input directory $INPUT_DIR not found"
    exit 1
fi

# Create log and output directories
mkdir -p "$LOG_DIR"
mkdir -p "output"

# Initialize error log file with header
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat > "$ERROR_LOG" << EOF
# Binary Patching Log
# Generated: $START_TIME
# Input Directory: $INPUT_DIR
# Output Directory: output
#
# Format: STATUS|TYPE|FILE|RELATIVE_PATH|TIMESTAMP|DETAILS
#
EOF

echo "=============================================================="
echo "Parallel Binary Patcher"
echo "=============================================================="
echo ""

# Search for all .c files
echo "Searching for .c files in $INPUT_DIR..."
mapfile -t C_FILES < <(find "$INPUT_DIR" -type f -name "*.c")

TOTAL=${#C_FILES[@]}

if [ $TOTAL -eq 0 ]; then
    echo "No .c files found in $INPUT_DIR"
    
    # Write to log
    END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
    cat >> "$ERROR_LOG" << EOF
[SUMMARY]
Files processed: 0
Files patched successfully: 0
Patching errors: 0
[END]
# Processing finished: $END_TIME
EOF
    # Create done.txt indicating completion
    touch done.txt
    exit 1
fi

echo "Found $TOTAL .c files"
echo ""

echo "Starting parallel processing with $MAX_PARALLEL workers..."
echo "=============================================================="

# Function to process a file
process_file() {
    local c_file="$1"
    local error_log="$2"
    
    # Create directory structure in logs keeping hierarchy
    local rel_path="${c_file#input/}"  # Removes 'input/' from start
    local log_dir="$LOG_DIR/$(dirname "$rel_path")"
    mkdir -p "$log_dir"
    local log_file="$log_dir/$(basename "$c_file" .c).log"
    
    python3 "$PYTHON_SCRIPT" "$c_file" "$JSON_FILE" "$BINARY_INPUT" "$error_log" > "$log_file" 2>&1
    local exit_code=$?
    
    echo "$exit_code|$c_file|$log_file"
}

export -f process_file
export PYTHON_SCRIPT JSON_FILE BINARY_INPUT LOG_DIR ERROR_LOG

# Counters
SUCCESSFUL=0
FAILED=0
PROCESSED=0

# Process files in parallel using GNU parallel if available
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for processing"
    echo ""
    
    # Use GNU parallel
    printf '%s\n' "${C_FILES[@]}" | \
        parallel -j "$MAX_PARALLEL" --bar process_file {} "$ERROR_LOG" | \
        while IFS='|' read -r exit_code c_file log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $(basename "$c_file")"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $(basename "$c_file") (see $log_file)"
            fi
        done
else
    echo "Using xargs for processing (install 'parallel' for better progress)"
    echo ""
    
    # Fallback to xargs
    printf '%s\n' "${C_FILES[@]}" | \
        xargs -P "$MAX_PARALLEL" -I {} bash -c 'process_file "$@"' _ {} "$ERROR_LOG" | \
        while IFS='|' read -r exit_code c_file log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $(basename "$c_file")"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $(basename "$c_file") (see $log_file)"
            fi
        done
fi

# Write final summary to log
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat >> "$ERROR_LOG" << EOF
[SUMMARY]
Files processed: $TOTAL
Files patched successfully: $SUCCESSFUL
Patching errors: $FAILED
[END]
# Processing finished: $END_TIME
EOF

echo ""
echo "=============================================================="
echo "Processing complete!"
echo "Successful: $SUCCESSFUL"
echo "Failed: $FAILED"
echo "Total: $TOTAL"
echo "=============================================================="
echo ""
echo "Detailed log: $ERROR_LOG"
echo "Individual logs: $LOG_DIR/ (maintains same hierarchy as input/)"

# Create done.txt marker file indicating process has finished
touch done.txt
echo "Created done.txt marker file"

# Exit with error code if there were failures
if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Some files failed. Check $ERROR_LOG and logs in $LOG_DIR/ for details"
    exit 1
fi

exit 0