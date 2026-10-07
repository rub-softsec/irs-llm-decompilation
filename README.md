# Hierarchical IRs for LLM-Based Decompilation

![Python](https://img.shields.io/badge/python-3.12-blue)
[![License: GPL v3](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)

This repository contains the code that evaluates LLM-based binary decompilation from hierarchical intermediate representations (IRs) and disassembly. Modern decompilers build a hierarchy of IRs to progressively recover source code from a binary, yet existing LLM-based approaches largely treat decompilation as a flat translation from raw disassembly. The pipelines in this repository measure how lifting the abstraction level of the compiled code affects the quality of the decompiled code across four commercial LLMs (`GPT-4.1`, `GPT-4o-mini`, `Claude Sonnet 4`, and `Claude 3.5 Haiku`), four representation levels extracted with Binary Ninja (disassembly, LLIL, MLIL, and HLIL), and four compiler optimization levels (`-O0` to `-O3`).

The two pipelines, one for an academic dataset built from ExeBench and one for the V8 JavaScript engine, follow five stages, from source code compilation or binary acquisition, through IR extraction and LLM decompilation, to recompilation and functional testing. The failures observed in the recompilation and testing stages are classified with a hierarchical error taxonomy that separates compilation errors, detected statically by the compiler, from runtime errors, detected dynamically by the tests.

## Repository Structure

### [dataset_builder_academic](./dataset_builder_academic)
Builds the academic dataset. It computes the Halstead Difficulty of the ExeBench functions and selects a stratified sample of them by difficulty.

### [dataset_builder_v8](./dataset_builder_v8)
Builds the V8 dataset. It extracts the leaf functions of the `d8` binary, verifies their test coverage by patching each one with a dummy implementation and running the V8 test suite, and samples the covered functions by Halstead Difficulty.

### [pipeline_academic_local](./pipeline_academic_local)
Runs the five-stage pipeline on the academic dataset on a single machine, from compilation at the four optimization levels and IR extraction to LLM decompilation, recompilation, and unit testing.

### [pipeline_v8_distributed](./pipeline_v8_distributed)
Runs the pipeline on the V8 dataset. It extracts the IRs from the `d8` binary, queries the LLMs, recompiles their output and, in its distributed stages, patches the recompiled functions into the original binary with Patcherex2 and runs the V8 test suite against the patched binaries.

### [error_taxonomy_analysis](./error_taxonomy_analysis)
Classifies the failures of both pipelines with the hierarchical error taxonomy, compilation errors from the compiler output and runtime errors from the execution logs.

Each directory is self-contained and documents its own usage in its `README.md`.

## Software Environment

The experiments were run with the following tools and versions.

| Tool | Version |
|---|---|
| Python | 3.12.3 |
| GCC | 13.3.0 |
| Binary Ninja | 5.1.8104 |
| Patcherex2 | 0.2.9 |
| V8 JavaScript engine | 14.4.0 |

The LLMs were queried through their public APIs at the following snapshots.

| Model | API snapshot |
|---|---|
| GPT-4.1 | `gpt-4.1-2025-04-14` |
| GPT-4o-mini | `gpt-4o-mini-2024-07-18` |
| Claude Sonnet 4 | `claude-sonnet-4-20250514` |
| Claude 3.5 Haiku | `claude-3-5-haiku-20241022` |

## How to Cite

This repository is part of a doctoral dissertation that has not been published yet. The citation will be added here once the dissertation is available.

**TBD**

## License

This repository is released under the GNU General Public License v3.0. See the [LICENSE](./LICENSE) file for details.
