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


## Human semantic review 001 (11 Oct 2026)

Added `diagnostics/cep002_review_packet.py` and 12 CPU tests in `tests/test_cep002_review_packet.py`. The script links `runs/cep002-data-intake-001/candidates-review.jsonl` and `runs/cep002-contract-drafts-001/contract-drafts.jsonl` using source IDs and SHA-256. It rejects tampered original text, altered drafts, premature approval, and overwriting the review packet.

It writes **only** `runs/cep002-contract-drafts-001/review-packet.md`, containing the three original questions, proposed input facts, required relations, likely semantic pitfalls, and unchecked human-review checklist items. Decisions remain `PENDING`; **zero independently approved contracts, zero XP locks, zero training records exported**. The review packet is a review aid, not proof of independent correctness or authorization to train.

Before running: `python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake tests.test_cep002_real_contract_drafts tests.test_cep002_review_packet -v`. Twelve new tests bring the expected total to 67. Then `python -m diagnostics.cep002_review_packet --dry-run` and `python -m diagnostics.cep002_review_packet --execute`. New tests have not yet been run in the user's Kali environment.


## Historical screening against actual experiment files (11 Oct 2026)

The user confirmed **70 passing CPU tests** and found `data/safe-start/questions.jsonl`, both `runs/rhar-validation-005/records.jsonl` and `runs/rhar-validation-006/records.jsonl`, plus numerous other past pilot and diagnostic `records.jsonl` files in the original Kali repo.

Added **`diagnostics/cep002_history_overlap.py`** and **18 synthetic CPU regression tests** in `tests/test_cep002_history_overlap.py`. The audit reads only 12 already selected/reviewed CEP-002 Data Intake questions and 60 reserved `(ID,SHA256)` pairs without holdout question or answer text. It screens these against Safe Start source questions and all `runs/**/records.jsonl` in the **original** research working tree. New isolated CEP-002 draft/manifests are not misidentified as historical experiments. Checks literal task IDs, question SHA-256 hashes, SHA-256 of source question strings, normalized question equality and full question embedded in a user prompt. Model outputs, reference answers and generated reasoning are ignored.

**Fail-closed** when critical historical files are missing, manifests malformed, a JSONL file empty/corrupt, or output would overwrite an earlier audit. Unknown record schemas and ID-only rows are reported as incomplete question-text coverage. Even zero matches means only `partial_historical_screen_no_match`, **never training approval**. No official evaluation question/answer text is emitted; output contains IDs, file names and counts. No exhaustive semantic/paraphrase similarity proof.

From Windows PowerShell with the `cep` function:

```powershell
cep -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake tests.test_cep002_real_contract_drafts tests.test_cep002_review_packet tests.test_cep002_history_overlap -q
cep -m diagnostics.cep002_history_overlap --dry-run --safe-start /home/rabbithollow/bottlecap-test/data/safe-start/questions.jsonl --history-root /home/rabbithollow/bottlecap-test/runs
```

After green tests and successful dry-run, optionally call the same command with `--execute`. Never overwrites `runs/cep002-history-audit-001/summary.json` and `overlaps.jsonl`. **The 18 new tests and historical audit have not yet run on the user's Kali system**; expected test total is 88. No GPU/training/learning dataset export.
