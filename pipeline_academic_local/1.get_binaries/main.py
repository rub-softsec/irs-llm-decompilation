#!/usr/bin/env python3
"""
Script to compile functions from a JSON file with different GCC optimization levels.

This component constitutes the first stage of the experimental pipeline. It reads C function
definitions from a JSONL dataset and compiles each valid function into independent object files
across multiple GCC optimization levels (O0, O1, O2, O3). These object files serve as the 
ground truth artifacts for subsequent disassembly and decompilation tasks.

Key features:
- Standardized compilation environment using GCC.
- Generation of multi-optimization targets for each sample.
- Robust error handling and logging for compilation failures.
"""

import json
import os
import tempfile
import subprocess
import sys
from pathlib import Path
from datetime import datetime

JSON_FILENAME = "input/selected.jsonl"

# Optimization levels to use
OPTIMIZATION_LEVELS = ['O0', 'O1', 'O2', 'O3']

def compile_function(func_def, func_head, deps, func_id, optimization_level, output_dir="output", error_log=None):
    """
    Compiles a C function into an object file with specified optimization level.
    
    Args:
        func_def: Complete function definition
        func_head: Function header
        deps: Required dependencies (headers)
        func_id: Function ID for naming the file
        optimization_level: GCC optimization level (O0, O1, O2, O3)
        output_dir: Base directory where compiled files will be saved
        error_log: List to accumulate errors
    """
    # Create optimization-level subdirectory
    opt_dir = os.path.join(output_dir, optimization_level)
    os.makedirs(opt_dir, exist_ok=True)
    
    # Create complete C code with dependencies and function
    full_c_code = f"{deps}\n\n{func_def}"
    
    # Use temporary files for the source code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as src_file:
        src_file.write(full_c_code)
        src_file.flush()
        
        # Define output filename using the ID in the optimization subdirectory
        obj_filename = os.path.join(opt_dir, f"{func_id}.o")
        
        try:
            # Compile to object file with optimization level
            cmd_obj = [
                'gcc',
                '-c',           # Compile without linking
                f'-{optimization_level}',  # Optimization flag
                '-o', obj_filename,
                src_file.name
            ]
            
            # Execute compilation
            result = subprocess.run(cmd_obj, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = f"Error compiling function ID={func_id} (optimization={optimization_level}):\n{result.stderr}\n"
                print(error_msg)
                if error_log is not None:
                    error_log.append(error_msg)
                return False
            else:
                print(f"Function ID={func_id} (optimization={optimization_level}) compiled successfully: {obj_filename}")
                return True
                
        except Exception as e:
            error_msg = f"Error processing function ID={func_id} (optimization={optimization_level}): {e}\n"
            print(error_msg)
            if error_log is not None:
                error_log.append(error_msg)
            return False
        finally:
            # Clean up temporary file
            try:
                os.unlink(src_file.name)
            except:
                pass


def process_json_file(json_filename):
    """
    Processes a JSON file line by line, extracting and compiling each function
    with all optimization levels.
    
    Args:
        json_filename: Name of the JSON file to process
    """
    compiled_count = 0
    error_count = 0
    error_log = []
    opt_stats = {}  # Track statistics by optimization level
    
    # Initialize optimization statistics
    for opt_level in OPTIMIZATION_LEVELS:
        opt_stats[opt_level] = {'compiled': 0, 'errors': 0}
    
    # Add timestamp to error log
    error_log.append(f"=== Processing started: {datetime.now()} ===\n")
    error_log.append(f"File processed: {json_filename}\n")
    error_log.append(f"Optimization levels: {', '.join(OPTIMIZATION_LEVELS)}\n\n")
    
    with open(json_filename, 'r') as f:
        for line_num, line in enumerate(f):
            try:
                # Parse JSON line
                data = json.loads(line.strip())
                
                # Extract required information
                func_def = data.get('func_def', '')
                func_head = data.get('func_head', '')
                deps = data.get('real_deps', '')
                func_id = data.get('id')
                score = data.get('score')  # Keep for logging purposes
                
                if func_id is None:
                    error_msg = f"Line {line_num}: 'id' field not found\n"
                    print(error_msg)
                    error_log.append(error_msg)
                    error_count += 1
                    continue
                
                if not func_def:
                    error_msg = f"Line {line_num} (ID={func_id}): func_def not found\n"
                    print(error_msg)
                    error_log.append(error_msg)
                    error_count += 1
                    continue
                
                # Compile function with each optimization level
                for opt_level in OPTIMIZATION_LEVELS:
                    if compile_function(func_def, func_head, deps, func_id, opt_level, error_log=error_log):
                        compiled_count += 1
                        opt_stats[opt_level]['compiled'] += 1
                    else:
                        error_count += 1
                        opt_stats[opt_level]['errors'] += 1
                    
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON at line {line_num}: {e}\n"
                print(error_msg)
                error_log.append(error_msg)
                error_count += 1
            except Exception as e:
                error_msg = f"Error processing line {line_num}: {e}\n"
                print(error_msg)
                error_log.append(error_msg)
                error_count += 1
    
    # Write summary
    summary = f"\n=== Summary ===\n"
    summary += f"Total function compilations attempted: {compiled_count + error_count}\n"
    summary += f"Total compilations successful: {compiled_count}\n"
    summary += f"Total compilation errors: {error_count}\n\n"
    
    # Add optimization-level breakdown
    summary += "=== Breakdown by Optimization Level ===\n"
    for opt_level in OPTIMIZATION_LEVELS:
        stats = opt_stats[opt_level]
        summary += f"{opt_level}: {stats['compiled']} compiled, {stats['errors']} errors\n"
    
    summary += f"\n=== Processing finished: {datetime.now()} ===\n"
    
    error_log.append(summary)
    print(summary)
    
    # Write error log to file
    if error_log:
        with open("error.txt", "w") as error_file:
            error_file.writelines(error_log)
        print(f"Error log saved to: error.txt")
    
    return compiled_count, error_count, opt_stats


def main():
    """
    Main script execution entry point.
    
    Validates input file existence, parameters, and orchestrates the dataset processing.
    Reports final statistics and directory structure upon completion.
    """
    if not os.path.exists(JSON_FILENAME):
        print(f"Error: File '{JSON_FILENAME}' does not exist")
        sys.exit(1)
    
    print(f"Processing file: {JSON_FILENAME}")
    print(f"Optimization levels: {', '.join(OPTIMIZATION_LEVELS)}")
    compiled, errors, opt_stats = process_json_file(JSON_FILENAME)
    
    # Show directory structure created
    print(f"\nDirectories created in output/:")
    for opt_level in OPTIMIZATION_LEVELS:
        print(f"  output/{opt_level}/ - {opt_stats[opt_level]['compiled']} files")
    
    # Exit with error code if no functions were compiled
    if compiled == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()