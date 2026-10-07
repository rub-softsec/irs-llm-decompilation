# Binary Reassembly Verification

This module verifies that the extracted functions can be successfully patched and reassembled using `patcherex2`. This serves as a critical check for the "reassemblability" of the code samples.

## Purpose

To ensure the integrity of the function selection, we attempt to apply a simple patch (replacing the function body with `return 42`) to every function in our dataset. If `patcherex2` fails to apply this patch or save the binary, it indicates potential issues with the function's control flow graph or boundaries, making it unsuitable for our dataset.

## Workflow

### 1. Execution (`run_pipeline.sh`)

Execute the verification pipeline script.

```bash
./run_pipeline.sh
```

*   **Configuration**: The script automatically locates:
    1.  Binary: `../0.extract_raw_functions/d8`
    2.  Map: `../1.get_usable_functions/map_usable.json`
*   **Action**: Attempts to patch each function in the map.

## Generated Artifacts

*   `output/`: Directory containing the patched binaries (one per function).
*   `logs/`: Individual log files for each patching attempt.
*   `execution_log.txt`: A summary log of the entire execution validation.

## Requirements

*   **Python 3.12.3**
*   **patcherex2**
