import binaryninja
import sys
import json
import os


def extract_pseudo_c_functions(binary_path, json_path, output_dir="output_c"):
    """
    Extracts Pseudo-C (Decompiled) representation of specific functions from a binary 
    using the BinaryNinja API.

    This function iterates through a list of functions provided in a JSON map, identifies 
    them in the binary, and exports their high-level IL (Pseudo-C) representation to 
    individual source files.

    Args:
        binary_path (str): Path to the target binary file (e.g., 'd8').
        json_path (str): Path to the filtered function map JSON (containing name and address).
        output_dir (str): Directory where the decompiled .c files will be saved.
    """
    
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load the JSON map containing target function addresses
    with open(json_path, 'r') as f:
        functions_data = json.load(f)
    
    print(f"Loading binary: {binary_path}")
    # Initialize BinaryNinja and load the binary view
    bv = binaryninja.load(binary_path)
    
    if bv is None:
        print("Error: Could not load binary. Please check the path and your license.")
        return
    
    # Perform full analysis on the binary to ensure accurate functions and IL
    bv.update_analysis_and_wait()
    
    print(f"Found {len(functions_data)} functions to extract")
    
    # Iterate through each function entry from the JSON map
    for func_data in functions_data:
        func_name = func_data['name']
        func_addr_str = func_data['addr']
        
        # Convert hex string address to integer
        func_addr = int(func_addr_str, 16)
        
        print(f"Processing {func_name} at {func_addr_str}...")
        
        # Retrieve the function object at the specified entry address
        function = bv.get_function_at(func_addr)
        
        if function is None:
            print(f"  Warning: No function found at address {func_addr_str}")
            continue
        
        # If analysis was skipped for this function, force it to run now
        if function.analysis_skipped:
            print(f"  Enabling analysis for skipped function...")
            function.analysis_skip_override = binaryninja.FunctionAnalysisSkipOverride.NeverSkipFunctionAnalysis
            bv.update_analysis_and_wait()
        
        # Extract the Pseudo-C code from the function
        pseudo_c = get_pseudo_c(bv, function)
        
        # Construct output filename using the function's address (unique identifier)
        output_filename = f"{func_addr_str}.c"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the extracted C code to disk
        with open(output_path, 'w') as f:
            f.write(pseudo_c)
        
        print(f"  Saved to {output_path}")
    
    # Close the binary view (though BNi usually handles this via scope, explicit close is good practice)
    bv.file.close()
    print(f"\nAll functions extracted to {output_dir}/")


def get_pseudo_c(bv, function):
    """
    Retrieves the Pseudo-C representation of a function from BinaryNinja.
    
    This method mirrors the approach used by the 'PCDump' plugin. It creates a linear
    view of the function's High-Level IL (HLIL) or Pseudo-C representation and
    iterates through the lines to construct the full source string.

    Args:
        bv (binaryninja.BinaryView): The binary view object.
        function (binaryninja.Function): The function object to decompile.
    
    Returns:
        str: The decompiled Pseudo-C code as a single string.
    """
    lines = []
    
    # Configure disassembly settings for clean output (hide addresses, wait for IL)
    settings = binaryninja.DisassemblySettings()
    settings.set_option(binaryninja.DisassemblyOption.ShowAddress, False)
    settings.set_option(binaryninja.DisassemblyOption.WaitForIL, True)
    
    # Create a linear view object specifically for variable/language representation (Pseudo-C)
    obj = binaryninja.LinearViewObject.language_representation(bv, settings)
    
    # Initialize a cursor for navigation
    cursor_end = binaryninja.LinearViewCursor(obj)
    
    # Seek to the end of the function to establish context? 
    # (Note: Logic follows standard BNi export patterns whereby we seek to function bounds)
    cursor_end.seek_to_address(function.highest_address)
    
    # Retrieve the body of the function
    body = bv.get_next_linear_disassembly_lines(cursor_end)
    
    # Reset cursor to retrieve function header/signature
    cursor_end.seek_to_address(function.highest_address)
    header = bv.get_previous_linear_disassembly_lines(cursor_end)
    
    # Accumulate header lines (function signature, etc.)
    for line in header:
        lines.append(f'{str(line)}\n')
    
    # Accumulate body lines (code)
    for line in body:
        lines.append(f'{str(line)}\n')
    
    # Combine all lines into the final source code string
    lines_of_code = ''.join(lines)
    return lines_of_code


if __name__ == "__main__":
    # Validate command line arguments
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print(f"Usage: python {sys.argv[0]} <binary_path> [json_path] [output_dir]")
        print("  binary_path: Path to the d8 binary")
        print("  json_path: Path to map_filtered.json (default: map_filtered.json)")
        print("  output_dir: Output directory for .c files (default: output_c)")
        sys.exit(1)
    
    # Parse arguments with defaults
    binary_path = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) >= 3 else "map_filtered.json"
    output_dir = sys.argv[3] if len(sys.argv) == 4 else "output_c"
    
    # Run the extraction pipeline
    extract_pseudo_c_functions(binary_path, json_path, output_dir)