# Academic Decompilation Pipeline

This directory contains the complete experimental pipeline used to evaluate the capabilities of Large Language Models (LLMs) in decompiling binary code. The pipeline is structured into five sequential stages, each handling a specific aspect of the workflow from binary compilation to semantic verification.

## Stages

### [1.get_binaries](./1.get_binaries) 
Compiles selected C functions into object files using various optimization levels (O0, O1, O2, O3).

### [2.get_IRs](./2.get_IRs)
Extracts Intermediate Representations (IRs) from the compiled binaries using the Binary Ninja API. It produces Assembly (ASM), Low Level IL (LLIL), Medium Level IL (MLIL), and High Level IL (HLIL).

### [3.queries_LLMs](./3.queries_LLMs)
Queries various LLMs (e.g., GPT-4, Claude) with the extracted IRs to generate decompiled C code, managing batch processing and API interactions.

### [4.recompile](./4.recompile)
Attempts to recompile the LLM-generated C code into object files to verify syntactic correctness and compilability.

### [5.test](./5.test)
Verifies the semantic correctness of the recompiled functions by executing the code against a test suite with known input/output pairs.

## Usage

Each subdirectory is self-contained with its own `README.md` and `main.py` script. Please follow the instructions in each directory's documentation to execute the specific stage of the pipeline.

## Dependencies

*   **Python 3.12.3**
*   **gcc 13.3.0**
*   **BinaryNinja 5.1.8104**

