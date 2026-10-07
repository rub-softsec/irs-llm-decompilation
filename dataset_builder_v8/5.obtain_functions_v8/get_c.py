import binaryninja
import sys
import json
import os
import argparse

def extract_pseudo_c_functions(binary_path, json_path, output_dir="output"):
    """
    Extract Pseudo C representation of specific functions from a binary.
    
    This script is designed to extract the source code for functions that have been
    "Covered" by the V8 test suite (i.e., replacing them with a dummy caused a failure).
    
    Args:
        binary_path: Path to the binary file (d8)
        json_path: Path to map_covered.json with function addresses
        output_dir: Directory to save the output .c files
    """
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"[*] Reading function map from: {json_path}")
    try:
        with open(json_path, 'r') as f:
            functions_data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    print(f"[*] Loading binary: {binary_path}")
    # Load the binary file
    bv = binaryninja.load(binary_path)
    
    if bv is None:
        print("Error: Could not load binary. Check path and license.")
        return
    
    # Wait for analysis to complete
    print("[*] Waiting for analysis to complete...")
    bv.update_analysis_and_wait()
    
    print(f"[*] Found {len(functions_data)} covered functions to extract")
    
    count_extracted = 0
    
    # Process each function from the JSON
    for func_data in functions_data:
        func_name = func_data.get('name', 'unknown')
        func_addr_str = func_data.get('addr')
        
        if not func_addr_str:
            continue
            
        # Convert address string to integer
        try:
            func_addr = int(func_addr_str, 16)
        except ValueError:
            print(f"  Warning: Invalid address format {func_addr_str}")
            continue
            
        # Get the function at the specified address
        function = bv.get_function_at(func_addr)
        
        if function is None:
            print(f"  Warning: No function found at {func_addr_str} ({func_name})")
            continue
        
        # Check if function analysis was skipped
        if function.analysis_skipped:
            print(f"  Enabling analysis for skipped function {func_name}...")
            function.analysis_skip_override = binaryninja.FunctionAnalysisSkipOverride.NeverSkipFunctionAnalysis
            bv.update_analysis_and_wait()
        
        # Get Pseudo C representation
        pseudo_c = get_pseudo_c(bv, function)
        
        # Create output filename: 0xaddr.c
        output_filename = f"{func_addr_str}.c"
        output_path = os.path.join(output_dir, output_filename)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(pseudo_c)
            
        count_extracted += 1
        # Optional: Print progress every N items or just print a dot
        # print(f"  Saved {func_name} to {output_path}")
    
    # Close the binary
    bv.file.close()
    print(f"\n[*] Extraction complete. {count_extracted}/{len(functions_data)} functions saved to {output_dir}/")


def get_pseudo_c(bv, function):
    """
    Gets the Pseudo C representation of a function.
    Based on PCDump-bn plugin approach.
    
    Args:
        bv: BinaryView instance
        function: Function instance
    
    Returns:
        String containing the Pseudo C code
    """
    lines = []
    
    # Configure disassembly settings
    settings = binaryninja.DisassemblySettings()
    settings.set_option(binaryninja.DisassemblyOption.ShowAddress, False)
    settings.set_option(binaryninja.DisassemblyOption.WaitForIL, True)
    
    # Create linear view object with language representation (Pseudo C)
    obj = binaryninja.LinearViewObject.language_representation(bv, settings)
    
    # Create cursor and navigate to function
    cursor_end = binaryninja.LinearViewCursor(obj)
    cursor_end.seek_to_address(function.highest_address)
    
    # Get function body (lines after cursor position)
    body = bv.get_next_linear_disassembly_lines(cursor_end)
    
    # Reset cursor to get header
    cursor_end.seek_to_address(function.highest_address)
    header = bv.get_previous_linear_disassembly_lines(cursor_end)
    
    # Append header lines
    for line in header:
        lines.append(f'{str(line)}\n')
    
    # Append body lines
    for line in body:
        lines.append(f'{str(line)}\n')
    
    # Join all lines into a single string
    return ''.join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Pseudo-C for covered functions using BinaryNinja.")
    
    # Default paths based on pipeline structure
    default_map = os.path.join('..', '4.analyze_logs', 'map_covered.json')
    default_out = "output"
    
    parser.add_argument('binary_path', help="Path to the d8 binary")
    parser.add_argument('--json_path', default=default_map, 
                        help=f"Path to map_covered.json (default: {default_map})")
    parser.add_argument('--output_dir', default=default_out,
                        help=f"Output directory (default: {default_out})")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.binary_path):
        print(f"Error: Binary not found at {args.binary_path}")
        sys.exit(1)
        
    extract_pseudo_c_functions(args.binary_path, args.json_path, args.output_dir)