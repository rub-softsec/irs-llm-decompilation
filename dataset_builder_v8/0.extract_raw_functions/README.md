# V8 Function Extraction & Selection Pipeline

This directory contains the initial stage of the data processing pipeline for V8 functions. The goal of this stage is to extract raw functions from the V8 `d8` binary, filter them for self-containment (no external dependencies), and generate decompiled C code for further complexity analysis.

## Purpose

The V8 `d8` binary contains thousands of functions. To create a clean dataset for decompilation, we must identify functions that are self-contained and extract their ground truth assembly and pseudo-C code.

## Workflow

### 1. Function Extraction (`1.extract.py`)

This script uses `angr` to analyze the binary and extract all identified functions into individual assembly files.

```bash
python 1.extract.py <path_to_d8_binary>
# Example: python 1.extract.py ./d8
```

*   **Action**: Analyzes the Control Flow Graph (CFG) of the binary and writes the assembly of each function to disk.
*   **Output**: 
    *   `output/`: Directory containing raw `.asm` files.
    *   `map.json`: A JSON mapping of function names to their entry addresses.

### 2. Filtering (`2.filter.py`)

This script filters the extracted functions to ensure they are self-contained.

```bash
python 2.filter.py
```

*   **Action**: Scans the `.asm` files and removes any functions that contain:
    *   `call` instructions (dependencies on other functions).
    *   Jumps to external addresses or register-based jumps (unresolved control flow).
*   **Input**: `output/` directory and `map.json`.
*   **Output**: 
    *   `output_filtered/`: Directory containing only the valid, self-contained `.asm` files.
    *   `map_filtered.json`: A filtered version of the function mapping.

### 3. Pseudo-C Extraction (`3.get_c.py`)

This script uses BinaryNinja to decompile the filtered functions into Pseudo-C.

```bash
python 3.get_c.py <path_to_d8_binary>
# Example: python 3.get_c.py ./d8
```

*   **Action**: Loads the binary in BinaryNinja, navigates to the addresses of the filtered functions, and exports their High-Level IL (HLIL) representation.
*   **Input**: `map_filtered.json` and the `d8` binary.
*   **Output**: 
    *   `output_c/`: Directory containing `0x<address>.c` files.

## Generated Artifacts

This directory produces the following artifacts (excluded from version control):

*   `output/*.asm`: Raw assembly files.
*   `output_filtered/*.asm`: Filtered assembly files.
*   `output_c/*.c`: Decompiled C source files.
*   `map.json` & `map_filtered.json`: Intermediate mapping files.

## Requirements

*   **Python 3.12.3**
*   **angr**: `pip install angr`
*   **capstone**: `pip install capstone`
*   **BinaryNinja**: Valid commercial license required.
