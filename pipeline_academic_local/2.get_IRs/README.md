# Get Intermediate Representations (IRs)

This directory constitutes the second stage of the experimental pipeline. It uses the Binary Ninja API to extract Intermediate Representations (IRs) and Disassembly from the compiled binaries generated in the previous stage.

## Purpose

The transformation from binary to high-level code involves multiple layers of abstraction. This stage systematically extracts these layers to provide a comprehensive dataset for analysis. We utilize scripts to extract:

1.  **Assembly (ASM)**: The raw disassembly.
2.  **Low Level IL (LLIL)**: Binary Ninja's low-level intermediate language, close to assembly but normalized.
3.  **Medium Level IL (MLIL)**: A higher level abstraction with variables and types.
4.  **High Level IL (HLIL)**: A pseudo-code representation closest to the original C source.

## Workflow

### 1. Extraction Pipeline (`run.sh`)

The extraction of all IRs is orchestrated by a single shell script that processes the input directory recursively.

```bash
bash run.sh
```

*   **Input**: `input/` directory containing the compiled object files (e.g., `O0/func_id.o`).
*   **Action**: It detects all binaries and runs the following Python scripts on each:
    *   `code/get_asm.py`: Extracts disassembly.
    *   `code/get_llil.py`: Extracts Low Level IL.
    *   `code/get_mlil.py`: Extracts Medium Level IL.
    *   `code/get_hlil.py`: Extracts High Level IL.
*   **Output**:
    *   `output/`: Directory structure mirroring the input, containing the extracted `.asm`, `.llil`, `.mlil`, and `.hlil` files.
    *   `error.txt`: Log of any empty files or processing errors.

## Generated Artifacts

For each input binary (e.g., `func_id.o`), this directory generates the following corresponding files:

*   `*.asm`: Disassembly text.
*   `*.llil`: Low Level Intermediate Language text.
*   `*.mlil`: Medium Level Intermediate Language text.
*   `*.hlil`: High Level Intermediate Language text.
