# LLM Query Pipeline

This directory contains the third stage of the pipeline, which orchestrates the batch querying of Large Language Models (LLMs) to decompile the extracted Intermediate Representation (IR) files into C code.

## Purpose

To evaluate the capabilities of current LLMs in decompilation tasks, we query different models (e.g., GPT-4.1, Claude Sonnet 4) with the extracted artifacts (ASM, LLIL, MLIL, HLIL). This stage manages the communication with the APIs, handles batch processing for efficiency, and saves the generated C code.

## Workflow

### 1. Batch Processing (`main.py`)

Execute the main script to start or resume the batch processing of files.

```bash
python3 main.py
```

*   **Configuration**: Requires a `.secret` file in this directory with valid API keys:
    ```
    API_KEY_OPENAI="..."
    API_KEY_ANTHROPIC="..."
    ```
*   **Input**: `input/` directory containing the extracted IR files (usually symlinked or copied from `../2.get_IRs/output/`).
*   **Action**: 
    1.  Scans `input/` for supported files (.asm, .llil, .mlil, .hlil).
    2.  Constructs prompts using defined templates for each file type.
    3.  Submits batch requests to configured LLM providers (OpenAI, Anthropic).
    4.  Polls for completion and downloads results.
*   **Output**: 
    *   `output/<model_name>/<ir_type>/<original_path>/<filename>.c`: Decompiled C files.
    *   `batch_state.json`: Tracks processing progress.
    *   `batch_info.json`: Detailed batch job metadata.
    *   `error.txt`: Error log.

## Generated Artifacts

For each input file (e.g., `func.asm`), the pipeline generates a decompiled C source file in the corresponding output structure.
