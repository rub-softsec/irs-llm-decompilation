# Distributed Binary Patching (Patcherex2)

This stage involves re-inserting the recompiled C code back into the original V8 binary to verify its behavior. Due to the computational requirements of binary patching and reassembly, this process is designed to run distributed across multiple machines.

## Purpose

To verify the semantic correctness of the decompiled code, we patch the original V8 binary with our recompiled function. If the patched binary passes the V8 test suite (in the next stage), we have high confidence that our decompiled code is functionally equivalent to the original.

## Distributed Architecture

The system uses a master-worker architecture:
*   **Master Node**: Orchestrates the process, distributes files, and aggregates results.
*   **Worker Nodes**: Receive a subset of functions, perform the patching locally, and return the modified binaries.

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

### 2. Initialization (`init.sh`)

Run this on **ALL** machines (master and workers) to install dependencies.

```bash
./init.sh
```

*   **Installs**: `python3`, `patcherex2`, and other tools.
*   **Creates**: Virtual environment `venv`.

### 3. Execution (`scripts/master.sh`)

The master script provides commands to manage the full lifecycle.

#### A. Full Automated Run
```bash
./scripts/master.sh full-run
```
This executes the following steps sequentially:
1.  **Distribute**: Splits input files based on the number of workers.
2.  **Send Base**: Transfers common files (binary, scripts) to workers.
3.  **Send Input**: Transfers the specific chunk of `.c` files to each worker.
4.  **Run**: Starts the patching process on all workers in parallel.

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

## Generated Artifacts

*   `output/`: Directory containing the patched V8 binaries (one per function).
*   `logs/`: Execution logs.

## Requirements

*   **Python 3.12.3**
*   **patcherex2**