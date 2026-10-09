# 🐇 RHAR Safe Start — CPU selection of the first 12 questions

[🇨🇿 Česky](../CZ%20docs/SAFE-START-DATA.md) · [Safe Start plan](SAFE-START.en.md) · [DEV-NOTES](DEV-NOTES.en.md)

**Decision (2026-10-10):** I authorized **only** downloading GSM8K `main/train` and selecting 12 questions on CPU. **No GPU generation, inference, LoRA or training has been authorized.**

## Exact source and integrity

- Source: [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k), configuration `main`, split `train`.
- Pinned dataset revision: `740312add88f781978c0658806c59bc2815b9866`.
- Only downloaded object: `main/train-00000-of-00001.parquet` (about 2.31 MB).
- Expected full-file SHA-256: `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`.
- The `diagnostics/safe_start_data.py` script refuses modified or corrupt files and never uses GPU. **It does not download the test split.**
- Reading the cached Parquet **directly requires `pyarrow`**. The first actual Kali download attempt reached Parquet parsing but failed because `pyarrow` was missing from `.venv`. I added `pyarrow==16.1.0` to `requirements.txt`; install only this dependency with `uv pip install --python .venv/bin/python pyarrow` (no need to pull the full CUDA/vLLM requirements). The downloader validates and reuses the existing cached file.

## Selection protocol

1. Read only each original training question and its answer. Extract the numeric gold after `####` and **never include the reference solution reasoning in a model prompt**.
2. Reject invalid, empty or overly short questions, nonnumeric gold values and source questions containing a `Final answer:` leakage.
3. Freeze ranking by SHA-256 of a **constant salt plus normalized question text**. Selection is not based on model outcomes or favoring easy questions.
4. Exclude exact and near-duplicate candidates. When `questions/questions.jsonl` already exists locally, compare candidate questions against its **user prompt text only**. Never read official gold answers, modify evaluation scripts, or download eval datasets.
5. Pass the resulting **12 review candidates** through `safe_start_plan.py`, which builds **36 planned** sampling records but does not generate text.

**Important:** matching text and heuristic similarity cannot prove the absence of paraphrased official SVAMP/MBPP+/BFCL/IFEval questions. Without a local eval file, the audit status is `pending_local_eval_corpus`. With one it is only `local_partial_only`, always `overlap_audit_exhaustive=false`. No candidate is automatically approved for training.

## Run on Kali

First, the CPU tests, which never download anything:

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data -v
python -c "import pyarrow.parquet; print('pyarrow OK')"
```

**Only after green tests**, run the separately approved download:

```bash
python -m diagnostics.safe_start_data --download
python -m diagnostics.safe_start_plan --dry-run --questions data/safe-start/questions.jsonl
```

All output stays in Git-ignored `data/safe-start/`:

| File | Contents |
| --- | --- |
| `raw/gsm8k-train.parquet` | Only train; SHA-256 verified |
| `questions.jsonl` | 12 candidate questions, stable IDs, numeric gold, pinned revision |
| `selection-report.json` | Counts, audit scope and hashes, `review_only`, `training_approved=false`, `gpu_used=false` |

Existing output is **never overwritten**. Avoid publicly committing raw data or answer keys.

## Verification status

- **Completed:** 16/16 new download/selector CPU unit tests plus the existing 15 planner tests: **31/31 passed in an isolated local environment**. Download success and SHA-256 failure cases used mocked network I/O.
- **Combined suite now confirmed on Kali:** **61/61 OK in 0.600 s** (`Ran 61 tests in 0.600s`, `OK`). Previous separate 45/45 and 16/16 runs remain documented historical checkpoints.
- **Newly confirmed on Kali:** 16/16 tests for the new module passed in 0.512 s; GSM8K main/train was loaded from a verified cached file with SHA-256 `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`; **7,473 real train records, 12 actually selected question IDs and 36 validated planned attempts**. IDs are preserved in `selection-report.json` and both DEV-NOTES.
- **Still pending:** `questions/questions.jsonl` does not exist (`Eval otázky chybí`), so evaluation-question overlap screening has **not** run (`pending_local_eval_corpus`, `local_eval_audit_performed=false`). GPU sampling, LoRA and token savings measurements are neither authorized nor completed. Selected data remain `review_only`.

I collaborate on this project with **ChatGPT (OpenAI, GPT-6)** and my local GGUF agent **Máša**; only verified work is credited.
