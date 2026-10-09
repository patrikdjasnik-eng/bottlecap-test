# 🧬 RHAR v0.1 — Correctness-Gated Reasoning Compression

**Status: research direction approved, detailed implementation proposal; no pilot or training has run yet.**  
**Date:** 2026-10-09 · **Branch:** `feat/reasoning-compression`

[🇨🇿 Čeština](../CZ%20docs/RHAR-V01-PLAN.md) · [My development diary](DEV-NOTES.en.md) · [IDEA.md](../IDEA.md)

## 🎯 Objective and motivation

I want to change **Qwen3-0.6B itself** so it generates **fewer total tokens (thinking and final answer)** without significant accuracy or generalization regressions. **I will not turn off thinking, use prompt-only shortening, or train on held-out evaluation benchmarks.**

I approved **Correctness-Gated Reasoning Compression as RHAR's first training research direction**, not a finalized algorithm, dataset, sample count, GPU budget or immediate weight modification. This is an **implementation proposal requiring further approval**. The first question is whether the unchanged model already generates useful, shorter, correct reasoning examples.

## 🧩 Proposed v0.1 pipeline

1. **Baseline and green tests.** Run the current **10 defined diagnostic tests** on Kali, then repeat one fixed-prompt baseline probe after the neutral-format correction. Preserve historical Experiment 002 (325 tokens, incorrect 42 vs 43).
2. **Separate permitted datasets.** Propose **20–30 distinct questions** across arithmetic and multiple-choice QA, potentially sampled from upstream's suggested **GSM8K, CommonsenseQA, ARC Easy and Skywork-OR1**. Freeze source revisions, licenses and exact choice **before execution**. **SVAMP, MBPP+, BFCL and IFEval are strictly held out.**
3. **Multiple samples per question.** Propose **2–3 independent generations**, thinking on, with recorded model revision, seeds, sampler, prompt and token cap. Preserve every real generation under a fresh local `runs/` directory.
4. **Correctness gate.** Check gold-answer correctness, properly closed generated text, actual thinking markers, parseable final answer and non-truncation. Reject incorrect, truncated, empty and ungradeable responses **with explicit reasons**.
5. **Candidate selection.** Compare total generated token lengths **only between correct candidates for the same prompt**. Shorter does **not** automatically mean better: independent reconstruction checks (RPD) are not yet implemented. If too few usable correct samples exist, stop and investigate.
6. **Training artifacts, then potentially LoRA.** Upon separate implementation approval, prepare JSONL SFT examples retaining actual thinking boundaries. Consider standard **LoRA supervised fine-tuning**, with loss **only on completion tokens, never the prompt**. **No model weights are being trained now.**
7. **Generalization checks.** Evaluate the original base and the modified checkpoint on **new, independent validation questions** using identical prompts and sampling, counting all generated tokens, including wrong answers. Only later use unchanged official `evaluate.py` and `compare.py` on compatible GPU hardware.

## 📦 Proposed data records

This is a **schema proposal**, not a claim that any dataset artifact exists.

| Category | Candidate fields |
| --- | --- |
| Question identity | `question_id`, `source`, `source_revision`, `task`, `split`, `gold_answer` |
| Inference settings | `model`, `model_revision`, `seed`, `sampling`, `max_new_tokens`, `thinking_enabled`, `prompt_hash` |
| Generated output | `generated_text`, `final_text`, `reasoning_split_status`, `terminated`, `truncated` |
| Measurements | `total_generated_tokens`, `reasoning_tokens`, `final_tokens`, `generation_seconds`, `peak_vram_gib` |
| Selection | `correct`, `accepted`, `rejection_reason`, `candidate_rank`, `verifier_version` |

Separate training and validation **by question identity before generation**, not by splitting multiple replies to the same question. Detect duplicates and near-duplicates crossing the split.

Upstream `utils/train/rewards.py` provides scoring for its suggested datasets, but can be **more permissive than the official evaluation grader**, so check response format independently. Upstream `utils/train/prepare_data.py` also contains literal formatting examples `Final answer: 42` and `Final answer: B` in training instructions. Their **potential answer-bias effect** warrants a separate decision and test. Training-prompt changes never authorize modifying **official** evaluation prompts.

## 🖥️ Hardware cost and constraints

An earlier GTX 1070 Ti inference took around **51–61 seconds**. **40–90 generations** might therefore consume roughly **35–90 minutes of generation**, before model loading, output-length variability and other overhead. **This is an uncertain estimate, not approved compute time or a completed run.** I must decide the final budget before running it.

The provided `train.py` is only a rollout demonstration, **not a working RHAR trainer**. It defaults to `bfloat16` on CUDA, whereas Pascal GTX 1070 Ti does not natively support bf16. If a LoRA pilot is approved, first test a memory-constrained `float16` configuration with micro-batch 1, gradient checkpointing and numerical/VRAM checks. Do not promise training will fit into 8 GB without testing.

## 🧪 Proposed verification and gates

| Check | Intended evidence |
| --- | --- |
| Unit tests | Reject missing/malformed thinking, wrong answer, truncation, duplicates, data leakage and invalid split |
| Dry run | Check data records and selection without GPU or model downloads |
| Sampling pilot | Record correctness fraction, number of shorter correct alternatives, thinking/final split |
| Simple baseline | Shortest-correct selection as a non-novel reference method |
| Training | LoRA runs without OOM/NaN and produces a standard `.safetensors` adapter |
| Held-out validation | Track **accuracy and total tokens jointly**, not brevity alone |
| Future RHAR ablations | Individually assess RPS, RPD, TPC and optionally HRM |
| Official final evaluation | Unmodified SVAMP / MBPP+ / BFCL / IFEval and paired CI via `compare.py` |

**Stop conditions:** failing unit test; leaked gold answer; invalid/truncated generations; too few correct candidates; OOM/NaN; accuracy regression; unmatched prompts or sampling. **One promising response is not evidence of success.**

## 🤝 Transparent AI collaboration

I collaborate on RHAR with **ChatGPT (OpenAI, GPT-6)** and **my own GGUF AI agent, Máša**. ChatGPT helps with design discussions, analysis, code and documentation. Máša is part of my development environment; **I do not attribute specific experiment results to her without documented evidence**. I retain final authority for research and implementation decisions.

## 🧪 Implemented offline phase

The first approved implementation step **is now in the repository**: `diagnostics/offline_selector.py` and **16 new CPU tests**. It processes only existing JSONL generations, with no model inference or training. See [OFFLINE-SELECTOR.en.md](OFFLINE-SELECTOR.en.md). **`selected_for_review.jsonl` is not approved training data.** A fresh Kali test run and offline analysis of historical Experiment 002 remain pending.

## ✅ Approval boundary

**Approved:** RHAR v0.1 research direction and documenting this implementation proposal.  
**Not yet authorized as concrete actions:** final data choice/download, a new GPU sampling pipeline, number of GPU generations, LoRA training, weight edits and official evaluation. **The offline selector and CPU tests are already implemented.**  
**Not performed:** pilot, training, checkpoint comparison, demonstrated savings, complete green suite since the last diagnostic fix.

**Next decision:** whether to **implement only a safe offline candidate-selection pipeline and CPU unit tests first**, with no sampling, training or GPU cost. This is a limited, independently testable first implementation step.
