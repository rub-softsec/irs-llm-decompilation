import binaryninja
import sys
import os

"""
Script to extract High Level Intermediate Language (HLIL) from binaries using Binary Ninja API.

HLIL is the highest level of abstraction provided by Binary Ninja, presenting a
pseudo-code representation that closely resembles the original source code.
"""
def list_all_functions_hlil(binary_path, output_file=None):
    """
    List all functions found in a binary file, including their HLIL code.
    
    Args:
        binary_path: Path to the binary file to analyze
        output_file: Optional path to write output to file
    """
    # Prepare the output handling
    if output_file:
        # If output_file doesn't have an extension, add .hlil
        if not os.path.splitext(output_file)[1]:
            output_file = output_file + '.hlil'
        f = open(output_file, 'w')
        def print_output(text):
            #print(text)
            f.write(text + '\n')
    else:
        def print_output(text):
            print(text)
    
    # Load the binary file
    bv = binaryninja.load(binary_path)
    
    #print_output(f"Functions found in {binary_path}:")
    #print_output("-" * 60)
    
    # Iterate over all functions and display basic information
    for function in bv.functions:
        print_output(f"Function Name: {function.name}")
        print_output("code:")
        
        # Get the HLIL function object
        hlil_function = function.hlil
        
        # Sort blocks by start address
        if hlil_function is not None:
            print_output(str(hlil_function))
        else:
            print_output("No HLIL available for this function")
    
    # Close the binary
    bv.file.close()
    
    # Close the output file if it was opened
    if output_file:
        f.close()
        print(f"\nOutput written to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: python {sys.argv[0]} <binary_path> [output_file]")
        print("If output_file is not specified, output will be printed to console")
        print("If output_file doesn't have an extension, .hlil will be added")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    list_all_functions_hlil(binary_path, output_file)