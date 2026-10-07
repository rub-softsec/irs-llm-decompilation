import binaryninja
import sys
import os

"""
Script to extract Low Level Intermediate Language (LLIL) from binaries using Binary Ninja API.

LLIL is a low-level abstraction that is close to assembly but normalized, removing
architecture-specific idiosyncrasies while preserving the semantics of the instructions.
"""
def list_all_functions_llil(binary_path, output_file=None):
    """
    List all functions found in a binary file, including their LLIL code.
    
    Args:
        binary_path: Path to the binary file to analyze
        output_file: Optional path to write output to file
    """
    # Prepare the output handling
    if output_file:
        # If output_file doesn't have an extension, add .llil
        if not os.path.splitext(output_file)[1]:
            output_file = output_file + '.llil'
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
        
        # Get the LLIL function object
        llil_function = function.llil
        
        # Sort blocks by start address
        if llil_function is not None:
            sorted_blocks = sorted(llil_function, key=lambda block: block.start)
            
            for block in sorted_blocks:
                #print_output(f"Block at 0x{block.start:x}:")
                
                for instruction in block:
                    # Get the LLIL instruction address
                    llil_address = instruction.address
                    
                    # Get the LLIL instruction text
                    instruction_text = ''
                    for token in instruction.tokens:
                        instruction_text += str(token)
                    
                    # Print the LLIL instruction
                    print_output(f"0x{llil_address:x}: {instruction_text}")
                
                #print_output("-----")
        else:
            print_output("No LLIL available for this function")
    
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
        print("If output_file doesn't have an extension, .llil will be added")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    list_all_functions_llil(binary_path, output_file)