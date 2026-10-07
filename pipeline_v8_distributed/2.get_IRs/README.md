# Get Intermediate Representations (IRs) - V8

This directory constitutes the second stage of the V8 pipeline. Unlike the academic pipeline which processes multiple small object files, this stage extracts Intermediate Representations (IRs) directly from a single large V8 binary (`d8`).

## Purpose

To prepare the data for LLM decompilation, we extract the specific functions identified during the dataset building phase. We use the Binary Ninja API to load the `d8` binary and extract the IRs for each function address listed in the `selected.json` map.

## Workflow

### 1. IR Extraction (`run.sh`)

Execute the shell script to run the extraction for all IR types sequentially.

```bash
./run.sh
```

Which executes:
1.  `python3 code/get_asm.py`: Extracts raw Assembly.
2.  `python3 code/get_llil.py`: Extracts Low Level IL.
3.  `python3 code/get_mlil.py`: Extracts Medium Level IL.
4.  `python3 code/get_hlil.py`: Extracts High Level IL.

*   **Input**: 
    *   `input/d8`: The compiled V8 binary.
    *   `input/selected.json`: The map of selected functions and their addresses.
*   **Output**: 
    *   `output/asm/*.asm`
    *   `output/llil/*.llil`
    *   `output/mlil/*.mlil`
    *   `output/hlil/*.hlil`
    *   `*.error`: Error logs for any failed extractions.

## Generated Artifacts

*   **IR Files**: Text-based representations of the code at four levels of abstraction.
*   **Error Logs**: Records of functions that could not be analyzed or extracted.

## Requirements

*   **Python 3.12.3**
*   **BinaryNinja**
