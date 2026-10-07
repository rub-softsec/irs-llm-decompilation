#!/usr/bin/env python3
"""
Python script to apply a test patch to a binary using Patcherex2.
This checks if the binary and the function are amiable to patching/reassembly.
"""
import json
import sys
from pathlib import Path
from patcherex2 import *

# Template C code used for all patch tests
C_CODE_TEMPLATE = """int patched_function() {
    return 42;
}
"""

def load_function_mapping(json_file):
    """
    Loads function mapping from JSON.
    Returns a dictionary: addr (str) -> name (str)
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Create mapping: address to function name
    mapping = {}
    for entry in data:
        addr = entry['addr'].lower().strip()
        # Remove '0x' prefix if present for normalization
        if addr.startswith('0x'):
            addr = addr[2:]
        mapping[addr] = entry['name']
    
    return mapping

def patch_binary(addr, function_name, binary_input):
    """
    Attempts to patch the binary at the specified function.
    
    Args:
        addr: Function address
        function_name: Name of the function to patch
        binary_input: Path to the input binary
        
    Returns:
        tuple: (success (bool), output_path (str), error_message (str/None))
    """
    # Create normalized address string for filename
    if not addr.startswith('0x'):
        addr_formatted = f"0x{addr}"
    else:
        addr_formatted = addr

    try:
        # Define output path
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / addr_formatted
        
        # Initialize Patcherex with the binary
        p = Patcherex(binary_input)
        
        # Add the patch: modify the target function with the template code
        p.patches.append(ModifyFunctionPatch(function_name, C_CODE_TEMPLATE))
        
        # Apply patches and save the new binary
        p.apply_patches()
        p.save_binary(str(output_path))
        
        return (True, str(output_path), None)
    
    except Exception as e:
        return (False, addr_formatted, str(e))

def process_entry(addr, function_name, binary_input):
    """Processes a single function entry."""
    print(f"[{addr}] Processing -> Function: {function_name}")
    
    # Attempt to patch
    success, output, error = patch_binary(addr, function_name, binary_input)
    
    if success:
        print(f"[{addr}] Success: Created {output}")
    else:
        print(f"[{addr}] Failed: {error}")
    
    return (success, output, error)

def main():
    if len(sys.argv) != 5:
        print("Usage: patch_binary.py <addr> <function_name> <binary_input> <log_file>")
        print("Example: patch_binary.py 0x1934de0 _ZN2v814AsyncHooksWrap6EnableEv ./d8 error.txt")
        sys.exit(1)
    
    addr = sys.argv[1]
    function_name = sys.argv[2]
    binary_input = sys.argv[3]
    log_file = sys.argv[4]
    
    # Normalize address
    addr_clean = addr.lower().strip()
    if addr_clean.startswith('0x'):
        addr_clean = addr_clean[2:]
    
    # Process the entry
    success, output, error = process_entry(addr, function_name, binary_input)
    
    # Log the result
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    
    with open(log_file, 'a') as f:
        if success:
            f.write(f"SUCCESS|PATCH|{addr}|{addr}|{timestamp}|Output: {output}\n")
        else:
            f.write(f"ERROR|PATCH|{addr}|{addr}|{timestamp}|{error}\n")
    
    # Return exit code based on success
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()