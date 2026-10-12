# 🧠 BottleCapAI — ThinkingCap Test

[🇨🇿 Čeština](CZ%20docs/README.md) · **🇬🇧 English**

[![Challenge](https://img.shields.io/badge/Challenge-BottleCapAI_ThinkingCap-7C3AED)](https://github.com/BottleCapAI/ThinkingCap-Test)
![Research status](https://img.shields.io/badge/Research-in_progress-yellow)
![Benchmark status](https://img.shields.io/badge/Full_benchmark-not_run-orange)
![GPU](https://img.shields.io/badge/GPU-GTX_1070_Ti_8GB-76B900?logo=nvidia&logoColor=white)
![CPU](https://img.shields.io/badge/CPU-Intel_i5--3450-0071C5?logo=intel&logoColor=white)
![Mainboard](https://img.shields.io/badge/Mainboard-ASUS_P8B75--M-232323)
![RAM](https://img.shields.io/badge/RAM-16_GB-475569)
![License](https://img.shields.io/badge/Upstream-Apache_2.0-2563EB)

> 🐇 Rabbit Hollow Research: explore **RHAR — Rabbit Hollow Adaptive Reasoning**, a modular research concept for shorter Qwen3-0.6B reasoning without sacrificing accuracy.

**Active research direction:** RHAR-CEP 002 (VPS + XP + REC + Verified Lock), **a proposed algorithm not yet implemented or trained**. Earlier RPS/RPD/TPC ideas remain archived; conventional SFT adapters have been locally evaluated, but this does not demonstrate CEP 002.

## 🎯 Challenge

Improve the reasoning model's efficiency by **changing the model's behavior**, not by setting `enable_thinking=false` or relying on a prompt alone.

- **Base model:** `Qwen/Qwen3-0.6B`.
- **Goal:** reduce total generated tokens (thinking + final answer) while maintaining comparable accuracy.
- **Benchmarks:** SVAMP, MBPP+, BFCL, IFEval.
- **Rules:** never train on evaluation benchmarks; do not change the official evaluation settings.
- **Current status:** exploratory local Validation 007 completed on 40 GSM8K-train questions (SFT004 17/40 correct, 4,611 tokens; SFT003 14/40, 4,885 tokens; original Qwen 6/40, 19,860 tokens and 32 truncations). **No official BottleCapAI benchmark; no CEP 002 implementation or claim of generalization.**

## 🖥️ Development PC

| Component | Configuration |
| --- | --- |
| GPU | **NVIDIA GeForce GTX 1070 Ti**, 8 GB VRAM |
| CPU | **Intel Core i5-3450**, 3.10 GHz, 4 cores / 4 threads |
| Motherboard | **ASUS P8B75-M** |
| RAM | **16 GB** |

Details, limitations, and an external-GPU plan: [docs/HARDWARE.en.md](docs/HARDWARE.en.md). The GTX 1070 Ti may be used for lightweight local experiments, but official vLLM evaluation requires a newer GPU. A full local benchmark on this card is not expected.

## 🔬 Research files

- [🧪 RHAR Validation 007 — local base vs SFT003 vs SFT004](docs/RHAR-VALIDATION-007.en.md) — 40-question exploratory result, user-provided GPU log, data-screen and truncation limitations. [Czech](CZ%20docs/RHAR-VALIDATION-007.md).
- [🧠 RHAR-CEP 002 — VPS + XP + REC algorithm (research proposal)](docs/CEP-002.en.md) — verified procedural steps, up to three real strategies, proven retroactive corrections and a small controlled experiment; **documentation only, no new GPU/training**. [Czech](CZ%20docs/CEP-002.md).
- [🐇 RHAR Safe Start — prepare 36 generations safely](docs/SAFE-START-GENERATION.en.md) — explicit-gated future Qwen3 runner, 24 new CPU tests, no GPU execution. [Czech](CZ%20docs/SAFE-START-GENERATION.md).
- [🛡️ Safe Start — CPU-only official evaluation overlap audit](docs/SAFE-START-OVERLAP.en.md) — six pinned source objects, 18 new tests, no GPU. [Czech](CZ%20docs/SAFE-START-OVERLAP.md).
- [🐇 RHAR Safe Start GSM8K CPU intake](docs/SAFE-START-DATA.en.md) — SHA-256 pinned main/train, 12 deterministic review candidates and 16 new unit tests. [Czech](CZ%20docs/SAFE-START-DATA.md).
- [🐇 RHAR Safe Start — implementation plan and CPU tests](docs/SAFE-START.en.md) — 12 math questions × 3 planned generations; no GPU used. [Czech](CZ%20docs/SAFE-START.md).
- [RHAR v0.1 offline selector](docs/OFFLINE-SELECTOR.en.md) — review existing generations, strict correctness checks, selection and CPU tests. [Czech](CZ%20docs/OFFLINE-SELECTOR.md).
- [RHAR v0.1 — research protocol](docs/RHAR-V01-PLAN.en.md) — approved direction, proposed data pipeline, metrics and approval boundaries. [Czech](CZ%20docs/RHAR-V01-PLAN.md).
- [IDEA.md](IDEA.md) — hypothesis, method, measurement plan, and experiment log. [Czech](CZ%20docs/IDEA.md).
- [docs/DEV-NOTES.en.md](docs/DEV-NOTES.en.md) — development diary, progress and approval decisions. [Czech](CZ%20docs/DEV-NOTES.md).
- [docs/UPSTREAM-README.md](docs/UPSTREAM-README.md) — original challenge. [Czech translation](CZ%20docs/UPSTREAM-README.md).
- [docs/REASONING-DIAGNOSTIC.en.md](docs/REASONING-DIAGNOSTIC.en.md) — read-only Qwen3 reasoning diagnostic, with CPU unit tests. [Czech](CZ%20docs/REASONING-DIAGNOSTIC.md).
- [📊 Experiment 002 — visual report](docs/experiments/002-reasoning-baseline.en.md) — measured metrics, reasoning ratio, incorrect answer, and investigation. [Czech](CZ%20docs/experiments/002-reasoning-baseline.md).
- `train.py`, `evaluate.py`, `compare.py` — official BottleCapAI tools.

## 🤝 Working with AI

I work on the project together with **ChatGPT (OpenAI, GPT-6)** and **my own local GGUF agent, Máša**. I disclose AI assistance for hypothesis discussions, development and documentation. I separate real measurements and my decisions from AI proposals; I do not attribute specific commits or tests to Máša without evidence. See my [development diary](docs/DEV-NOTES.en.md).

## ✅ Experiment principles

**No progress without green tests.** Every intervention must have repeatable verification and a baseline comparison. Record negative results and the exact hardware used, too.

Important technical decisions, experiments, and major changes are discussed first; I make the final decision. See the [development diary](docs/DEV-NOTES.en.md).

Original challenge: [BottleCapAI/ThinkingCap-Test](https://github.com/BottleCapAI/ThinkingCap-Test). The upstream source is distributed under Apache-2.0; see [LICENSE](LICENSE).
