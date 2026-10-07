#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from patcherex2 import *

def load_function_mapping(json_file):
    """Loads the JSON and creates an addr -> name dictionary"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Create address to function name mapping
    mapping = {}
    for entry in data:
        addr = entry['addr'].lower().strip()
        # Remove '0x' prefix if exists for normalization
        if addr.startswith('0x'):
            addr = addr[2:]
        mapping[addr] = entry['name']
    
    return mapping

def extract_address_from_filename(filename):
    """Extracts the address from the filename (without 0x and without .c)"""
    name = Path(filename).stem  # Get name without extension
    # Remove '0x' if exists
    if name.startswith('0x'):
        name = name[2:]
    return name.lower()

def patch_binary(c_file_path, function_name, binary_input):
    """
    Patches the binary with the function from the .c file
    Returns (success, output_path, error_message)
    """
    try:
        # Read .c file content
        with open(c_file_path, 'r') as f:
            c_code = f.read()
        
        # Create output path replacing 'input' with 'output' in hierarchy
        # Example: input/model/IR/0x123.c -> output/model/IR/0x123
        relative_path = c_file_path.relative_to(c_file_path.parts[0])  # Removes 'input'
        output_dir = Path("output") / relative_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / c_file_path.stem
        
        # Create patcher
        p = Patcherex(binary_input)
        
        # Add patch
        p.patches.append(ModifyFunctionPatch(function_name, c_code))
        
        # Apply patches
        p.apply_patches()
        
        # Save binary
        p.save_binary(str(output_path))
        
        return (True, str(output_path), None)
    
    except Exception as e:
        return (False, str(c_file_path), str(e))

def process_file(c_file, function_mapping, binary_input):
    """Processes a single .c file"""
    addr = extract_address_from_filename(c_file.name)
    
    # Search for function name in mapping
    if addr not in function_mapping:
        return (False, str(c_file), f"Address {addr} not found in JSON mapping")
    
    function_name = function_mapping[addr]
    
    print(f"[{Path(c_file).name}] Processing -> Function: {function_name}")
    
    # Patch binary
    success, output, error = patch_binary(c_file, function_name, binary_input)
    
    if success:
        print(f"[{Path(c_file).name}] Successfully created: {output}")
    else:
        print(f"[{Path(c_file).name}] Failed - Error: {error}")
    
    return (success, output, error)

def main():
    if len(sys.argv) != 5:
        print("Usage: patch_single.py <c_file_path> <json_mapping_file> <binary_input> <log_file>")
        print("Example: patch_single.py input/model/IR/0x12345.c selected.json ./d8 error.txt")
        sys.exit(1)
    
    c_file_path = Path(sys.argv[1])
    json_file = sys.argv[2]
    binary_input = sys.argv[3]
    log_file = sys.argv[4]
    
    # Validate .c file exists
    if not c_file_path.exists():
        error_msg = f"Error: File {c_file_path} does not exist"
        print(error_msg)
        
        # Write to error log
        from datetime import datetime
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"ERROR|FILE_NOT_FOUND|{c_file_path}|{c_file_path}|{timestamp}|File does not exist\n")
        
        sys.exit(1)
    
    # Load mapping
    try:
        function_mapping = load_function_mapping(json_file)
    except Exception as e:
        error_msg = f"Error loading JSON mapping: {e}"
        print(error_msg)
        
        from datetime import datetime
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"ERROR|JSON_LOAD|{json_file}|{json_file}|{timestamp}|{str(e)}\n")
        
        sys.exit(1)
    
    # Process file
    success, output, error = process_file(c_file_path, function_mapping, binary_input)
    
    # Write result to log
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    
    # Get relative path
    try:
        relative_path = c_file_path.relative_to('input')
    except:
        relative_path = c_file_path
    
    with open(log_file, 'a') as f:
        if success:
            f.write(f"SUCCESS|PATCH|{c_file_path}|{relative_path}|{timestamp}|Output: {output}\n")
        else:
            f.write(f"ERROR|PATCH|{c_file_path}|{relative_path}|{timestamp}|{error}\n")
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()