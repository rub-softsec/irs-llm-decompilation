# Error Taxonomy Analysis

This directory contains the framework for analyzing and categorizing errors encountered during the LLM-based decompilation process. The analysis is divided into two distinct phases: **Static Analysis** (Compilation Errors) and **Dynamic Analysis** (Execution Errors).

## Structure

*   **error_compilation/**: Scripts for analyzing compiler errors (GCC/Clang output). Focuses on syntax, type mismatches, linker errors, etc.
*   **error_execution/**: Scripts for analyzing runtime behavior. Focuses on logic errors, crashes, and timeouts by parsing execution logs.

---

## Usage

To use these analysis scripts, you must set up your input data in a specific directory structure. The scripts are designed to process data across multiple experimental iterations.

### 1. Data Setup

For both `error_compilation` and `error_execution`, you need to create an `input` directory inside the respective folder.

**Required Directory Hierarchy:**

```text
[error_taxonomy_analysis]
├── error_compilation/
│   ├── input/                  <-- You must create this
│   │   ├── iteration_1/        <-- Iteration ID
│   │   │   ├── Model_Name/
│   │   │   │   ├── IR_Type/       <-- e.g., 'asm', 'llil'
│   │   │   │   │   ├── Opt_Level/ <-- e.g., 'no_opt', 'O2'
│   │   │   │   │   │   ├── file1.error  <-- Compiler output files
│   │   │   │   │   │   └── ...
│   │   └── ...
├── error_execution/
    ├── input/                  <-- You must create this
        ├── iteration_1/
            ├── ... (same hierarchy)
                ├── ...
                    ├── file1.txt    <-- Execution logs
```

*   **Input Files**:
    *   For **Compilation**: Place `.error` files containing standard error output from the compiler.
    *   For **Execution**: Place `.txt` files containing the execution log.

### 2. Running the Analysis

#### Compilation Error Analysis

Navigate to `error_compilation/` and run the scripts:

1.  **Detailed Analysis (per iteration)**:
    ```bash
    cd error_compilation
    python3 error_taxonomy.py
    ```
    *   **Function**: Analyzes errors while preserving the iteration structure.
    *   **Output**: Generates `detailed_error_taxonomy_by_iteration.json` and reorganizes files into `output/`.

2.  **Consolidated Analysis (aggregated)**:
    ```bash
    python3 error_taxonomy_by_all.py
    ```
    *   **Function**: Ignores iterations and groups stats solely by Model/IR/Optimization. Useful for overall performance views.
    *   **Output**: Generates `consolidated_error_taxonomy.json`.

#### Execution Error Analysis

Navigate to `error_execution/` and run the scripts (same logic applies):

1.  **Detailed Analysis**:
    ```bash
    cd error_execution
    python3 error_taxonomy.py
    ```
    *   **Distinction**: Separates files into `allfailed` (0% pass) and `partialfailed` categories.

2.  **Consolidated Analysis**:
    ```bash
    python3 error_taxonomy_by_all.py
    ```

### 3. Generated Outputs

Running the scripts will create an `output/` directory and several JSON reports:

*   **output/** (Directory):
    *   Contains the original error files reorganized by their taxonomy category (e.g., `output/syntax/...`).
    *   Useful for manually inspecting specific classes of errors.

*   **JSON Reports**:
    *   `detailed_error_taxonomy_by_iteration.json`: Full hierarchical breakdown: `Iteration -> Model -> IR -> Opt -> Category -> Counts`.
    *   `consolidated_error_taxonomy.json`: Aggregated breakdown: `Model -> IR -> Opt -> Category -> Counts`.
    *   `iteration_comparison.json`: Statistics comparing error distributions across different iterations.
    *   `error_summary*.json`: High-level summary of total errors processed.

## Requirements

*   **Python 3.12.3**