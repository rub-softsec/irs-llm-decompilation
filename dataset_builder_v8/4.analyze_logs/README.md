# Log Analysis and Classification

This step processes the testing results from `3.V8_testing` to classify the functions into two categories.

## Purpose

To build our dataset, we need to understand which functions are effectively verified by the V8 test suite.

*   **Not Covered / Non-Essential (`map_uncovered.json`)**: Functions where replacing them with a dummy (`return 42`) **did NOT cause V8 to fail**. This implies the test suite does not cover these functions (or they are trivial).
*   **Covered / Essential (`map_covered.json`)**: Functions where replacing them with a dummy **caused V8 to fail**. This means the test suite actively exercises these functions, making them ideal candidates for our dataset.

## Workflow

### 1. Classification (`classify_results.py`)

Run the analysis script to parse the logs and generate the classification maps.

```bash
python classify_results.py
```

*   **Default Input**:
    *   Logs: `../3.V8_testing/logs`
    *   Map: `../1.get_usable_functions/map_usable.json`
*   **Custom Input**:
    ```bash
    python classify_results.py --log_dir /path/to/logs --input_map /path/to/map.json
    ```

## Generated Artifacts

*   `map_uncovered.json`: JSON list of non-critical functions.
*   `map_covered.json`: JSON list of critical functions (ground truth candidates).
