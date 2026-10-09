# 🔬 Reasoning diagnostic — Qwen3-0.6B

[🇨🇿 Čeština](../CZ%20docs/REASONING-DIAGNOSTIC.md) · [🇬🇧 English](REASONING-DIAGNOSTIC.en.md)

## Objective

**Observe only** the original Qwen3-0.6B model: separate reasoning from the final answer and log correctness, time, token counts, repetition, and GPU memory. This is not training, a model improvement, or the official BottleCap AI benchmark.

## BottleCap AI rules

- Thinking stays **enabled** (`enable_thinking=True`).
- The prompt specifies only the output format (`Final answer: ...`) — it **does not request shorter reasoning**.
- The script does not modify weights, create an adapter, or change the official `evaluate.py`, `compare.py`, or evaluation settings.
- All questions are hand-written (math, logic, code comprehension), **not** copied from SVAMP, BFCL, MBPP+, or IFEval.
- Any future reasoning compression algorithm **requires the project owner's approval**.

## Running on WSL2 / Kali

From the project with `.venv` activated (PyTorch and Transformers already prepared):

~~~bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate

# 1. Quick CPU tests (no model download or network)
python -m unittest tests.test_reasoning_probe -v

# 2. Show configuration and cases (no model download)
python -m diagnostics.reasoning_probe --dry-run

# 3. First real measurement (one question, one generation)
python -m diagnostics.reasoning_probe --limit 1

# 4. With approval for further measurements: three domains, two samples
python -m diagnostics.reasoning_probe --limit 3 --samples 2
~~~

Default: 3 questions × 1 generation, 512 new token cap; seed 9001, temperature 0.6, top-p 0.95, top-k 20, `float16` on CUDA. Uses the exact original-model revision pinned in the official `evaluate.py`.

## Output

Under `runs/diagnostics/<UTC timestamp>/`:

- `config.json` — model, revision, parameters, device, and sample count.
- `records.jsonl` — individual answers, reasoning/final lengths, durations, correctness, repetition, and PyTorch memory data.
- `summary.json` — aggregate **exploratory** metrics.

The `runs/` directory is ignored by Git: raw generated output (including reasoning) is **not published automatically**.

## Interpretation

- `total_tokens`: all generated tokens.
- `reasoning_tokens`: reasoning segment including boundary tokens; `final_tokens`: final segment including any EOS. They sum to `total_tokens` **when parsing succeeds**.
- `split_status`: if thinking markers are missing or malformed, reasoning/final counts are `null`, never an invented zero.
- `truncated`: generation did not finish with a recognized end token; such responses count as incorrect.
- `repeated_reasoning_fourgrams`: very rough four-word repetition indicator, **not** a reasoning quality metric.
- `pytorch_allocated_gib` and `pytorch_peak_allocated_gib`: PyTorch-tracked allocation only, not total GPU VRAM occupancy.
- `exploratory_accuracy`: fraction correct on only these diagnostic cases. **Not official BottleCap AI accuracy.**

## Status

- [x] Diagnostic CPU unit tests: **9/9** passed locally.
- [x] `--dry-run` tested locally.
- [ ] First diagnostic GPU run on GTX 1070 Ti: **awaiting user's output**.
- [ ] Decision on further experiments: **requires owner's approval**.

Record measurements and decisions in the [development diary](DEV-NOTES.en.md).
