#!/usr/bin/env python3
"""
Script to filter ASM files that don't contain any function calls or external jumps.

This module automates the process of identifying and selecting "self-contained" functions
from a set of disassembled assembly files. A self-contained function is defined as one that:
1. Does not contain any `call` instructions (no sub-function invocations).
2. Does not contain jumps to external addresses (only internal control flow).
3. Does not utilize dynamic register-based jumps (which imply unknown targets).

The script reads .asm files from an input directory, checks these conditions, and copies
the passing files to an output directory. It also generates a filtered JSON mapping file.
"""

import os
import json
import re
from pathlib import Path


def extract_blocks(content):
    """
    Extracts all basic block addresses defined in the ASM file.

    It specifically looks for labels in the format `block_0x...:` which mark the start
    of basic blocks in the generated assembly.

    Args:
        content (str): The full content of the ASM file.

    Returns:
        set: A set of block addresses (as hex strings, lowercase, without '0x' prefix)
             present in the file.
    """
    blocks = set()
    # Regex to capture the address part of a block label (e.g., block_0x1234:)
    block_pattern = r'^block_(0x[0-9a-fA-F]+):'
    
    for line in content.splitlines():
        match = re.match(block_pattern, line.strip())
        if match:
            # Extract the address (e.g., "0x314b9c0")
            block_addr = match.group(1)
            blocks.add(block_addr.lower())
    
    return blocks


def is_register_jump(operand):
    """
    Checks if a jump operand involves a register (direct or indirect).

    Register-based jumps (e.g., `jmp rax` or `jmp [rax]`) are considered external or
    unresolved control flow for the purpose of this analysis, as the target cannot be
    statically determined easily.

    Args:
        operand (str): The operand string from a jump instruction.

    Returns:
        bool: True if the operand involves a register, False otherwise.
    """
    # List of common x86-64 registers to check against
    registers = [
        'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
        'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
        'ax', 'bx', 'cx', 'dx', 'si', 'di', 'bp', 'sp',
        'al', 'bl', 'cl', 'dl', 'ah', 'bh', 'ch', 'dh'
    ]
    
    operand_lower = operand.lower().strip()
    
    # Check for direct register jumps (e.g., "jmp rax")
    if operand_lower in registers:
        return True
    
    # Check for indirect register jumps (e.g., "jmp qword ptr [rax]", "jmp [rcx]")
    # Looking for register names within brackets or pointer arithmetic
    for reg in registers:
        if reg in operand_lower and ('[' in operand_lower or 'ptr' in operand_lower):
            return True
    
    return False


def contains_external_jumps(file_path):
    """
    Checks if an ASM file contains any external jumps.

    External jumps are defined as:
    1. Jumps to fixed addresses that are NOT defined as block labels within the file itself.
    2. Jumps to dynamic targets (register-based).

    Args:
        file_path (str or Path): Path to the ASM file to analyze.

    Returns:
        bool: True if the file contains external jumps, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # First, map all valid internal jump targets (block addresses)
        blocks = extract_blocks(content)
        
        # Regex to match all jump instructions (conditional and unconditional)
        # Matches: jmp, je, jne, ja, jae, jb, jbe, jg, jge, jl, jle, jo, jno, js, jns, jz, jnz, etc.
        jump_pattern = r'^\s*(j[a-z]{1,3})\s+(.+)$'
        
        for line in content.splitlines():
            # Strip comments (start with ;)
            line = line.split(';')[0].strip()
            
            match = re.match(jump_pattern, line, re.IGNORECASE)
            if match:
                # instruction = match.group(1).lower() # Unused, but extracted for clarity
                operand = match.group(2).strip()
                
                # Case 1: Dynamic/Register jumps are assumed external/unsafe
                if is_register_jump(operand):
                    return True
                
                # Case 2: Fixed address jumps
                # Extract address from operand (e.g., "0x314ba17")
                addr_match = re.search(r'0x[0-9a-fA-F]+', operand)
                if addr_match:
                    jump_addr = addr_match.group(0).lower()
                    
                    # Verify if this address exists as a block within this file
                    if jump_addr not in blocks:
                        return True
        
        return False
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return True  # Fail safe: if we can't read it, assume it's invalid


def contains_call_instruction(file_path):
    """
    Checks if an ASM file contains any 'call' instructions.

    Any function call implies a dependency on external code or other functions,
    making the function not self-contained.

    Args:
        file_path (str or Path): Path to the ASM file.

    Returns:
        bool: True if file contains call instructions, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to match call instructions (direct and indirect)
        # Matches: call <target>, call qword ptr [...], call dword ptr [...], etc.
        call_pattern = r'^\s*call\s+'
        
        for line in content.splitlines():
            # Strip comments
            line = line.split(';')[0].strip()
            
            # Check for call instruction
            if re.match(call_pattern, line, re.IGNORECASE):
                return True
                
        return False
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return True  # Fail safe


