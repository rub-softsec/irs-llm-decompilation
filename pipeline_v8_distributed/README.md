# V8 Distributed Pipeline

This directory contains the experimental pipeline adapted for the V8 dataset. It is functionally similar to the [Academic Pipeline](../pipeline_academic_local/), but with specific modifications to handle the pre-compiled V8 binaries and distributed processing requirements.

## Pipeline Stages

### 1. [SKIPPED] Get Binaries
This stage is omitted in this pipeline. The V8 binaries and target function selection are handled upstream by the [V8 Dataset Builder](../dataset_builder_v8/). The output (`d8` binary and `selected.json`) serves as the input for Stage 2.

### [2.get_IRs](./2.get_IRs)
Extracts Intermediate Representations (IRs) directly from the provided `d8` binary using the function addresses specified in the selection map. It produces Assembly (ASM), Low Level IL (LLIL), Medium Level IL (MLIL), and High Level IL (HLIL).

### [3.queries_LLMs](./3.queries_LLMs)
Queries various LLMs to decompile the extracted IRs. This stage is configured for distributed processing to handle the large scale of the V8 dataset.

### [4.recompile](./4.recompile)
Attempts to recompile the LLM-generated C code back into object files, verifying syntactic correctness and valid C code generation.

### [5.patcherex2](./5.patcherex2)
**Distributed Stage.**
Patches the original V8 binary with the recompiled functions. This stage uses a master-worker architecture to distribute the binary rewriting workload across multiple machines.

### [6.V8_testing_suite](./6.V8_testing_suite)
**Distributed Stage.**
Verifies the semantic correctness of the decompiled code by running the official V8 test suite against the patched binaries.

## Requirements

*   **Python 3.12.3**
*   **BinaryNinja 5.1.8104**
*   **patcherex2 0.2.9**
