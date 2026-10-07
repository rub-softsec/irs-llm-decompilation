import binaryninja
import sys
import json
import os


def extract_asm_functions(binary_path, json_path, output_dir="output/asm", error_file="asm.error"):
    """
    Extract ASM representation of specific functions from a binary.
    
    Args:
        binary_path: Path to the binary file (d8)
        json_path: Path to map.json with function addresses
        output_dir: Directory to save the output .asm files
        error_file: Path to error log file
    """
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load the JSON file with function addresses
    with open(json_path, 'r') as f:
        functions_data = json.load(f)
    
    print(f"Loading binary: {binary_path}")
    # Load the binary file
    bv = binaryninja.load(binary_path)
    
    if bv is None:
        print("Error: Could not load binary")
        with open(error_file, 'w') as err_f:
            err_f.write("CRITICAL ERROR: Could not load binary\n")
        return
    
    # Wait for analysis to complete
    bv.update_analysis_and_wait()
    
    print(f"Found {len(functions_data)} functions to extract")
    
    # List to track errors
    errors = []
    
    # Process each function from the JSON
    for func_data in functions_data:
        func_name = func_data['name']
        func_addr_str = func_data['addr']
        
        # Convert address string to integer
        func_addr = int(func_addr_str, 16)
        
        print(f"Processing {func_name} at {func_addr_str}...")
        
        # Get the function at the specified address
        function = bv.get_function_at(func_addr)
        
        if function is None:
            error_msg = f"No function found at address {func_addr_str} for {func_name}"
            print(f"  Warning: {error_msg}")
            errors.append(f"Function: {func_name}, Address: {func_addr_str} - {error_msg}")
            continue
        
        # Check if function analysis was skipped
        if function.analysis_skipped:
            print(f"  Enabling analysis for skipped function...")
            function.analysis_skip_override = binaryninja.FunctionAnalysisSkipOverride.NeverSkipFunctionAnalysis
            bv.update_analysis_and_wait()
        
        try:
            # Get ASM representation
            asm_code = get_asm_code(bv, function)
            
            # Create output filename: 0xaddr.asm
            output_filename = f"{func_addr_str}.asm"
            output_path = os.path.join(output_dir, output_filename)
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write(asm_code)
            
            print(f"  Saved to {output_path}")
        
        except Exception as e:
            error_msg = f"Exception while processing: {str(e)}"
            print(f"  Error: {error_msg}")
            errors.append(f"Function: {func_name}, Address: {func_addr_str} - {error_msg}")
    
    # Close the binary
    bv.file.close()
    
    # Write errors to file if any occurred
    if errors:
        with open(error_file, 'w') as err_f:
            err_f.write("=" * 60 + "\n")
            err_f.write("ERRORS DURING ASM EXTRACTION\n")
            err_f.write("=" * 60 + "\n\n")
            for error in errors:
                err_f.write(error + "\n")
            err_f.write("\n" + "=" * 60 + "\n")
            err_f.write(f"Total errors: {len(errors)}\n")
        print(f"\n{len(errors)} errors occurred. See {error_file} for details.")
    else:
        # Create empty error file or remove it if it exists
        if os.path.exists(error_file):
            os.remove(error_file)
        print(f"\nAll functions extracted successfully!")
    
    print(f"All functions extracted to {output_dir}/")


def get_asm_code(bv, function):
    """
    Gets the ASM representation of a function.
    
    Args:
        bv: BinaryView instance
        function: Function instance
    
    Returns:
        String containing the ASM code
    """
    lines = []
    
    # Add function header information
    lines.append(f"Function Name: {function.name}\n")
    lines.append(f"Architecture: {bv.arch.name}\n")
    lines.append(f"Entry Point: 0x{function.start:x}\n")
    lines.append("code:\n")
    
    # Sort blocks by start address
    sorted_blocks = sorted(function, key=lambda block: block.start)
    
    for block in sorted_blocks:
        asm_address = block.start
        
        for instruction in block:
            # Get the disassembled text
            instruction_text = ''
            for token in instruction[0]:
                instruction_text = instruction_text + str(token).replace('\n', '')
            
            lines.append(f"0x{asm_address:x}: {instruction_text}\n")
            asm_address = asm_address + instruction[1]
    
    # Join all lines into a single string
    return ''.join(lines)


if __name__ == "__main__":
    binary_path = "input/d8"
    json_path = "input/selected.json"
    output_dir = "output/asm"
    error_file = "asm.error"
    
    # Check if required files exist
    if not os.path.exists(binary_path):
        print(f"Error: Binary file not found at {binary_path}")
        sys.exit(1)
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        sys.exit(1)
    
    extract_asm_functions(binary_path, json_path, output_dir, error_file)