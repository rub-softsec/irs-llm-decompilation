#!/bin/bash

# Script to execute Binary Ninja scripts on all binaries
# and save results in the output/ directory

# Create output directory if it doesn't exist
if [ ! -d "output" ]; then
    echo "Creating output/ directory"
    mkdir output
fi

# Verify that required directories exist
if [ ! -d "code" ]; then
    echo "Error: code/ directory not found"
    exit 1
fi

if [ ! -d "input" ]; then
    echo "Error: input/ directory not found"
    exit 1
fi

# Array with scripts to execute
scripts=("get_asm.py" "get_hlil.py" "get_llil.py" "get_mlil.py")

# Counter for processed files
total_files=0
processed_files=0

# Count total binaries recursively
while IFS= read -r binary; do
    ((total_files++))
done < <(find input -type f)

echo "Found $total_files binaries in input/"
echo "========================================"

# Process each binary recursively
while IFS= read -r binary; do
    # Get relative path from input
    relative_path=${binary#input/}
    # Get directory path from relative path
    relative_dir=$(dirname "$relative_path")
    # Get filename without path and without extension
    filename=$(basename "$binary")
    filename_no_ext="${filename%.*}"
    
    # Create output directory structure if it doesn't exist
    if [ "$relative_dir" != "." ]; then
        output_dir="output/$relative_dir"
        if [ ! -d "$output_dir" ]; then
            echo "Creating directory: $output_dir"
            mkdir -p "$output_dir"
        fi
    else
        output_dir="output"
    fi
    
    echo "Processing: $relative_path"
    
    # Execute each script
    for script in "${scripts[@]}"; do
        # Get output extension based on script
        case $script in
            "get_asm.py")
                ext="asm"
                ;;
            "get_hlil.py")
                ext="hlil"
                ;;
            "get_llil.py")
                ext="llil"
                ;;
            "get_mlil.py")
                ext="mlil"
                ;;
        esac
        
        # Output file using filename without extension
        output_file="$output_dir/${filename_no_ext}.${ext}"
        
        # Execute the script
        if python3 "code/$script" "$binary" "$output_file" 2>/dev/null; then
            echo "  $script completed -> $output_file"
        else
            echo "  Error executing $script"
        fi
    done
    
    ((processed_files++))
    echo "Progress: $processed_files/$total_files files processed"
done < <(find input -type f)

echo "========================================"
echo "Process completed!"
echo "Files processed: $processed_files"
echo "Results saved in: output/"

# Check for empty files and remove them
echo "========================================"
echo "Checking for empty files in output/"
echo "========================================"

# Initialize error.txt file (clear if exists)
> error.txt

empty_files=()
removed_count=0

# Check each file in output directory recursively
while IFS= read -r file; do
    # Check if file is empty
    if [ ! -s "$file" ]; then
        # Get relative path from output/
        relative_path=${file#output/}
        empty_files+=("$relative_path")
        
        # Write to error.txt
        echo "$relative_path" >> error.txt
        
        # Remove the empty file
        rm "$file"
        ((removed_count++))
        echo "  Removed empty file: $relative_path"
    fi
done < <(find output -type f)

# Clean up empty directories in output
find output -type d -empty -delete

echo "========================================"
if [ ${#empty_files[@]} -eq 0 ]; then
    echo "All files contain data. No empty files found."
    echo "error.txt is empty (no errors)"
else
    echo "Found and removed $removed_count empty files"
    echo "Empty files have been logged to error.txt"
fi
echo "========================================"