def load_map_json(map_file='map.json'):
    """
    Loads the initial function mapping from a JSON file.

    Args:
        map_file (str): Path to the map.json file.

    Returns:
        list: A list of function entry dictionaries, or None if loading fails.
    """
    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Warning: '{map_file}' not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{map_file}': {e}")
        return None
    except Exception as e:
        print(f"Error reading '{map_file}': {e}")
        return None


def save_filtered_map(filtered_functions, output_file='map_filtered.json'):
    """
    Saves the list of filtered functions to a new JSON file.

    Args:
        filtered_functions (list): The list of function entries that passed validation.
        output_file (str): Path to the output JSON file.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_functions, f, indent=2)
        print(f"✓ Created: {output_file}")
    except Exception as e:
        print(f"Error writing '{output_file}': {e}")


def filter_asm_files(input_dir='output', output_dir='output_filtered', 
                     map_file='map.json', output_map='map_filtered.json'):
    """
    Main driver function to filter ASM files and generate a clean dataset.

    It iterates through all .asm files in the input directory, checks them against
    the self-contained criteria (no calls, no external jumps), and copies valid
    files to the output directory. It also updates the function mapping JSON.

    Args:
        input_dir (str): Directory containing source .asm files.
        output_dir (str): Directory to store filtered .asm files.
        map_file (str): Path to the input map.json file.
        output_map (str): Path to the output filtered map.json file.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Validation: Check if input directory exists
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True)
    
    # Load original mapping data
    map_data = load_map_json(map_file)
    
    # Find all .asm files in the input directory
    asm_files = list(input_path.glob('*.asm'))
    
    if not asm_files:
        print(f"No .asm files found in '{input_dir}'")
        return
    
    print(f"Found {len(asm_files)} .asm files in '{input_dir}'")
    print(f"Processing files...\n")
    
    filtered_count = 0
    skipped_call_count = 0
    skipped_jump_count = 0
    filtered_functions = []
    
    # Track names of functions that pass all quality filters
    functions_passing_filters = set()
    
    # Process each ASM file individually
    for asm_file in asm_files:
        function_name = asm_file.stem  # Extract filename without extension
        
        has_calls = contains_call_instruction(asm_file)
        has_external_jumps = contains_external_jumps(asm_file)
        
        if not has_calls and not has_external_jumps:
            # File passes all checks; copy to output directory
            output_file = output_path / asm_file.name
            
            try:
                with open(asm_file, 'r', encoding='utf-8') as src:
                    content = src.read()
                
                with open(output_file, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                
                filtered_count += 1
                functions_passing_filters.add(function_name)
                print(f"✓ Copied: {asm_file.name}")
                
            except Exception as e:
                print(f"✗ Error copying {asm_file.name}: {e}")
        else:
            # File failed checks; log the reason
            if has_calls:
                skipped_call_count += 1
                print(f"✗ Skipped (contains call): {asm_file.name}")
            elif has_external_jumps:
                skipped_jump_count += 1
                print(f"✗ Skipped (contains external jump): {asm_file.name}")
    
    # Filter the original map JSON to include only valid functions
    if map_data is not None:
        print(f"\nFiltering map.json...")
        
        for entry in map_data:
            if 'name' in entry and entry['name'] in functions_passing_filters:
                filtered_functions.append(entry)
        
        # Save the new filtered map
        save_filtered_map(filtered_functions, output_map)
        
        print(f"✓ Filtered map contains {len(filtered_functions)} entries")
    else:
        print("\nSkipping map.json filtering (file not available)")
    
    # Print execution summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    print(f"  Total .asm files processed: {len(asm_files)}")
    print(f"  Files copied (passing all filters): {filtered_count}")
    print(f"  Files skipped (has calls): {skipped_call_count}")
    print(f"  Files skipped (has external jumps): {skipped_jump_count}")
    print(f"  Output directory: '{output_dir}'")
    if map_data is not None:
        print(f"  Original map entries: {len(map_data)}")
        print(f"  Filtered map entries: {len(filtered_functions)}")
        print(f"  Filtered map file: '{output_map}'")
    print(f"{'='*60}")


if __name__ == "__main__":
    # Standard entry point: define paths and run filter
    filter_asm_files(
        input_dir='output',
        output_dir='output_filtered',
        map_file='map.json',
        output_map='map_filtered.json'
    )