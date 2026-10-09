# 🐇 RHAR Safe Start — implementation plan and CPU tests

**Status, 2026-10-10:** first preparation phase approved and the CPU-only planner implemented. **No model inference, training-data downloads or training occurred.** No token savings are claimed.

[🇨🇿 Čeština](../CZ%20docs/SAFE-START.md) · [RHAR v0.1](RHAR-V01-PLAN.en.md) · [Development diary](DEV-NOTES.en.md)

## 🎯 Scope I approved

I will start with a small mathematics pilot: **12 distinct questions × 3 generations = 36 model responses**, with thinking enabled. The goal is to learn whether the original Qwen produces variable-length **correct** reasoning traces for the same problems. **36 is a planned number, not a completed benchmark.** I am not promising 12 usable SFT examples.

## 🧩 Proposed frozen configuration

| Setting | Planned value |
| --- | --- |
| Model | `Qwen/Qwen3-0.6B` |
| Model revision | `c1899de289a04d12100db370d81485cdf75e47ca` |
| Questions | 12 distinct arithmetic problems |
| Samples per question | 3 with seeds `9001`, `9002`, `9003` |
| Thinking | `True` |
| Sampling | temperature `0.6`, top_p `0.95`, top_k `20` |
| Token cap | `max_new_tokens=512`; reject truncated outputs |
| Possible future source | **GSM8K / train**; an exact dataset revision must be approved and pinned |
| Final answer format | neutral `Final answer:` instruction; no sample answer `42` |
| Official evaluation | SVAMP, MBPP+, BFCL, IFEval remain untouched |

The three seeds designate **planned independent samples**, not evidence they have been generated or a guarantee of statistical independence. GPU generation remains subject to separate approval.

## 🧱 Implementation stages and gates

**A — Completed: offline planner.** I added `diagnostics/safe_start_plan.py` and `tests/test_safe_start_plan.py`. The planner uses the standard library and settings from the existing `reasoning_probe.py`. Its only permitted CLI operation is `--dry-run`. It never loads GPU, Transformers or a dataset client, and it does not write any files.

**B — Not yet approved: select 12 real questions.** I provisionally restricted the validator to **GSM8K train / math**, but no real questions have been selected or downloaded. Before use, I must approve the exact dataset revision, licensing, the selected questions, duplicate checking against other sources and official evaluation benchmarks, and train/validation boundaries. A literal `source=gsm8k` field **cannot independently establish provenance or prove that no evaluation questions overlap**.

**C — Not yet approved: 36 GPU generations.** On separate approval, I would build a resumable generator with pinned settings and complete per-response records, including reasoning/final/total token counts, seeds, format status, elapsed time and failures. A rough **30–60 minutes of inference** extrapolated from previous single generations is uncertain and **not an approved GPU budget**.

**D — Not yet approved: correctness-gated filtering.** I would feed generation records into the existing `offline_selector.py`, but only after ensuring authentic provenance and matching data schemas. A correct final number **does not validate intermediate mathematical reasoning steps**. All selected traces would remain `review_only`.

**E — Separate future decision: LoRA and evaluation.** Preparing training data is not training. Weight modifications, held-out validation and official benchmarks need separate approval and appropriate hardware.

## 🛡️ Local input contract

Once the data choice is approved, a local JSONL file must contain **exactly 12 records**. Each record must contain *exactly*:

| Field | Meaning |
| --- | --- |
| `question_id` | Unique question ID |
| `question` | Non-empty text of a math problem |
| `gold_answer` | Numeric gold answer encoded as a string |
| `source` | `gsm8k` only in this proposed schema |
| `source_revision` | Exact 40-character lowercase hex dataset commit |
| `split` | `train` only |
| `task` | `math` only |

No actual questions or gold answers have been committed. The validator rejects unexpected sources and fields, mixed revisions, wrong splits, nonnumeric answers, missing questions and exact duplicates. **Near-duplicates and evaluation contamination require a separate external audit.**

## 🐇 Approved GSM8K CPU-only data preparation (2026-10-10)

After 45/45 tests passed on Kali, I approved **only downloading GSM8K main/train and selecting 12 questions on CPU**. A pinned downloader and 16 additional CPU tests are in the repository. **See [SAFE-START-DATA.en.md](SAFE-START-DATA.en.md) for the exact commands.** All selected examples remain review-only and not automatically suitable for training. The combined current suite defines 61 tests; 61/61 on Kali is still pending.

## 🧪 Verifying the CPU preparation

After `git pull` on Kali:

```bash
cd ~/bottlecap-test
source .venv/bin/activate
python -m unittest tests.test_safe_start_plan -v
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan -v
python -m diagnostics.safe_start_plan --dry-run
```

Optionally **only after a later approved, manually prepared local dataset**:

```bash
python -m diagnostics.safe_start_plan --dry-run --questions data/safe-start/questions.jsonl
```

The planner **does not perform inference**. It validates local JSONL in memory, computes a plan of **36 proposed attempts**, and only prints a summary. It omits raw questions and gold answers from the plan, but **does not independently verify input metadata against an authoritative dataset host**.

## ✅ Actual verification and limits

- **15/15 new CPU tests passed** in an isolated local Python environment; `python -m diagnostics.safe_start_plan --dry-run` also succeeded. That test environment used a minimal local copy of the original `reasoning_probe.py` constants, **not a full checkout of the GitHub branch**.
- The previous **30/30** offline-selector and diagnostic tests were independently confirmed on my Kali in the prior step. **The new combined 45-test suite still needs a Kali run after `git pull`.**
- No 36 responses were generated, no approved 12-question dataset was assembled, no LoRA training was run, and no token savings were measured. **Planning alone is not the finished RHAR algorithm.**

I collaborate with **ChatGPT (OpenAI, GPT-6)** and my own local GGUF AI agent **Máša**. I keep research decisions in my developer voice and do not attribute unverified actions or runs to Máša.

**Next approval boundary:** once all 45 tests are green, decide on exact dataset examples, revision and de-duplication. **GPU remains unused until a future experiment is explicitly authorized.**
