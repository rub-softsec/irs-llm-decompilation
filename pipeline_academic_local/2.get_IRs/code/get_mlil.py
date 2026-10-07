import binaryninja
import sys
import os

"""
Script to extract Medium Level Intermediate Language (MLIL) from binaries using Binary Ninja API.

MLIL provides a higher level of abstraction than LLIL, introducing concepts such as
variables, types, and structure fields, making it suitable for analysis that requires
understanding of data flow and types.
"""
def list_all_functions_mlil(binary_path, output_file=None):
    """
    List all functions found in a binary file, including their MLIL code.
    
    Args:
        binary_path: Path to the binary file to analyze
        output_file: Optional path to write output to file
    """
    # Prepare the output handling
    if output_file:
        # If output_file doesn't have an extension, add .mlil
        if not os.path.splitext(output_file)[1]:
            output_file = output_file + '.mlil'
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
        print_output(f"Entry Point: 0x{function.start:x}")
        print_output("code:")
        
        # Get the MLIL function object
        mlil_function = function.mlil
        
        # Sort blocks by start address
        if mlil_function is not None:
            sorted_blocks = sorted(mlil_function, key=lambda block: block.start)
            
            for block in sorted_blocks:
                #print_output(f"Block at 0x{block.start:x}:")
                
                for instruction in block:
                    # Get the MLIL instruction address
                    mlil_address = instruction.address
                    
                    # Get the MLIL instruction text
                    instruction_text = ''
                    for token in instruction.tokens:
                        instruction_text += str(token)
                    
                    # Print the MLIL instruction
                    print_output(f"0x{mlil_address:x}: {instruction_text}")
                
                #print_output("-----")
        else:
            print_output("No MLIL available for this function")
    
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
        print("If output_file doesn't have an extension, .mlil will be added")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    list_all_functions_mlil(binary_path, output_file)