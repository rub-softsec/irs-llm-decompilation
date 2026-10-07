# V8 Testing Suite (Distributed)

This stage involves running the standard V8 test suite against the patched binaries generated in the previous stage (`5.patcherex2`).
## Purpose

To validate the semantic correctness of decompilation by ensuring the patched V8 binary passes the official V8 tests suite.

## Distributed Architecture

Similar to the previous stage, this process uses a master-worker architecture:
*   **Master Node**: Orchestrates the process, distributes binary files, and aggregates test results.
*   **Worker Nodes**: Receive binary files, setup a local V8 environment, run tests, and report results.

## Workflow

The entire process is controlled via `scripts/master.sh` on the master node.

### 1. Configuration (`machines.json`)

You must create a `machines.json` file in this directory to define your cluster.
**Note: This file is git-ignored for security.**

```json
[
    {"id": 1, "ip": "192.168.1.101"},
    {"id": 2, "ip": "192.168.1.102"},
    ...
]
```

### 2. Execution (`scripts/master.sh`)

The master script provides commands to manage the full lifecycle.

#### A. Full Automated Run
```bash
./scripts/master.sh full-run
```
This executes the following steps:
1.  **Distribute**: Splits binary files from `input/` based on the number of workers.
2.  **Send Base**: Transfers common files (scripts, `v8_dir.zip`) to workers.
3.  **Send Input**: Transfers the specific chunk of binaries to each worker.
4.  **Run**: Starts the testing process on all workers in parallel.

#### B. Manual Control
You can also run steps individually:
```bash
./scripts/master.sh distribute
./scripts/master.sh send-all
./scripts/master.sh run-all
./scripts/master.sh check-all    # Check status
./scripts/master.sh retrieve-all # Download results
./scripts/master.sh clean-all    # Cleanup remote workspaces
```

## Local Execution (Single Machine)

If you do not need distributed processing, you can run `main.sh` directly:

```bash
./main.sh
```

**Prerequisites**:
- `input/` directory should contain the patched V8 binaries.
- You must have `v8_dir.zip` (the `v8/` compressed directory) in this directory containing the V8 build environment and `run_test_v8.sh` which has the following code:
```bash
#!/bin/bash

tools/run-tests.py --outdir=out/x64.release mjsunit mozilla benchmarks test262 debugger intl wasm-js wasm-spec-tests webkit --exit-after-n-failures=1
```

## Generated Artifacts

*   `output/`: Directory containing test output logs for each binary.
*   `logs/`: Execution logs.

## Requirements

*   **V8 Build Environment**: A pre-built V8 environment compressed as `v8_dir.zip`.