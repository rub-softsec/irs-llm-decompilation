# V8 Dataset Builder Pipeline

This directory contains the complete pipeline for creating our dataset of V8 functions for decompilation analysis. The pipeline automates the extraction, verification, testing, and selection of functions from the V8 JavaScript engine.

## Stages

### [0. Extract Raw Functions](./0.extract_raw_functions/README.md)
Extracts all functions from the `d8` binary and filters them to ensure they are self-contained (no `call` instructions or external jumps).

### [1. Verify Existence](./1.get_usable_functions/README.md)
Verifies that the decompiled Pseudo-C source files were successfully generated for all filtered functions.

### [2. Reassembly Verification & Patching](./2.patchterex_execution/README.md)
Verifies that the functions can be re-assembled by applying a patch (replacing the function body with a dummy `return 42` implementation). This step produces the modified binaries.

### [3. V8 Testing](./3.V8_testing/README.md)
Runs the V8 test suite using the patched binaries from Step 2. This identifies which functions are critical (cause test failures when replaced) and which are not covered by tests.

### [4. Log Analysis](./4.analyze_logs/README.md)
Analyzes the testing logs to classify functions into:
*   **Covered (Critical)**: Functions that caused failures (Good candidates, as potential decompilation errors will likely be caught).
*   **Not Covered (Non-Essential)**: Functions where the dummy implementation passed (Bad candidates, as correctness cannot be easily verified).

### [5. Source Extraction](./5.obtain_functions_v8/README.md)
Extracts the final Pseudo-C source code specifically for the "Covered" functions identified in the previous step.

### [6. Selection & Metrics](./6.select_functions_v8/README.md)
Calculates Halstead complexity metrics for the verified functions and performs stratified sampling to ensure the final dataset is diverse and balanced.

## Important Note on Reproducibility

**Compiling your own V8 binary is required.**

Due to V8 build process, internal function names and addresses change with every compilation. Therefore, it is not possible to provide a static list of "target functions" that will work across different builds.

However, this pipeline allows you to generate a dataset **statistically equivalent** to the one used in our experiments.

## Requirements

*   **Python 3.12.3**
*   **gcc 13.3.0**
*   **V8 engine 14.4.0**
*   **BinaryNinja 5.1.8104**
*   **patcherex2 0.2.9**
