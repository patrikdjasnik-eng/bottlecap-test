# 🛡️ RHAR Safe Start — CPU-only audit for evaluation overlap

[🇨🇿 Česky](../CZ%20docs/SAFE-START-OVERLAP.md) · [GSM8K selection](SAFE-START-DATA.en.md) · [DEV-NOTES](DEV-NOTES.en.md)

**Approval, 2026-10-10:** after the **61/61 green Kali tests** and discovering that `questions/questions.jsonl` was absent, I authorized **only downloading the necessary pinned official evaluation source data and screening candidate overlap on CPU**. **I did not authorize official evaluation, model inference, GPU use, or training.**

## 📌 Sources and provenance

The separate `diagnostics/safe_start_overlap.py` auditor uses the same source revisions as the unmodified `utils/eval/benchmarks.py`:

| Family | Provenance pin | Read only prompt/question text from |
| --- | --- | --- |
| SVAMP | commit `78e727689e1c1bebfc4be39c446898e8e10b0518` + SHA-256 | `SVAMP.json`: Body + Question |
| MBPP+ | release `v0.2.0` + SHA-256 of decompressed content | `MbppPlus.jsonl.gz`: prompt |
| BFCL | commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` | three BFCL v4 categories: simple_python, multiple, irrelevance; user messages |
| IFEval | commit `4700efb9afa54286b0e04473ba80a13e8461e25f` | `input_data.jsonl`: prompt |

There are **six source objects and four benchmark families**. SVAMP and MBPP+ use the known content SHA-256 pins already present in our official-evaluation source code. BFCL and IFEval URLs are pinned to Git commits; their actual downloaded hashes are recorded, but no separately established expected content hashes are embedded.

These original data files may also contain reference answers and metadata; the audit **extracts only prompt text and never writes the other fields to its report**. Sources are loaded temporarily into memory, not installed as evaluation/training files. Read sizes are bounded.

## 🔍 Screening protocol

1. Read the existing **12 GSM8K candidates** and verify their ordered IDs and question SHA-256 against the immutable `selection-report.json`. Never reselect or edit candidates.
2. Only with explicit `--download`, read all six pinned sources. **Unavailable input, a mismatching pinned checksum or unexpected schema fails closed**: a partial screen cannot be reported as clean.
3. Compare normalized question text via **exact matching** and the `close_match` near-duplicate heuristic.
4. Create a new ignored `data/safe-start/overlap-audit.json` with counts, source hashes, candidate IDs and potential matching source indices. **No original files are overwritten.**
5. Always record `training_approved=false`, `overlap_audit_exhaustive=false` and `semantic_paraphrases_ruled_out=false`. **Zero matches does not rule out all paraphrases or authorize training.**

## 🧪 Run on Kali

First the CPU regression suite: 61 earlier tests plus **18 new overlap tests**, so expect **79** tests:

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data tests.test_safe_start_overlap -v
```

**Only after passing**, execute the separately approved one-shot fetch/screen:

```bash
python -m diagnostics.safe_start_overlap --download
```

The result is printed and saved to `data/safe-start/overlap-audit.json`. **Do not run `python utils/eval/benchmarks.py`, `evaluate.py`, or a trainer.** If a fetch or parser fails, stop and share the traceback rather than treating the check as complete. The tool refuses to overwrite a previous report.

For our review I need only the JSON audit report, **not the original candidate question text or gold answers**.

## ✅ Verification status

- **Previously verified:** 61/61 CPU tests on Kali (`Ran 61 tests in 0.600s`, `OK`), 12 selected GSM8K candidates and a verified dataset SHA-256.
- **New implementation:** `diagnostics/safe_start_overlap.py` and **18/18 isolated local CPU unit tests passed**. Unit tests mock HTTP; they are not evidence of successfully fetching the real upstream sources.
- **Still pending on Kali:** the combined **79/79 test suite** and the actual six-source download and overlap report. **No model inference or training has occurred.**

I keep final research decisions myself and collaborate with **ChatGPT (OpenAI, GPT-6)** and my local AI assistant **Máša**; I do not attribute unverified runs to either.
