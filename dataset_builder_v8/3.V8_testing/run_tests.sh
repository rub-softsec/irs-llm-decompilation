#!/bin/bash

# Configuration
# Point to the output of the previous step (2.patchterex_execution)
INPUT_DIR="../2.patchterex_execution/output"
V8_ZIP="./v8_dir.zip"
MAX_PARALLEL=3
LOG_DIR="logs"
ERROR_LOG="execution_log.txt"

# Verify required files/directories
if [ ! -f "$V8_ZIP" ]; then
    echo "Error: V8 zip file $V8_ZIP not found."
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    # Fallback to local inputs if the pipeline path isn't found
    INPUT_DIR="input"
    if [ ! -d "$INPUT_DIR" ]; then
        # Last attempt: Check if we are running in standalone mode where input might be provided differently
        echo "Error: Input directory not found at ../2.patchterex_execution/output or ./input"
        exit 1
    fi
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
# Using find to handle potential subdirectories (though step 2 output is flat)
mapfile -t BINARY_FILES < <(find "$INPUT_DIR" -type f ! -name ".*")

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
    
    # Process path to maintain relative structure in output
    # If input is "../2.patchterex_execution/output/0x123", we want basename or relative path from input dir
    # Since find returns full relative path from execution dir (e.g., ../2.patchterex.../output/0x123), 
    # we need to be careful with output structure.
    # Simple approach: flatten or use basename for flat output if structure isn't required deep.
    # Previous step 2 output is flat (just 0xADDR files).
    
    local bin_name=$(basename "$binary_file")
    
    # Log directory for this file
    local log_file="$LOG_DIR/${bin_name}.log"
    local output_file="output/${bin_name}.out"
    
    # Start logging
    echo "Processing: $binary_file" > "$log_file"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%S.%6N")" >> "$log_file"
    echo "============================================" >> "$log_file"
    
    # Create temporary directory
    local tmp_dir=$(mktemp -d)
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|TMPDIR_CREATION|$bin_name|N/A|$timestamp|Failed to create temporary directory" >> "$error_log"
        echo "FAILED: Could not create temporary directory" >> "$log_file"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    echo "Created temporary directory: $tmp_dir" >> "$log_file"
    
    # Copy v8_zip to temporary directory
    cp "$v8_zip" "$tmp_dir/" 2>> "$log_file"
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|ZIP_COPY|$bin_name|N/A|$timestamp|Failed to copy v8_dir.zip" >> "$error_log"
        echo "FAILED: Could not copy v8_dir.zip" >> "$log_file"
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    # Unzip v8_dir.zip
    cd "$tmp_dir"
    unzip -q v8_dir.zip >> "$log_file" 2>&1
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|UNZIP|$bin_name|N/A|$timestamp|Failed to unzip v8_dir.zip" >> "$error_log"
        echo "FAILED: Could not unzip v8_dir.zip" >> "$log_file"
        cd - > /dev/null
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    cd - > /dev/null
    
    # Verify d8 location in unzipped structure
    # Assuming standard structure: v8_dir/v8/out/x64.release/d8
    local d8_target_path="$tmp_dir/v8_dir/v8/out/x64.release/d8"
    
    # Copy input binary to be the new 'd8' executable
    cp "$binary_file" "$d8_target_path" 2>> "$log_file"
    if [ $? -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|BINARY_COPY|$bin_name|N/A|$timestamp|Failed to copy binary to $d8_target_path" >> "$error_log"
        echo "FAILED: Could not copy binary to d8 location" >> "$log_file"
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    # Ensure it's executable
    chmod +x "$d8_target_path"
    
    # Execute tests
    cd "$tmp_dir/v8_dir/v8/"
    echo "Running tests..." >> "$log_file"
    
    # Run the test script (assumed to be part of the zip or environment)
    # If run_test_v8.sh is inside the zip, we use it.
    if [ -f "./run_test_v8.sh" ]; then
        # Ensure script is executable
        chmod +x ./run_test_v8.sh
        ./run_test_v8.sh > output.out 2>&1
        local test_exit_code=$?
    else
        echo "Warning: run_test_v8.sh not found in zip content. Trying standard test command." >> "$log_file"
        # Fallback or error if the test harness isn't valid
        test_exit_code=1
    fi
    
    if [ $test_exit_code -ne 0 ]; then
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N")
        echo "ERROR|TEST_EXECUTION|$bin_name|N/A|$timestamp|Test failed (exit code $test_exit_code)" >> "$error_log"
        echo "FAILED: Test execution failed" >> "$log_file"
        cd - > /dev/null
        rm -rf "$tmp_dir"
        echo "1|$binary_file|$log_file"
        return 1
    fi
    
    # Save output
    cd - > /dev/null
    cp "$tmp_dir/v8_dir/v8/output.out" "$output_file" 2>> "$log_file"
    
    # Cleanup
    rm -rf "$tmp_dir"
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

# Execution Loop
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for processing"
    echo ""
    
    printf '%s\n' "${BINARY_FILES[@]}" | \
        parallel -j "$MAX_PARALLEL" --bar process_binary {} "$ERROR_LOG" "$V8_ZIP" | \
        while IFS='|' read -r exit_code binary_file log_file; do
            ((PROCESSED++))
            bin_name=$(basename "$binary_file")
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $bin_name"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $bin_name (see $log_file)"
            fi
        done
else
    echo "Using xargs for processing"
    echo ""
    
    printf '%s\n' "${BINARY_FILES[@]}" | \
        xargs -P "$MAX_PARALLEL" -I {} bash -c 'process_binary "$@"' _ {} "$ERROR_LOG" "$V8_ZIP" | \
        while IFS='|' read -r exit_code binary_file log_file; do
            ((PROCESSED++))
            bin_name=$(basename "$binary_file")
            if [ "$exit_code" -eq 0 ]; then
                ((SUCCESSFUL++))
                echo "[$PROCESSED/$TOTAL] Success: $bin_name"
            else
                ((FAILED++))
                echo "[$PROCESSED/$TOTAL] Failed: $bin_name (see $log_file)"
            fi
        done
fi

# Final Summary
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
echo "Individual logs: $LOG_DIR/"
echo "Test outputs: output/"

# Create marker file
touch done.txt

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Some tests failed. Check logs for details."
    exit 1
fi

exit 0
