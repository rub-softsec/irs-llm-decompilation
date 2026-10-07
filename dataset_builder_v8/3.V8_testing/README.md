# V8 Testing Suite

This module executes the V8 testing suite on the patched binaries to verify that the modifications didn't break V8's core functionality.

## Purpose

The main objective of this step is to determine the impact of the **dummy implementation** applied in Step 2. We want to distinguish between:

*   **Critical Functions**: Those that, when replaced by a dummy, cause V8 to crash or fail its test suite.
*   **Non-Critical/Unused Functions**: Those that can be replaced without affecting the execution of the standard V8 test suite.

## Workflow

### 1. Local Testing (`run_tests.sh`)

Run the standard V8 test suite against each patched binary.

```bash
./run_tests.sh
```

*   **Input**: Defaults to `../2.patchterex_execution/output` (patched binaries).
*   **Requirements**: `v8_dir.zip` (containing the V8 test environment) must be in the current directory.
*   **Configuration**: Set `MAX_PARALLEL` in the script to adjust worker count.

## Generated Artifacts

*   `output/`: Contains the test results for each binary.
*   `logs/`: Detailed execution logs.
*   `execution_log.txt`: Summary of testing.
