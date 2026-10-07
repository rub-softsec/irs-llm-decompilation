import binaryninja
import sys
import os

"""
Script to extract Assembly code from binaries using Binary Ninja API.

This script loads a binary file and iterates through all its functions to extract
the raw disassembly instructions.
"""
def list_all_functions(binary_path, output_file=None):
    """
    List all functions found in a binary file, including their assembly code.
    
    Args:
        binary_path: Path to the binary file to analyze
        output_file: Optional path to write output to file
    """
    # Prepare the output handling
    if output_file:
        # If output_file doesn't have an extension, add .asm
        if not os.path.splitext(output_file)[1]:
            output_file = output_file + '.asm'
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
        print_output(f"Architecture: {bv.arch.name}")
        print_output(f"Entry Point: 0x{function.start:x}")
        print_output("code:")
        
        # Sort blocks by start address
        sorted_blocks = sorted(function, key=lambda block: block.start)
        
        for block in sorted_blocks:
            #print_output(f"Block at 0x{block.start:x}:")
            asm_address = block.start
            
            for instruction in block:
                # In recent versions of Binary Ninja, you can get the disassembled text like this:
                instruction_text = ''
                for token in instruction[0]:
                    instruction_text = instruction_text + str(token).replace('\n', '')
                
                print_output(f"0x{asm_address:x}: {instruction_text}")
                asm_address = asm_address + instruction[1]
            
            #print_output("-----")
    
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
        print("If output_file doesn't have an extension, .asm will be added")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    list_all_functions(binary_path, output_file)