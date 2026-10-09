# 🧪 RHAR v0.1 — Offline correctness gate and candidate selector

[🇨🇿 Čeština](../CZ%20docs/OFFLINE-SELECTOR.md) · [🇬🇧 English](OFFLINE-SELECTOR.en.md) · [RHAR v0.1 plan](RHAR-V01-PLAN.en.md)

**Status:** I implemented an **offline review of pre-existing JSONL generations**. The script has no PyTorch or GPU dependency. **It does not launch Qwen, download datasets, edit weights or train.** Selection is for human review, not automatic training.

## What it does

`diagnostics/offline_selector.py` reads `records.jsonl`, independently grades the final answer against the gold answer (it does not trust the recorded `correct` flag), and returns a reason for every accepted or rejected record. Checks include:

1. Valid task and gold answer: **numbers** (including decimals) and **single-letter choices** only. It does not execute code or validate function calls or general factual claims.
2. Exactly one parseable last line `Final answer: ...`; reject invalid or duplicated outputs.
3. No truncation, consistent `<think>…</think>` markers (or a recorded prefilled opening) and `reasoning_tokens + final_tokens == total_tokens`. Token counts are **taken from the record**, not independently retokenized.
4. Reported correctness mismatches, duplicate seeds and same-question consistency of prompts, models and answer keys.
5. Explicit training provenance: `source`, `source_revision`, `split=train`, `model_revision`, `prompt_hash`, `thinking_enabled=true`, `seed`. **Without it, a record is analysis-only.** Source names resembling SVAMP/MBPP/BFCL/IFEval are rejected for training selection. This simple name check **cannot prove an arbitrary dataset does not contain official benchmark questions**; independently verify provenance and cross-split duplicates before training.
6. At most **one shortest correct candidate per question**, and only when at least two correct samples with distinct seeds and comparable metadata exist. A single correct sample is not evidence of compression.

**Important:** a correct final answer does not guarantee every reasoning step is valid. **RPD and RPS are not yet implemented**; all selections are `review_only` and require further examination.

## Running on Kali / WSL2

First run the CPU-only test suite; it loads no LLM:

~~~bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe -v
~~~

Once green, inspect historical Experiment 002 **without any new inference**:

~~~bash
python -m diagnostics.offline_selector runs/diagnostics/20261009T210123Z/records.jsonl
~~~

Optional: `--out runs/offline/my-review` (a new, non-existing output folder) and `--min-correct 2` (minimum 2).

## Output: new `runs/offline/<UTC>/` folder

| File | Contents |
| --- | --- |
| `review_records.jsonl` | Per-answer `correct`, `training_eligible`, `selected`, `reason`, length and seed |
| `selected_for_review.jsonl` | At most one shortest correct candidate per comparable question; **review_only**, never automatically approved training data |
| `summary.json` | Counts, regraded correctness, rejection reasons, input SHA-256, `no_training_performed=true` and `official_benchmark=false` |

Output stays under Git-ignored `runs/`. **Generated text may contain sensitive content — do not publish raw traces without inspection.** Existing output directories are not overwritten. Invalid JSONL lines fail with their line number before results are written.

The historical Experiment 002 contains just one incorrect answer (`42` rather than `43`). **The expected selection count is zero.** This is expected program behavior, **not** a newly measured result from my Kali.

## Tests, limitations and approvals

- **Implemented and locally tested:** 16 new selector unit tests; together with a locally reconstructed current diagnostic suite, **26/26 passed in an isolated test environment**. A fresh run on my Kali after `git pull` is still **pending**, as is any GPU pilot.
- Unit tests cover wrong answer `42`, mismatched stored correctness, broken thinking markers, truncation, accounting, blocked sources, provenance, duplicate seeds, mismatched prompts and refusal to overwrite output.
- This does **not verify each reasoning step**, prepare a trusted ML training dataset or guarantee freedom from official benchmark contamination. JSONL metadata can be false; independently confirm provenance before any actual model training.
- **Awaiting a separate decision:** datasets, sampling pipeline, GPU budget, RPD reconstruction checks, LoRA, weight updates and official evaluation.

I collaborate transparently with **ChatGPT (OpenAI, GPT-6)** and my own local GGUF agent **Máša**. I write this record in my own developer voice and do not attribute any unverified runs to Máša.
