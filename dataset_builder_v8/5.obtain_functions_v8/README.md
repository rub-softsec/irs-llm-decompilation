# Obtain V8 Functions

This step extracts the original Pseudo-C source code for the "Covered" functions identified in the previous step.

## Purpose

We only want to train/evaluate our models on functions that are actively tested by V8's test suite. Since `map_covered.json` contains the list of functions that, when broken, cause test failures, these are our ground truth functions. This script uses BinaryNinja to extract their decompiled code.

## Workflow

### 1. Source Extraction (`get_c.py`)

Run the script to extract the Pseudo-C code for the identified functions.

```bash
python get_c.py /path/to/d8
```

*   **Input**: 
    *   `/path/to/d8`: The original V8 binary.
    *   `../4.analyze_logs/map_covered.json`: The list of target functions.
*   **Output**: 
    *   `output/*.c`: Extracted Pseudo-C files.

## Generated Artifacts

*   `output/`: Directory containing the verified Pseudo-C source files.

## Requirements

*   **BinaryNinja**
