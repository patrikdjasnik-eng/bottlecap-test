# IDEA.md — RHAR: Rabbit Hollow Adaptive Reasoning

**Status (2026-10-09):** The project owner **approved RHAR as a unified modular research direction**. This authorizes the concept, not specific training methods, architectural code changes, expenditure, or model weight updates.

[🇨🇿 Czech version](CZ%20docs/IDEA.md) · [Development diary](docs/DEV-NOTES.en.md)

## Motivation

The original Qwen3-0.6B can produce unnecessary reasoning tokens. We want to reduce **total generated tokens (reasoning + final answer)** without meaningfully compromising accuracy across different tasks. Prompt-only shortening and turning off thinking are explicitly not acceptable methods.

## Hypothesis

**RHAR** investigates whether a model can learn more efficient reasoning when training considers **information progress (RPS)**, **recoverability of essential information (RPD)**, and **protection of general capabilities (TPC)** together.

This is an *unproven research hypothesis*. Related methods already exist; we do not claim world-first novelty or demonstrated improvement.

## The three modules

| Module | Hypothesized function | Research question | Status |
| --- | --- | --- | --- |
| **RPS — Reasoning Progress Signature** | Measure informative progress versus redundancy in reasoning steps, potentially including hidden-state signals | Can the model learn to avoid unproductive reasoning? | Concept approved, implementation unspecified |
| **RPD — Reversible Proof Distillation** | Assess whether shortened reasoning preserves sufficient information for independent reconstruction or verification | Does concision preserve crucial proof content? | Concept approved, implementation unspecified |
| **TPC — Transfer-Protected Compression** | Monitor and constrain capability regressions across math, coding, function calling and instruction following | Will compression generalize rather than overfit one domain? | Concept approved, implementation unspecified |

These mechanisms should ideally affect **what the model learns**, not require costly extra verification agents on every inference. Feasibility and overhead remain open questions.

## Modular research plan (proposed experiments, not yet authorized)

1. Measure the unchanged base model: exact answers, reasoning/final/total token counts, time, variance and failures.
2. Investigate **RPS separately** and determine whether progress/redundancy signals are reliable beyond one problem.
3. Investigate **RPD separately** on permitted training or research data; measure reconstruction reliability and its computational cost.
4. Investigate **TPC separately** using separate allowed training/validation tasks across several domains, without fitting to official held-out evaluation data.
5. Perform **ablation comparisons** of base, individually testable modules, RPS+RPD and RPS+RPD+TPC; preserve matched experimental settings.
6. **After further owner approval**, select training objectives and data, choose LoRA or another model modification, define the compute budget, and run training.
7. Evaluate trained candidates with unchanged official `evaluate.py`; compare paired base/candidate outputs using `compare.py`.

The previous correctness-filtered short-reasoning distillation idea remains a **possible training baseline**, not an approved or implemented RHAR algorithm.

## Metrics and evaluation

- **Primary:** correctness and total generated tokens including thinking and final answer.
- **Diagnostic:** reasoning/final split, repetition indicators, truncation, time, variability, GPU use, per-domain regressions and reconstruction outcomes.
- **Controls:** matched sampling/seeds and prompts for comparisons; clear training/validation split; ablations; failure logs.
- **Official held-out evaluation:** SVAMP, MBPP+, BFCL and IFEval, using the supplied recipe and paired uncertainty intervals. **Never train on these benchmarks.**
- **Novelty:** compare an implemented mechanism with the closest literature before claiming novelty; unseen private work cannot be ruled out.

## Constraints

- Base model: `Qwen/Qwen3-0.6B`. Final model remains approximately 0.6B and **continues to reason**.
- **Never use prompt engineering alone to shorten thinking; never switch thinking off.**
- Do not change the official benchmark prompts, generation settings, token cap or scoring.
- Keep standard Hugging Face Transformers/vLLM compatibility for final submission.
- Never invent benchmark scores, improvements, originality, or tests that did not happen.
- **Major choices require explicit project-owner approval**; documentation of this approved concept does not authorize new experiments.

## Current status and observations

- **User-verified exploratory inference:** correct `Final answer: 43`, 371 generated tokens, 61.45 seconds, 6.04 tokens/s and 1.12 GiB allocated PyTorch memory on GTX 1070 Ti. **One unofficial question, not a measured improvement.**
- **Read-only diagnostic:** `diagnostics/reasoning_probe.py` exists with independent tests; its first owner-run GPU diagnostic output is still pending.
- **RHAR:** direction approved, mechanisms and training unimplemented, **no RHAR results yet**.

## Hardware

See [docs/HARDWARE.en.md](docs/HARDWARE.en.md). Local machine: GTX 1070 Ti 8 GB (compute capability 6.1), i5-3450, ASUS P8B75-M, 16 GB RAM. Local PyTorch CUDA inference works; official vLLM evaluation needs a supported GPU. Hidden-state diagnostics and training feasibility have not been established.

## What worked / failed

Record actual runs, negative findings, hardware and decisions in [docs/DEV-NOTES.en.md](docs/DEV-NOTES.en.md). No RPS/RPD/TPC training experiment has been performed.
