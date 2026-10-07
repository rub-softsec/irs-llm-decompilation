#!/bin/bash

# Configuration
INPUT_DIR="input"
V8_ZIP="./v8_dir.zip"
MAX_PARALLEL=3
LOG_DIR="logs"
ERROR_LOG="error.txt"

# Verify required files exist
if [ ! -f "$V8_ZIP" ]; then
    echo "Error: V8 zip file $V8_ZIP not found"
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input directory $INPUT_DIR not found"
    exit 1
fi

# Create output and logs directories
mkdir -p "$LOG_DIR"
mkdir -p "output"

# Initialize error log with header
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat > "$ERROR_LOG" << EOF
# V8 Testing Log
# Generated: $START_TIME
# Input Directory: $INPUT_DIR
# Output Directory: output
#
# Format: STATUS|PHASE|FILE|RELATIVE_PATH|TIMESTAMP|ERROR_DETAILS
#
EOF

echo "=============================================================="
echo "V8 Parallel Testing Suite"
echo "=============================================================="
echo ""

# Find all binary files (regular files, not directories)
echo "Searching for binary files in $INPUT_DIR..."
mapfile -t BINARY_FILES < <(find "$INPUT_DIR" -type f)

TOTAL=${#BINARY_FILES[@]}

if [ $TOTAL -eq 0 ]; then
    echo "No binary files found in $INPUT_DIR"
    
    # Write to log
    END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
    cat >> "$ERROR_LOG" << EOF
[SUMMARY]
Files processed: 0
Files tested successfully: 0
Testing errors: 0
[END]
# Processing finished: $END_TIME
EOF
    # Create done.txt marker
    touch done.txt
    exit 1
fi

echo "Found $TOTAL binary files"
echo ""

echo "Starting parallel processing with $MAX_PARALLEL workers..."
echo "=============================================================="

# Function to process a binary file
process_binary() {
    local binary_file="$1"
    local error_log="$2"
    local v8_zip="$3"
    
    # Get relative path and create output structure
    local rel_path="${binary_file#input/}"  # Remove 'input/' from beginning
    local bin_name=$(basename "$binary_file")
    local dir_path=$(dirname "$rel_path")
    
    # Create log and output directories maintaining hierarchy
    local log_dir_create="$LOG_DIR/$dir_path"
    local output_dir="output/$dir_path"
    mkdir -p "$log_dir_create"
    mkdir -p "$output_dir"

    local current_dir_log_dir=$(pwd)
    local log_dir="$current_dir_log_dir/$log_dir_create"
    
    local log_file="$log_dir/${bin_name}.log"
    local output_file="$output_dir/${bin_name}.out"
    
    # Start logging
    echo "Processing: $binary_file" > "$log_file"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%6N")" >> "$log_file"
    echo "============================================" >> "$log_file"
    
    # Create temporary directory
    local tmp_dir=$(mktemp -d)
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|TMPDIR_CREATION|$bin_name|$rel_path|$timestamp|Failed to create temporary directory" >> "$error_log"
        echo "FAILED: Could not create temporary directory" >> "$log_file"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Created temporary directory: $tmp_dir" >> "$log_file"
    
    # Copy v8_dir.zip to temporary directory
    cp "$v8_zip" "$tmp_dir/" 2>> "$log_file"
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|ZIP_COPY|$bin_name|$rel_path|$timestamp|Failed to copy v8_dir.zip to temporary directory" >> "$error_log"
        echo "FAILED: Could not copy v8_dir.zip" >> "$log_file"
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Copied v8_dir.zip to temporary directory" >> "$log_file"
    
    # Unzip v8_dir.zip
    cd "$tmp_dir"
    unzip -q v8_dir.zip >> "$log_file" 2>&1
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|UNZIP|$bin_name|$rel_path|$timestamp|Failed to unzip v8_dir.zip" >> "$error_log"
        echo "FAILED: Could not unzip v8_dir.zip" >> "$log_file"
        cd - > /dev/null
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Unzipped v8_dir.zip successfully" >> "$log_file"
    cd - > /dev/null
    
    # Copy binary to v8/out/x64.release/d8
    local d8_path="$tmp_dir/v8_dir/v8/out/x64.release/d8"
    cp "$binary_file" "$d8_path" 2>> "$log_file"
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|BINARY_COPY|$bin_name|$rel_path|$timestamp|Failed to copy binary to $d8_path" >> "$error_log"
        echo "FAILED: Could not copy binary to d8 location" >> "$log_file"
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Copied binary to $d8_path" >> "$log_file"
    
    # Change to v8 directory and run tests
    cd "$tmp_dir/v8_dir/v8/"
    echo "Running tests..." >> "$log_file"
    
    ./run_test_v8.sh > output.out 2>&1
    local test_exit_code=$?
    
    if [ $test_exit_code -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|TEST_EXECUTION|$bin_name|$rel_path|$timestamp|Test execution failed with exit code $test_exit_code" >> "$error_log"
        echo "FAILED: Test execution failed with exit code $test_exit_code" >> "$log_file"
        cd - > /dev/null
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Tests executed successfully" >> "$log_file"
    
    # Save output to final location
    local current_dir=$(pwd)
    cd - > /dev/null
    cp "$tmp_dir/v8_dir/v8/output.out" "$output_file" 2>> "$log_file"
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|OUTPUT_SAVE|$bin_name|$rel_path|$timestamp|Failed to save output to $output_file" >> "$error_log"
        echo "FAILED: Could not save output file" >> "$log_file"
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Saved output to $output_file" >> "$log_file"
    
    # Clean up temporary directory
    rm -rf "$tmp_dir"
    echo "Cleaned up temporary directory" >> "$log_file"
    echo "SUCCESS" >> "$log_file"
    
    echo "0|$binary_file|$log_file"
    return 0
}

export -f process_binary
export V8_ZIP LOG_DIR ERROR_LOG

# Counters
SUCCESSFUL=0
FAILED=0
PROCESSED=0

# Process files in parallel using GNU parallel if available
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for processing"
    echo ""
    
    # Use GNU parallel
    printf '%s\n' "${BINARY_FILES[@]}" | \
        parallel -j "$MAX_PARALLEL" --bar process_binary {} "$ERROR_LOG" "$V8_ZIP" | \
        while IFS='|' read -r exit_code binary_file log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $(basename "$binary_file") (see $log_file)"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $(basename "$binary_file") (see $log_file)"
            fi
        done
else
    echo "Using xargs for processing (install 'parallel' for better progress)"
    echo ""
    
    # Fallback to xargs
    printf '%s\n' "${BINARY_FILES[@]}" | \
        xargs -P "$MAX_PARALLEL" -I {} bash -c 'process_binary "$@"' _ {} "$ERROR_LOG" "$V8_ZIP" | \
        while IFS='|' read -r exit_code binary_file log_file; do
            ((PROCESSED++))
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $(basename "$binary_file") (see $log_file)"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $(basename "$binary_file") (see $log_file)"
            fi
        done
fi

# Write final summary to log
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
cat >> "$ERROR_LOG" << EOF
[SUMMARY]
Files processed: $TOTAL
Files tested successfully: $SUCCESSFUL
Testing errors: $FAILED
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
echo "Test outputs: output/ (maintains same hierarchy as input/)"

# Create done.txt marker file
touch done.txt
echo "Created done.txt marker file"

# Exit with error code if there were failures
if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Some tests failed. Check $ERROR_LOG and logs in $LOG_DIR/ for details"
    exit 1
fi

exit 0