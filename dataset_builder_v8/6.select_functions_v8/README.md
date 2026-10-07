# Function Selection and Metrics

This final module performs the selection of the dataset that will be used for training/evaluation.

## Purpose

To ensure a balanced and diverse dataset, we calculate code complexity metrics (Halstead) for all "Covered" functions and then perform stratified sampling. This prevents over-representation of trivial functions and ensures we have a good distribution of complexity.

## Workflow

### 1. Metric Calculation (`measure.py`)

Calculate Halstead metrics (Difficulty, Volume, Effort) for each function.

```bash
python measure.py
```

*   **Input**: `../5.obtain_functions_v8/output` (Pseudo-C files).
*   **Output**: `output/metrics.json`.

### 2. Stratified Selection (`select.py`)

Perform stratified sampling based on difficulty buckets.

```bash
python select.py
```

*   **Input**: `output/metrics.json`.
*   **Action**: Groups functions into buckets (e.g., Difficulty 1.0-2.0) and samples evenly.
*   **Output**: `output/selected.json`.

## Generated Artifacts

*   `output/metrics.json`: All covered functions with their complexity metrics.
*   `output/selected.json`: The final dataset selection.
