# Function Verification Pipeline

This directory contains the final stage of the pipeline, which verifies the semantic correctness of the recompiled functions by executing them against a ground-truth input/output test suite.

## Purpose

To ensure that the decompiled code behaves identically to the original function, we execute the recompiled binaries with predefined input sets and compare the output against the expected ground truth. This is the ultimate test of decompilation accuracy.

## Workflow

### 1. Verification (`main.py`)

Execute the main script to start the verification process.

```bash
python3 main.py
```

*   **Input**: 
    *   `input/`: Directory containing the recompiled object files (usually symlinked or copied from `../4.recompile/output/`).
    *   `json/selected.jsonl`: Metadata file containing the test cases (`real_io_pairs`) and execution wrappers (`real_exe_wrapper`) for each function ID.
*   **Action**: 
    1.  Loads the metadata and input binaries.
    2.  For each binary, creates a C++ test harness that links against the object file.
    3.  Runs the test harness with the input data specified in `real_io_pairs`.
    4.  Compares the execution output with the expected output (`diff_io`).
*   **Output**: 
    *   `output/<path>/<filename>.txt`: Detailed test report for each function.
        *   Contains the pass/fail status for each test case.
        *   "ALL TESTS PASSED" or "SOME TESTS FAILED".

## Generated Artifacts

*   **Test Reports**: Text files summarizing the verification results for each function.

## Acknowledgements

The code within `binarytest` and `jsonl_reader` has been adapted from the original ExeBench.
