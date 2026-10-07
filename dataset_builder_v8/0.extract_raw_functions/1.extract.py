import angr
import os
import sys
import json

def extract_functions(binary_path, output_dir='output'):
    """
    Extracts all functions from a binary file using angr and saves their disassembly.

    This function analyzes the control flow graph (CFG) of the provided binary to identify
    functions. It then disassembles each function block using Capstone and saves the
    assembly code to individual .asm files. It also generates a JSON mapping of function
    names to their entry addresses.

    Args:
        binary_path (str): The file path to the target binary (e.g., 'd8').
        output_dir (str): The directory where the extracted assembly files will be saved.
                          Defaults to 'output'.

    Returns:
        None: The function writes output files directly to the disk.
    """
    # Create output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the binary using angr
    print(f"[*] Loading binary: {binary_path}")
    project = angr.Project(binary_path, auto_load_libs=False)
    
    # Generate the Control Flow Graph (CFG) to identify functions
    # CFGFast is usually sufficient and faster than CFGAccurate
    print("[*] Analyzing binary...")
    cfg = project.analyses.CFGFast()
    
    print(f"[+] Found {len(cfg.functions)} functions\n")
    
    # Initialize list to store function metadata for the mapping file
    function_map = []
    
    # Iterate through all identified functions in the CFG
    for addr, func in cfg.functions.items():
        # Exclude PLT (Procedure Linkage Table) entries and SimProcedures (simulated functions)
        # We are only interested in actual user/library code within the binary
        if func.is_plt or func.is_simprocedure:
            continue
        
        # Record function details for the map
        function_map.append({
            "name": func.name,
            "addr": hex(addr)
        })
        
        # Sanitize the function name to be safe for use as a filename
        # Replace typically problematic characters like slashes
        func_name = func.name.replace('/', '_').replace('\\', '_')
        output_path = os.path.join(output_dir, f"{func_name}.asm")
        
        try:
            # Write the disassembly of the function to a file
            with open(output_path, 'w') as f:
                # Write header information
                f.write(f"; Function: {func.name}\n")
                f.write(f"; Address: {hex(addr)}\n")
                f.write(f"; Size: {func.size} bytes\n\n")
                
                # Iterate through each basic block in the function
                for block in func.blocks:
                    # Write block label
                    f.write(f"block_{hex(block.addr)}:\n")
                    
                    # Disassemble the block using Capstone engine
                    disasm = block.capstone.insns
                    for insn in disasm:
                        f.write(f"  {insn.mnemonic} {insn.op_str}\n")
                    f.write("\n")
            
            print(f"[+] Extracted: {func_name}")
        
        except Exception as e:
            # Log any errors encountered during extraction of a specific function
            print(f"[-] Error extracting {func_name}: {e}")
    
    # Save the function mapping to a JSON file in the current directory
    map_path = os.path.join('.', 'map.json')
    with open(map_path, 'w') as f:
        json.dump(function_map, f, indent=2)
    
    print(f"\n[+] Function map saved to {map_path}")
    print(f"[*] Done! Functions saved to {output_dir}/")

if __name__ == "__main__":
    # Ensure correct command line usage
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <binary>")
        sys.exit(1)
    
    # Run the extraction process
    extract_functions(sys.argv[1])