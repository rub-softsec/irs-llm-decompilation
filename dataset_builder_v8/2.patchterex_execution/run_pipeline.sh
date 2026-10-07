#!/bin/bash

# Configuration
# Point to inputs from previous steps
BINARY_INPUT="../0.extract_raw_functions/d8"  # Assuming d8 is in step 0 or can be found there
JSON_FILE="../1.get_usable_functions/map_usable.json"
MAX_PARALLEL=11
PYTHON_SCRIPT="patch_binary.py"
LOG_DIR="logs"
ERROR_LOG="execution_log.txt"

# Verify required files
if [ ! -f "$BINARY_INPUT" ]; then
    # Fallback to local if not found
    BINARY_INPUT="./d8"
    if [ ! -f "$BINARY_INPUT" ]; then
        echo "Error: Binary not found at $BINARY_INPUT"
        exit 1
    fi
fi

if [ ! -f "$JSON_FILE" ]; then
    # Fallback to local map
    JSON_FILE="./map_filtered_exists.json"
    if [ ! -f "$JSON_FILE" ]; then
        echo "Error: JSON file not found at $JSON_FILE"
        exit 1
    fi
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT not found"
    exit 1
fi

# Create output directories
mkdir -p "$LOG_DIR"
mkdir -p "output"

# Initialize log file
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat > "$ERROR_LOG" << EOF
# Binary Patching Log
# Generated: $START_TIME
# JSON File: $JSON_FILE
# Output Directory: output
#
# Format: STATUS|TYPE|ADDR|ADDR|TIMESTAMP|DETAILS
#
EOF

echo "=============================================================="
echo "Parallel Binary Patcher"
echo "=============================================================="
echo ""

# Read entries from JSON
echo "Loading entries from $JSON_FILE..."

# Check for valid JSON content
TOTAL=$(python3 -c "import json; data=json.load(open('$JSON_FILE')); print(len(data))" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$TOTAL" ] || [ "$TOTAL" -eq 0 ]; then
    echo "No valid entries found in $JSON_FILE or file is malformed"
    exit 1
fi

echo "Found $TOTAL entries"
echo ""
echo "Starting parallel processing with $MAX_PARALLEL workers..."
echo "=============================================================="

# Function to process a single entry
process_entry() {
    local index="$1"
    local error_log="$2"
    
    # Extract addr and name from JSON by index
    local addr=$(python3 -c "import json; data=json.load(open('$JSON_FILE')); print(data[$index]['addr'])")
    local name=$(python3 -c "import json; data=json.load(open('$JSON_FILE')); print(data[$index]['name'])")
    
    # Create individual log file
    local log_file="$LOG_DIR/${addr}.log"
    
    python3 "$PYTHON_SCRIPT" "$addr" "$name" "$BINARY_INPUT" "$error_log" > "$log_file" 2>&1
    local exit_code=$?
    
    echo "$exit_code|$addr|$name|$log_file"
}

export -f process_entry
export PYTHON_SCRIPT JSON_FILE BINARY_INPUT LOG_DIR ERROR_LOG

# Counters
SUCCESSFUL=0
FAILED=0
PROCESSED=0

# Create indices sequence
INDICES=$(seq 0 $((TOTAL - 1)))

# Process in parallel
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for processing"
    echo ""
    
    echo "$INDICES" | \
        parallel -j "$MAX_PARALLEL" --bar process_entry {} "$ERROR_LOG" | \
        while IFS='|' read -r exit_code addr name log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $addr ($name)"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $addr ($name) (see $log_file)"
            fi
        done
else
    echo "Using xargs for processing (install 'parallel' for progress bar)"
    echo ""
    
    echo "$INDICES" | \
        xargs -P "$MAX_PARALLEL" -I {} bash -c 'process_entry "$@"' _ {} "$ERROR_LOG" | \
        while IFS='|' read -r exit_code addr name log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $addr ($name)"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $addr ($name) (see $log_file)"
            fi
        done
fi

# Write summary to log
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat >> "$ERROR_LOG" << EOF
[SUMMARY]
Entries processed: $TOTAL
Entries patched successfully: $SUCCESSFUL
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
echo "Individual logs: $LOG_DIR/"

# Create marker file
touch done.txt

# Exit with error if any failures occurred
if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Some entries failed. Check logs for details."
    exit 1
fi

exit 0