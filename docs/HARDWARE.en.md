# 🖥️ Hardware — Rabbit Hollow Research

Configuration as reported by Windows PowerShell diagnostics (October 8, 2026).

| Component | Details |
| --- | --- |
| **GPU** | NVIDIA GeForce GTX 1070 Ti, **8 GB VRAM** |
| **CPU** | Intel Core i5-3450 @ 3.10 GHz, **4 cores / 4 threads** |
| **Motherboard** | ASUSTeK COMPUTER INC. **P8B75-M** |
| **RAM** | **16 GB** |
| **Development environment** | Windows + PowerShell; WSL2/Kali available |

## Limitations and decisions

The GTX 1070 Ti is a Pascal GPU (compute capability 6.1). The standard vLLM CUDA backend used by the official `evaluate.py` does not support this GPU generation; therefore, **we will not report fictional benchmark results**.

- Locally: static checks, pytest, unit tests, training-data preparation, short inference experiments if a suitable runtime works.
- Training: prefer LoRA on an available external GPU, e.g. Google Colab T4 16 GB (fp16, not bf16).
- Official final evaluation: a GPU supported by vLLM, ideally Ampere or newer.
- Comparison: baseline and candidate with the same evaluation settings; measure accuracy and total tokens, and preserve confidence intervals (CIs).

## Performance log

| Date | Model / adapter | Device | Evaluation | Tokens saved | Accuracy change |
| --- | --- | --- | --- | --- | --- |
| — | Qwen3-0.6B | not yet run | pending | — | — |

No performance number is considered measured until an actual run has been completed.
