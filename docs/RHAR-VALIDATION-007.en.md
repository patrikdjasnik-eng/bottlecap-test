# 🧪 RHAR Validation 007 — BASE vs SFT003 vs SFT004

**End-of-day record: 2026-10-12.** **Status: completed exploratory local GPU comparison as evidenced by the user's terminal output; NOT an official BottleCapAI benchmark.**  
[🇨🇿 Česky](../CZ%20docs/RHAR-VALIDATION-007.md) · [DEV-NOTES](DEV-NOTES.en.md) · [CEP 002](CEP-002.en.md)

## Actual evidence and limits

The user reported a successful local Kali/WSL2 CPU test run: `Ran 10 tests in 0.057s`, `OK`. Then `python -m diagnostics.rhar_validation_007 --dry-run --out runs/rhar-validation-007` returned `status=plan_only`, **40 questions × 3 variants = 120 planned generations**, `gpu_used=false`, `training_performed=false`. The user explicitly ran `--execute --approve-gpu` in offline Hugging Face / Transformers mode. The terminal printed **120 per-example lines** and a final `status=completed_exploratory` summary.

**Independent verification limitation:** the user's local `runs/rhar-validation-007/records.jsonl`, `summary.json`, SFT004 training logs and raw traces were not provided. The inspected remote `feat/reasoning-compression` branch did not contain `diagnostics/rhar_validation_007.py`, its tests or the SFT004 training script at documentation time. Do not claim to have audited or rerun those local files.

## Protocol reported by dry-run

- **Qwen/Qwen3-0.6B**, pinned model revision `c1899de289a04d12100db370d81485cdf75e47ca`; source **GSM8K/main/train**, **40** questions, **one seed 9001** and cap **512** with temperature 0.6 / top-p 0.95 / top-k 20.
- Variants: **base**, **SFT003** (`runs/rhar-training-003`), **SFT004 / long-SFT** (`runs/rhar-training-004-long-sft`).
- Validation fingerprint `256adfdeddf9c73371893573c71af9698d11116c525b884cd5f79e276f3bf175`, selection seed **7007**.
- The script reported exclusion of **2,500** SFT004 training IDs plus **100** loss-validation IDs, `training004_train_and_loss_validation_excluded=true`, `validation_used_for_loss_in_training004=false`; **1,262** protected unique IDs including historical partitions, previous runs and **60** CEP002 reserved holdout IDs, with **3,611** remaining fresh candidates. These are script-reported controls, not independently verified here.
- **2,759** official evaluation prompts were screened using a **heuristic text overlap check only**. This does not rule out semantic paraphrases or fully certify decontamination.

## Reported results

| Metric | Original base | SFT003 | SFT004 |
| --- | ---: | ---: | ---: |
| Strict correct | **6/40 (15%)** | **14/40 (35%)** | **17/40 (42.5%)** |
| Completed | 8/40 | 38/40 | 39/40 |
| Truncated | **32/40** | 2/40 | 1/40 |
| Mean emitted tokens | 496.50 | 122.12 | **115.28** |
| Total emitted tokens | 19,860 | 4,885 | **4,611** |

**SFT004 vs base:** +11 correct (+27.5 percentage points), -15,249 generated tokens (~76.8% fewer), with **12 paired fixes and 1 regression**. Critically, the base hit its **512-token cap on 32/40 questions**: this is a comparison against a **heavily censored** baseline, not a general proof of equivalent performance.

**SFT004 vs SFT003:** +3 correct (+7.5 percentage points), -274 tokens (~5.6%), with **6 paired fixes and 3 regressions**. Forty questions at a single seed and potentially different SFT training data/compute budgets do **not** establish a stable causal benefit. Invalid and truncated responses remain in the token total.

The program explicitly reported `quality_preservation_demonstrated=false`, `generalization_demonstrated=false` and `official_benchmark=false`. No official SVAMP/MBPP+/BFCL/IFEval score follows from this run. These are **standard SFT adapter results, NOT a validation of the still-proposed CEP 002 algorithm**.

## End-of-day lessons and next gates

1. Preserve original local `plan.json`, `records.jsonl`, `summary.json`, the validation fingerprint, adapter metadata and local training code. At the next session, inspect local Git status and whether Validation 007 / SFT004 sources have been committed and pushed before claiming the remote branch is reproducible.
2. Review the **six paired SFT004 wins and three losses** against SFT003 from immutable raw traces; do not train on these already-scored questions if they must remain held out.
3. Keep CEP 002 **VPS + XP + REC + Verified Lock** a separate, unimplemented hypothesis. A matched SFT control, fresh unseen holdout, more seeds and independent validation are required before attributing improvements to the new mechanism.
4. The official `evaluate.py` / `compare.py` protocol remains unchanged, with GPU or new training permitted only by separate explicit user approval.

**Today's session ends here.** Documentation only; no new GPU work, inference or model training was triggered by this entry. 🐇🛡️
