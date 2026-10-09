# 🐇 RHAR Safe Start — preparing 36 Qwen3-0.6B generations

[🇨🇿 Čeština](../CZ%20docs/SAFE-START-GENERATION.md) · [Safe Start](SAFE-START.en.md) · [Overlap screen](SAFE-START-OVERLAP.en.md) · [DEV-NOTES](DEV-NOTES.en.md)

**Decision (2026-10-10):** I approved **preparing the generator and CPU tests only — not GPU execution, model inference/downloads, or training**.

## 🔬 Scope and frozen configuration

Twelve previously selected GSM8K train questions × three generations each = **36 planned responses**. The research compares **correctness and actual generated-token counts**; this is not evidence of token savings or model-weight improvements.

| Setting | Pinned value |
| --- | --- |
| Model | `Qwen/Qwen3-0.6B` at `c1899de289a04d12100db370d81485cdf75e47ca` |
| Seeds | `9001`, `9002`, `9003` per question |
| Thinking | `enable_thinking=True` |
| Sampling | temperature `0.6`, top_p `0.95`, top_k `20` |
| Cap | `max_new_tokens=512` |
| Potential GPU | CUDA + float16; model must already be in local cache |
| Training / official benchmark | **Never run by this script** |

The `diagnostics/safe_start_generate.py` module checks the exact twelve question IDs and hashes against `selection-report.json`, and validates the completed `overlap-audit.json` for six pinned official evaluation source objects and no heuristic text matches. **This is not exhaustive semantic contamination detection and does not authorize model training.**

The prompt uses the unchanged `build_prompt`, with **no gold answer or shortened-reasoning instruction**. Output records include seeds, all generated tokens, correct reasoning/final boundaries, independently graded answer, prompt hash, and inference latency. Prefilled `<think>` tokens are not mistakenly counted as model output; missing thinking markers remain unknown instead of zero. Incomplete responses lacking EOS are `truncated` and excluded from correct candidate selection. Records fit the existing `diagnostics/offline_selector.py`.

## 🧪 CPU-only verification

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate

python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data tests.test_safe_start_overlap tests.test_safe_start_generate -v

python -m diagnostics.safe_start_generate --dry-run
```

Expect **103 tests** (79 existing + 24 new) and dry-run `status=plan_only`, `planned_generations=36`, `gpu_used=false`, `model_loaded=false`, `training_performed=false`. Dry run does **not** import torch/Transformers, access GPU, download any data, or write results.

## 🚫 GPU execution is NOT approved

The future runner has **two required explicit flags**, `--execute` and `--confirm-gpu-36`, but those switches are **not authorized for use yet**. A separate user approval is required. Actual future execution would use only an existing local model cache (`local_files_only=True`) and create fresh Git-ignored files in `runs/safe-start/<UTC>/`: config, incremental JSONL records, and summary only after all 36 attempts. Existing results are never overwritten; no automatic resume. All outputs remain `review_only`, not approved training examples.

**Newly verified on Kali (2026-10-10):** the complete **103/103 test suite in 0.917 s** (`Ran 103 tests in 0.917s`, `OK`). Running `python -m diagnostics.safe_start_generate --dry-run` confirmed **12 questions, 36 planned attempts and three seeds**, all three input SHA-256 values, and `gpu_used=false`, `model_loaded=false`, `model_downloaded=false`, `training_performed=false`, `model_generations_performed=0`. Input hashes: questions `ebb3595c677ec6a660da3ff8731448182674967beab4d5e7f5256347541d32bc`, selection report `0760c4825de4e18bbbfcb6429dd543dcfa7fcc9e18dae83a118bccdf2b3cb89a`, overlap audit `7b9443abf9e2960084bfaf6472ddf049ff057d4f4e1c889a4c01902a2ccc7ca4`. **This is not a GPU run or measured token savings.**

I collaborate with **ChatGPT (OpenAI, GPT-6)** and my local assistant **Máša**; no unverified model runs are attributed to either.
