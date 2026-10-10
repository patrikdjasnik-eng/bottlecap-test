# IDEA.md — RHAR: Causal Evidence Preservation (CEP)

**Status, 2026-10-10:** one active research hypothesis, **not** a proven novel algorithm or a successful BottleCapAI submission.

[🇨🇿 Czech research direction](CZ%20docs/IDEA.md) · [Development history](docs/DEV-NOTES.en.md)

## Challenge objective

Modify **Qwen3-0.6B** to produce fewer **total generated tokens including thinking**, while retaining accuracy. Keep thinking enabled, use non-evaluation data for training, and preserve the upstream `evaluate.py` / `compare.py` settings. Never train on **SVAMP, MBPP+, BFCL, or IFEval**.

## One active hypothesis — RHAR-CEP

**Causal Evidence Preservation (working title):** It may be possible to teach concise reasoning *without losing correctness* by protecting indispensable dependencies from **problem inputs → calculations/justification → answer**, instead of merely shortening sequences or selecting the shortest correct final answer.

This is a proposed mechanism, **not yet specified sufficiently for implementation and not yet trained**. The causal importance of a step must be supported by an independently testable procedure; deleting a sentence or matching the final answer is not sufficient evidence. The distinguishing algorithm and its effect remain unproven.

## Evidence that motivated it

Training 001: actual rank-8 LoRA technical pilot with one GSM8K sample. Training 002: actual LoRA SFT with 11 GSM8K reference rationales and 60 steps. In one exploratory comparison, the base model generated **512 tokens** and was truncated, while Training 002 generated **137 tokens**, terminated, but answered **4.5 hours** instead of **6** after substituting 90 km for the input 180 km. Both were incorrect under strict completion grading. Thus **73.24% fewer observed tokens is not accuracy-preserving compression**, and the base measurement is capped. No generalization or official BottleCapAI success has been demonstrated.

Training 003 is conventional GSM8K LoRA supervised fine-tuning with validation and checkpoints, as a **control baseline**. Its GPU completion is not evidenced in the current research record. CEP is not yet implemented.

## The single controlled experiment

- **Base:** unchanged Qwen3-0.6B.
- **SFT control:** ordinary Training 003 on allowed data.
- **CEP candidate:** a precisely defined dependency-preserving training intervention on matched permissible data/budget, *if implemented*.

Measure strict correctness, completed answers, and generated tokens (thinking + final) on disjoint questions with identical evaluation conditions. Run the untouched official benchmarks where compatible hardware permits. **Shorter incorrect generations are failures.** If CEP does not beat plain SFT on the length/accuracy tradeoff out of sample, revise or reject the hypothesis.

## Prior work and originality

LoRA, SFT, selecting short correct traces, and protecting key reasoning steps already have prior art:
- Keypoint-based Progressive CoT Distillation (ICML 2024): https://proceedings.mlr.press/v235/feng24e.html
- Less is More Tokens (2025): https://arxiv.org/abs/2509.05226
- LEASH (2026): https://aclanthology.org/2026.acl-long.129/

The possible RHAR contribution would be **a specific verified dependency-preservation training signal**, plus controlled evidence that it helps beyond baseline SFT. We do not claim world-first originality; similarity to further published or unpublished methods must still be checked.

## Scope and submission

Only one active question: **Can evidence-preserving compression shorten Qwen3-0.6B without sacrificing correct answers, better than standard SFT?** RPS, RPD, TPC, HRM and other ideas are archived possibilities, **not parallel modules or active tests**. Details and negative experiments remain in the development diary, not the active plan.

Submission requires an honest `IDEA.md`, model/LoRA safetensors, git bundle, and official results when available; report any missing evaluation transparently. No training or GPU action is initiated by this documentation.
