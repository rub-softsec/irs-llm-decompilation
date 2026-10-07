#!/bin/bash

# Verify parameters
if [ $# -ne 2 ]; then
    echo "Usage: $0 <source_directory> <destination_directory>"
    exit 1
fi

SOURCE="$1"
DESTINATION="$2"

# Verify that source directory exists
if [ ! -d "$SOURCE" ]; then
    echo "Error: Source directory '$SOURCE' does not exist"
    exit 1
fi

# Create destination directory if it doesn't exist
mkdir -p "$DESTINATION"

# Iterate through all subdirectories in source
for subdir in "$SOURCE"/*; do
    # Verify it's a directory
    if [ ! -d "$subdir" ]; then
        continue
    fi
    
    # Iterate through subdirectory content (skipping the first numeric level)
    find "$subdir" -type f -o -type d | while read -r item; do
        # Calculate relative path removing the numeric subdirectory prefix
        relative_path="${item#$subdir/}"
        
        # If it's the subdirectory itself, continue
        if [ "$relative_path" = "$item" ]; then
            continue
        fi
        
        destination_path="$DESTINATION/$relative_path"
        
        # If it's a directory, create it
        if [ -d "$item" ]; then
            mkdir -p "$destination_path"
        # If it's a file
        elif [ -f "$item" ]; then
            # Create parent directory if it doesn't exist
            mkdir -p "$(dirname "$destination_path")"
            
            # Check if file already exists
            if [ -f "$destination_path" ]; then
                echo "CONFLICT: File '$relative_path' already exists. Appending content from '$item'"
                cat "$item" >> "$destination_path"
            else
                cp "$item" "$destination_path"
            fi
        fi
    done
done

echo "Process completed"