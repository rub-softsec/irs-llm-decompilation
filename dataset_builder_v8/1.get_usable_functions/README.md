# Function Verification

This step serves as a validation layer between raw function extraction and subsequent processing. It verifies that for every function listed in our filtered map, a corresponding decompiled C file exists on the filesystem.

## Purpose

The previous step (`0.extract_raw_functions`) generates a list of filtered functions and attempts to decompile them. However, decompiler errors or interruptions might result in missing files. This script ensures that the dataset pipeline only proceeds with functions that have valid source files available for analysis.

## Workflow

### 1. Verification (`filter.py`)

Run the verification script to check for file existence and generate a clean list of usable functions.

```bash
python filter.py
```

*   **Default Input**: 
    *   Map: `../0.extract_raw_functions/map_filtered.json`
    *   Source Directory: `../0.extract_raw_functions/output_c/`
*   **Custom Input**:
    ```bash
    python filter.py --input_map /path/to/map.json --input_dir /path/to/dir --output_map map.json
    ```

## Generated Artifacts

*   `map_usable.json`: A JSON list of functions that have been confirmed to exist and are ready for the next stage.
