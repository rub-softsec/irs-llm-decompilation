#!/usr/bin/env python3
"""
Script to verify that the decompiled Pseudo-C files actually exist for the 
filtered functions.

This script reads the function mapping generated in the previous step 
(0.extract_raw_functions) and checks if the corresponding .c file exists 
in the output directory. It produces a new mapping file containing only 
the functions that were successfully decompiled and saved.
"""

import json
import os
import argparse
import sys

def verify_extracted_functions(input_map_path, input_dir, output_map_path):
    """
    Verifies that the decompiled .c files exist for each entry in the map.

    Args:
        input_map_path (str): Path to the `map_filtered.json` from Step 0.
        input_dir (str): Directory containing the extracted .c files (Step 0 output).
        output_map_path (str): Path where the verified mapping will be saved.
    """
    
    # Check if input map exists
    if not os.path.exists(input_map_path):
        print(f"Error: Input map file '{input_map_path}' not found.")
        return

    # Load the original filtered map
    print(f"Loading map from: {input_map_path}")
    with open(input_map_path, 'r') as f:
        data = json.load(f)

    print(f"Checking existence of files in: {input_dir}")
    
    # Filter entries where the corresponding .c file exists
    filtered_data = []
    missing_count = 0
    
    for entry in data:
        addr = entry['addr']
        # The filename format from Step 0 is '0xADDRESS.c'
        # Ensure we construct the filename correctly
        file_name = f'{addr}.c'
        file_path = os.path.join(input_dir, file_name)
        
        if os.path.exists(file_path):
            filtered_data.append(entry)
        else:
            missing_count += 1
            # Optional: verbose logging for missing files
            # print(f"Warning: File not found for {entry['name']} at {file_path}")

    # Save the result to the new JSON file
    with open(output_map_path, 'w') as f:
        json.dump(filtered_data, f, indent=2)

    print(f"\nProcessing Complete:")
    print(f"  Total input entries: {len(data)}")
    print(f"  Validated entries (found): {len(filtered_data)}")
    print(f"  Missing entries: {missing_count}")
    print(f"  Verified map saved to: {output_map_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify existence of decompiled function files."
    )
    
    # Default paths assume the standard directory structure
    default_map = os.path.join('..', '0.extract_raw_functions', 'map_filtered.json')
    default_dir = os.path.join('..', '0.extract_raw_functions', 'output_c')
    default_output = 'map_usable.json'

    parser.add_argument(
        '--input_map', 
        default=default_map,
        help=f"Path to input map JSON (default: {default_map})"
    )
    parser.add_argument(
        '--input_dir', 
        default=default_dir,
        help=f"Directory containing .c files (default: {default_dir})"
    )
    parser.add_argument(
        '--output_map', 
        default=default_output,
        help=f"Path to output verified map JSON (default: {default_output})"
    )

    args = parser.parse_args()

    verify_extracted_functions(args.input_map, args.input_dir, args.output_map)