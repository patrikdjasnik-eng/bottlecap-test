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
