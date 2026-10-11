# 🐰 RHAR CEP-002 — CPU MVP

**Status (11 Oct 2026):** first isolated implementation with 22 new CPU unit tests. No new GPU run, LoRA training, or measured CEP-002 performance improvement on Qwen.

Files: `diagnostics/cep002_cpu.py` and `tests/test_cep002_cpu.py`.

## What it tests

- **VPS:** a previously manually reviewed task contract, input facts, mathematical intermediate steps, and final answer. A safe arithmetic AST evaluator checks simple expressions without `eval`. Results: VERIFIED / INVALID / UNVERIFIED / TRUNCATED.
- **XP:** logs original traces and outcomes to JSONL, locks only VERIFIED entries, selects at most three distinct existing traces. Token counts come from external measurements only.
- **REC + Verified Lock:** a verified trigger can only request a recheck; it cannot declare an earlier locked trace wrong. Proven repairs are appended as new records. Changed contracts or verifiers suspend XP export pending manual review.

## Explicit limitations

The verifier accepts **only a narrow machine-readable arithmetic format**, not arbitrary natural-language reasoning. It does not independently prove that the source problem was translated into a correct task contract. `reviewed_by` and `overlap_screen_passed` are attestations, not an automatically performed audit. It does not create alternative mathematical strategies or model generations. JSONL is not a physically immutable archive.

SVAMP, MBPP+, BFCL, and IFEval must never be training sources. No new data preparation, training, or official benchmark has been run. The old CEP 001 is a separate experimental approach.

## Running CPU tests

From the repository root:

`python -m unittest tests.test_cep002_cpu -v`

Full suite (may need additional dependencies):

`python -m unittest discover -s tests -p 'test_*.py'`

**No progress without green tests.** Next steps are manual contract review and separate data auditing, followed by A/B/C training and paired evaluation only with explicit approval.

## Synthetic batch 001 (11 Oct 2026)

Added 12 *hand-authored synthetic* arithmetic examples in `diagnostics/cep002_fixture_batch.py`. The cases exercise percentages, successive discounts, fractions, warehouse inventory, wages, averages, and other simple relations. **These are not GSM8K, new training data, or real Qwen generations.** The fixture author is not an independent external auditor.

Commands:
- `python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch -v`
- `python -m diagnostics.cep002_fixture_batch --dry-run`
- `python -m diagnostics.cep002_fixture_batch --execute --out runs/cep002-fixture-001`

The last command writes a JSONL history and report without overwriting existing runs. All 12 correct example traces are **expected** to be VERIFIED, but the new tests and batch still need execution on the user's computer. This validates a narrow set of task contracts, not model improvement. Do not describe the synthetic fixture's `overlap_screen_passed` flag as an independent audit of real data.


## GSM8K Data Intake 001 (11 Oct 2026)

Added `diagnostics/cep002_data_intake.py` and ten CPU unit tests in `tests/test_cep002_data_intake.py`. Reads only locally cached, SHA-256 pinned GSM8K `main/train` data and local official evaluation prompts for overlap screening (never training targets).

The deterministic partition (`seed=42`) excludes historic positions: **1,000 prior train + 100 loss validation + 20 Evaluation 005 + 60 Evaluation 006 = 1,180**. It selects **12 subsequent questions** for manual review only and reserves the **following 60** as future holdout, whose question texts and answers are not included in the output manifest. Every review example is marked `contract: null` and `approved_for_training: false`.

Important: earlier independent pilot/review records have not yet been exhaustively screened, and semantic/near-duplicate overlaps can be missed. **None of the new examples is automatically approved for CEP training.** Viewing reserved holdout questions or answers can invalidate their unseen status.

Local usage (from worktree, Python environment with `pyarrow`; point to original repository files explicitly):

`python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake -v`

`python -m diagnostics.cep002_data_intake --dry-run --raw-parquet /home/rabbithollow/bottlecap-test/data/safe-start/raw/gsm8k-train.parquet --eval-questions /home/rabbithollow/bottlecap-test/questions/questions.jsonl --out runs/cep002-data-intake-001`

After green dry-run, `--execute` may be run explicitly. An existing output directory is never overwritten. No model inference or training occurs.


## First real contract DRAFTS 001 (11 Oct 2026)

The first three rows of `runs/cep002-data-intake-001/candidates-review.jsonl` (allowed local *GSM8K main/train*, NOT competition evaluation) are mapped into tightly scoped math contract drafts by `diagnostics/cep002_real_contract_drafts.py`. It checks expected source-question SHA-256 hashes, source/revision, gold answers, and exact arithmetic using `fractions.Fraction`.

- `gsm8k-train-00664`: dog lifespan `2.5*4=10`, fish lifespan `10+2=12`.
- `gsm8k-train-06718`: shampoo `1/3+1/4=7/12`, at `1/12` bottle per day => **7 days**. Exact twelfths, no rounding.
- `gsm8k-train-03644`: `240+500=740`, Twitter `370`, TikTok `1110`, YouTube `1620`, total `3840`.

**Strict gate:** all drafts stay **UNVERIFIED** with `reviewed_by=""`, `overlap_screen_passed=false`, `approved_for_training=false`. These hand-authored reference traces are NOT Qwen generations, XP locks, or training targets. Exact arithmetic checks numerical consistency but **do not independently review the semantic translation from source questions to contracts**. These three questions are now seen and cannot later qualify as an untouched holdout.

Added 11 CPU tests: `python -m unittest tests.test_cep002_real_contract_drafts -v`. First `python -m diagnostics.cep002_real_contract_drafts --dry-run`, followed by explicit `--execute`. An existing output path is never overwritten.
