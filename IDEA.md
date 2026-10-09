# IDEA.md — Adaptive Reasoning Compression

## Motivation

Qwen3-0.6B can generate long reasoning traces even for simple tasks. Objective: reduce *total generated tokens* without significant loss of accuracy, including across unseen benchmarks.

## Hypothesis

**Correctness-filtered concise reasoning distillation.** Distill a small number of short *and correct* reasoning traces from the original model, using only permitted training data. Fine-tune with a small LoRA adapter, retaining explicit thinking and final-answer format. The goal is fewer redundant steps, not prompt-only shortening.

## Method (proposed)

1. Prepare training/validation sets using `utils/train/prepare_data.py`. Never use the four evaluation benchmarks for training.
2. Sample multiple teacher completions from the base Qwen3-0.6B with its thinking enabled; record number of generated tokens.
3. Use the training answer key and `utils/train/rewards.py` to filter incorrect completions. Favor the shortest *correct* non-empty reasoning chain for each question.
4. Use supervised fine-tuning with LoRA. Mask prompt tokens in the loss. Start with a small training set and watch for over-compression, truncation and format regressions.
5. Validate on a held-out portion of training datasets; then evaluate with the official unchanged `evaluate.py`.
6. Compare `runs/base` and `runs/mine` via `compare.py`. Record token reduction, accuracy delta, 95% CIs and run configuration.

## Constraints

- Source model: `Qwen/Qwen3-0.6B`.
- Final model should remain approximately 0.6B and produce actual reasoning.
- No training on SVAMP, MBPP+, BFCL, or IFEval.
- Do not change the benchmark prompts, generation recipe, or token cap.
- Prefer the standard Hugging Face + vLLM load path.
- All results must be backed by actual runs, not estimates.

## Results

Not measured yet.

## Hardware

See [docs/HARDWARE.md](docs/HARDWARE.md). Local setup: GTX 1070 Ti (8 GB), Intel i5-3450, ASUS P8B75-M, 16 GB RAM.

## What worked / failed

Pending experiments.
