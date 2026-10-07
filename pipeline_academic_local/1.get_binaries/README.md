# Get Binaries

This directory contains the first stage of the pipeline, focused on compiling the selected C functions into object files using different GCC optimization levels.

## Purpose

The `main.py` script takes the selected dataset (which ensures a balanced distribution of code complexity) and compiles each function to object files. This process creates the ground truth binary artifacts that will be used for disassembly and decompilation in subsequent stages.

## Workflow

### 1. Compilation (`main.py`)

Execute the compilation script to process the input dataset and generate object files across multiple optimization levels.

```bash
python3 main.py
```

*   **Input**: `input/selected.jsonl` containing:
    *   `id`: Unique identifier for the function.
    *   `func_def`: The C source code.
    *   `real_deps`: Required headers.
*   **Action**: Iterates through the dataset and compiles each function using `gcc` with `-O0`, `-O1`, `-O2`, and `-O3` flags.
*   **Output**: 
    *   `output/`: Directory structure containing the object files.
    *   `error.txt`: Log of any compilation failures.

## Generated Artifacts

This directory will produce the following artifacts (organized by optimization level):

*   `output/O0/*.o`: Object files compiled with `-O0`.
*   `output/O1/*.o`: Object files compiled with `-O1`.
*   `output/O2/*.o`: Object files compiled with `-O2`.
*   `output/O3/*.o`: Object files compiled with `-O3`.
