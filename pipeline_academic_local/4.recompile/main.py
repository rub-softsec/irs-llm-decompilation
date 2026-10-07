#!/usr/bin/env python3
"""
Script to compile C functions from input directory.
Reads C files from input directory and compiles them using metadata from JSON file.
Maintains directory hierarchy in output directory.
Compilation errors are saved to errors.txt and error files in output/error/ directory.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

JSON_FILENAME = "json/selected.jsonl"
INPUT_DIR = "input"
OUTPUT_DIR = "output"
ERROR_DIR = os.path.join(OUTPUT_DIR, "error")

def load_json_metadata(json_filename):
    """
    Load metadata from JSON file indexed by function ID.
    
    Args:
        json_filename: Path to the JSON file
        
    Returns:
        Dictionary with function ID as key and metadata as value
    """
    metadata = {}
    
    try:
        with open(json_filename, 'r') as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    func_id = data.get('id')
                    
                    if func_id is not None:
                        metadata[str(func_id)] = {
                            'func_head': data.get('func_head', ''),
                            'deps': data.get('real_deps', ''),
                            'line_num': line_num
                        }
                except json.JSONDecodeError as e:
                    print(f"Warning: Error parsing JSON at line {line_num}: {e}")
                    
    except FileNotFoundError:
        print(f"Error: JSON file '{json_filename}' not found")
        return {}
    
    return metadata

def find_c_files(input_dir):
    """
    Find all .c files in the input directory recursively.
    
    Args:
        input_dir: Root directory to search for .c files
        
    Returns:
        List of tuples (file_path, relative_path, func_id)
    """
    c_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return []
    
    for c_file in input_path.rglob("*.c"):
        # Get relative path from input directory
        relative_path = c_file.relative_to(input_path)
        
        # Extract function ID from filename (without extension)
        func_id = c_file.stem
        
        # Validate that func_id is numeric
        try:
            int(func_id)
            c_files.append((str(c_file), str(relative_path), func_id))
        except ValueError:
            print(f"Warning: Skipping file {c_file} - filename is not numeric")
    
    return c_files

def compile_function(c_file_path, relative_path, func_id, metadata, output_dir, error_dir, error_log):
    """
    Compiles a C function into an object file.
    
    Args:
        c_file_path: Path to the C source file
        relative_path: Relative path from input directory
        func_id: Function ID
        metadata: Metadata dictionary for the function
        output_dir: Output directory for successful compilations
        error_dir: Error directory for failed compilations
        error_log: List to accumulate general errors
        
    Returns:
        True if compilation successful, False otherwise
    """
    try:
        # Read the C function from file
        with open(c_file_path, 'r') as f:
            func_def = f.read().strip()
        
        if not func_def:
            error_msg = f"Error: File {c_file_path} is empty\n"
            print(error_msg)
            error_log.append(error_msg)
            return False
        
        # Get metadata for this function
        func_metadata = metadata.get(func_id)
        if not func_metadata:
            error_msg = f"Error: No metadata found for function ID {func_id} in JSON file\n"
            print(error_msg)
            error_log.append(error_msg)
            return False
        
        deps = func_metadata['deps']
        
        # Create complete C code with dependencies and function
        full_c_code = f"{deps}\n\n{func_def}"
        
        # Create output directory structure
        output_file_dir = os.path.join(output_dir, os.path.dirname(relative_path))
        os.makedirs(output_file_dir, exist_ok=True)
        
        # Define output filename
        output_filename = os.path.splitext(relative_path)[0] + ".o"
        obj_filename = os.path.join(output_dir, output_filename)
        
        # Write temporary C file for compilation
        temp_c_file = obj_filename.replace('.o', '_temp.c')
        with open(temp_c_file, 'w') as f:
            f.write(full_c_code)
        
        try:
            # Compile to object file
            cmd_obj = [
                'gcc',
                '-c',           # Compile without linking
                '-o', obj_filename,
                temp_c_file
            ]
            
            # Execute compilation
            result = subprocess.run(cmd_obj, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Compilation failed - create error file
                error_file_dir = os.path.join(error_dir, os.path.dirname(relative_path))
                os.makedirs(error_file_dir, exist_ok=True)
                
                error_filename = os.path.splitext(relative_path)[0] + ".error"
                error_file_path = os.path.join(error_dir, error_filename)
                
                # Write compilation error to error file
                with open(error_file_path, 'w') as ef:
                    ef.write(f"Compilation error for function ID {func_id}\n")
                    ef.write(f"Source file: {c_file_path}\n")
                    ef.write(f"Timestamp: {datetime.now()}\n")
                    ef.write(f"Command: {' '.join(cmd_obj)}\n\n")
                    ef.write("STDERR:\n")
                    ef.write(result.stderr)
                    if result.stdout:
                        ef.write("\nSTDOUT:\n")
                        ef.write(result.stdout)
                
                error_msg = f"Error compiling function ID={func_id} ({c_file_path}): See {error_file_path}\n"
                print(error_msg)
                error_log.append(error_msg)
                return False
            else:
                print(f"Function ID={func_id} compiled successfully: {obj_filename}")
                return True
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_c_file)
            except:
                pass
                
    except Exception as e:
        error_msg = f"Error processing function ID={func_id} ({c_file_path}): {e}\n"
        print(error_msg)
        error_log.append(error_msg)
        return False

def process_c_files():
    """
    Main processing function that compiles all C files found in input directory.
    """
    compiled_count = 0
    error_count = 0
    error_log = []
    
    # Add timestamp to error log
    error_log.append(f"=== Processing started: {datetime.now()} ===\n")
    error_log.append(f"Input directory: {INPUT_DIR}\n")
    error_log.append(f"Output directory: {OUTPUT_DIR}\n")
    error_log.append(f"JSON metadata file: {JSON_FILENAME}\n\n")
    
    # Load JSON metadata
    print("Loading JSON metadata...")
    metadata = load_json_metadata(JSON_FILENAME)
    if not metadata:
        error_msg = "Error: No metadata loaded from JSON file\n"
        print(error_msg)
        error_log.append(error_msg)
        return 0, 1
    
    print(f"Loaded metadata for {len(metadata)} functions")
    
    # Find all C files in input directory
    print("Scanning for C files...")
    c_files = find_c_files(INPUT_DIR)
    if not c_files:
        error_msg = "Error: No C files found in input directory\n"
        print(error_msg)
        error_log.append(error_msg)
        return 0, 1
    
    print(f"Found {len(c_files)} C files")
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)
    
    # Process each C file
    for c_file_path, relative_path, func_id in c_files:
        print(f"Processing {relative_path} (ID: {func_id})...")
        
        if compile_function(c_file_path, relative_path, func_id, metadata, 
                          OUTPUT_DIR, ERROR_DIR, error_log):
            compiled_count += 1
        else:
            error_count += 1
    
    # Write summary
    summary = f"\n=== Summary ===\n"
    summary += f"C files processed: {len(c_files)}\n"
    summary += f"Functions compiled successfully: {compiled_count}\n"
    summary += f"Compilation errors: {error_count}\n"
    summary += f"=== Processing finished: {datetime.now()} ===\n"
    
    error_log.append(summary)
    print(summary)
    
    # Write error log to file
    with open("error.txt", "w") as error_file:
        error_file.writelines(error_log)
    print(f"General error log saved to: errors.txt")
    
    if error_count > 0:
        print(f"Individual error files saved in: {ERROR_DIR}")
    
    return compiled_count, error_count

def main():
    """
    Main script function.
    """
    # Check if required directories and files exist
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Input directory '{INPUT_DIR}' does not exist")
        sys.exit(1)
    
    if not os.path.exists(JSON_FILENAME):
        print(f"Error: JSON file '{JSON_FILENAME}' does not exist")
        sys.exit(1)
    
    print(f"Processing C files from: {INPUT_DIR}")
    print(f"Using metadata from: {JSON_FILENAME}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    compiled, errors = process_c_files()
    
    # Exit with error code if no functions were compiled
    if compiled == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()