# IDEA.md — RHAR: Rabbit Hollow Adaptive Reasoning

**Status (2026-10-09):** I **chose RHAR as a unified modular research direction**. This authorizes the concept, not specific training methods, architectural code changes, expenditure, or model weight updates.

[🇨🇿 Czech version](CZ%20docs/IDEA.md) · [Development diary](docs/DEV-NOTES.en.md)

## Motivation

The original Qwen3-0.6B can produce unnecessary reasoning tokens. We want to reduce **total generated tokens (reasoning + final answer)** without meaningfully compromising accuracy across different tasks. Prompt-only shortening and turning off thinking are explicitly not acceptable methods.

## Hypothesis

**RHAR** investigates whether a model can learn more efficient reasoning when training considers **information progress (RPS)**, **recoverability of essential information (RPD)**, and **protection of general capabilities (TPC)** together.

This is an *unproven research hypothesis*. Related methods already exist; we do not claim world-first novelty or demonstrated improvement.

## The three modules

| Module | Hypothesized function | Research question | Status |
| --- | --- | --- | --- |
| **RPS — Reasoning Progress Signature** | Measure informative progress versus redundancy in reasoning steps, potentially including hidden-state signals | Can the model learn to avoid unproductive reasoning? | Concept approved, implementation unspecified |
| **RPD — Reversible Proof Distillation** | Assess whether shortened reasoning preserves sufficient information for independent reconstruction or verification | Does concision preserve crucial proof content? | Concept approved, implementation unspecified |
| **TPC — Transfer-Protected Compression** | Monitor and constrain capability regressions across math, coding, function calling and instruction following | Will compression generalize rather than overfit one domain? | Concept approved, implementation unspecified |

These mechanisms should ideally affect **what the model learns**, not require costly extra verification agents on every inference. Feasibility and overhead remain open questions.

## HRM — Hallucination Risk Monitor (research candidate)

**Status:** On 2026-10-09 I **decided to record this idea in Markdown**. HRM is a **proposed observational/risk-assessment extension**, **not yet a formally approved fourth RHAR module**, training component, or implemented experiment.

**Research question:** Can signals produced while studying RHAR predict the risk of an incorrect or unsupported response **before** correctness is independently verified? An error on a numerical task is not automatically a factual hallucination; distinguish the two in measurement and reporting.

**Proposed signals (not yet implemented):**

| Signal | Proposed observation | Limitation |
| --- | --- | --- |
| Answer instability | Variation of final answers over repeated samples | Agreement does not guarantee truth; extra generations cost time |
| RPS false progress | High reasoning activity or repetition without measurable advancement | A progress metric must first be validated, not inferred from verbosity |
| RPD information loss | Inconsistency or failure to reconstruct essential steps and the conclusion | Verification can itself be unreliable and expensive |
| External grounding | Claims contradicted by a provided source, known numerical result, or executable test | Requires suitable external evidence; unknown facts cannot be declared false |

**Measurements to propose and validate:**
1. Start with a **risk score**, not a claimed hallucination probability.
2. Label a separately collected dataset with a verifiable ground truth. Record **incorrect answer** and **unsupported factual claim** as distinct labels.
3. Use an independent calibration/validation split to map scores to probabilities only if supported by evidence. Evaluate **Brier score**, **expected calibration error (ECE)** and discrimination (e.g. **AUROC**, if both classes exist).
4. Compare against simple baselines such as model answer consistency. Measure predictive value of each RPS/RPD/TPC-derived signal through ablations.
5. Account for extra compute and memory. Prioritize lightweight single-generation probes locally on the GTX 1070 Ti; repeated sampling should be separately justified.
6. Never fit HRM using SVAMP, MBPP+, BFCL or IFEval held-out evaluation data. Keep official evaluation settings unchanged.

**Existing diagnostic:** `diagnostics/reasoning_probe.py` currently records correctness for a few hand-written tasks, counts and repetition, but **does not calculate risk, calibrated hallucination probability, factual grounding, ECE or Brier score**.

**Explicitly deferred:** HRM architecture, feature extraction, thresholds, calibration dataset, source checking, training integration and code changes require **my separate decision**. The idea must not be described as a verified novelty, measured improvement, or accurate prediction system.

## RHAR v0.1 — approved direction and proposed protocol

I approved **Correctness-Gated Reasoning Compression** as the first training-oriented research direction: search for **correct, complete, relatively short reasoning traces** before testing whether the model can learn from them. **The direction is approved, but implementation, dataset acquisition, GPU budget and training are not yet authorized.** I documented the details in [RHAR-V01-PLAN.en.md](docs/RHAR-V01-PLAN.en.md). Simple shortest-correct selection by itself is not an established novel algorithm.

## Modular research plan (further experiments not yet authorized)

1. Measure the unchanged base model: exact answers, reasoning/final/total token counts, time, variance and failures.
2. Investigate **RPS separately** and determine whether progress/redundancy signals are reliable beyond one problem.
3. Investigate **RPD separately** on permitted training or research data; measure reconstruction reliability and its computational cost.
4. Investigate **TPC separately** using separate allowed training/validation tasks across several domains, without fitting to official held-out evaluation data.
5. Perform **ablation comparisons** of base, individually testable modules, RPS+RPD and RPS+RPD+TPC; preserve matched experimental settings.
6. **After I explicitly approve the next step**, select training objectives and data, choose LoRA or another model modification, define the compute budget, and run training.
7. Evaluate trained candidates with unchanged official `evaluate.py`; compare paired base/candidate outputs using `compare.py`.

The previous correctness-filtered short-reasoning distillation idea remains a **possible training baseline**, not an approved or implemented RHAR algorithm.

**First v0.1 offline step implemented:** `diagnostics/offline_selector.py` with 16 CPU tests — review of existing generations and review-only candidate selection, **no model training**. See [OFFLINE-SELECTOR.en.md](docs/OFFLINE-SELECTOR.en.md). A specific RHAR learning mechanism remains undecided.

## Metrics and evaluation

- **Primary:** correctness and total generated tokens including thinking and final answer.
- **Diagnostic:** reasoning/final split, repetition indicators, truncation, time, variability, GPU use, per-domain regressions and reconstruction outcomes.
- **Controls:** matched sampling/seeds and prompts for comparisons; clear training/validation split; ablations; failure logs.
- **Official held-out evaluation:** SVAMP, MBPP+, BFCL and IFEval, using the supplied recipe and paired uncertainty intervals. **Never train on these benchmarks.**
- **Novelty:** compare an implemented mechanism with the closest literature before claiming novelty; unseen private work cannot be ruled out.

## Constraints

- Base model: `Qwen/Qwen3-0.6B`. Final model remains approximately 0.6B and **continues to reason**.
- **Never use prompt engineering alone to shorten thinking; never switch thinking off.**
- Do not change the official benchmark prompts, generation settings, token cap or scoring.
- Keep standard Hugging Face Transformers/vLLM compatibility for final submission.
- Never invent benchmark scores, improvements, originality, or tests that did not happen.
- **I explicitly decide on major changes before implementation**; documentation of this approved concept does not authorize new experiments.

## Current status and observations

- **My verified exploratory inference:** correct `Final answer: 43`, 371 generated tokens, 61.45 seconds, 6.04 tokens/s and 1.12 GiB allocated PyTorch memory on GTX 1070 Ti. **One unofficial question, not a measured improvement.**
- **Read-only diagnostic:** `diagnostics/reasoning_probe.py` exists with independent tests; my first GPU diagnostic completed: 325 tokens, incorrect 42 rather than 43 (Experiment 002).
- **RHAR:** direction approved, mechanisms and training unimplemented, **no RHAR results yet**.

## Hardware

See [docs/HARDWARE.en.md](docs/HARDWARE.en.md). Local machine: GTX 1070 Ti 8 GB (compute capability 6.1), i5-3450, ASUS P8B75-M, 16 GB RAM. Local PyTorch CUDA inference works; official vLLM evaluation needs a supported GPU. Hidden-state diagnostics and training feasibility have not been established.

## What worked / failed

Record actual runs, negative findings, hardware and decisions in [docs/DEV-NOTES.en.md](docs/DEV-NOTES.en.md). No RPS/RPD/TPC training experiment has been performed.



## Research originality review — 2026-10-10 (prior-art checkpoint)

**BottleCapAI wording:** “We're interested in your own ideas, not how well you can copy other's.” The four formal rules permit LoRA and fine-tuning on permitted non-evaluation data; they demand an unchanged evaluation and honest documentation. **Using a published baseline is allowed; claiming it is novel is not.** Do not train on SVAMP, MBPP+, BFCL or IFEval. 

**Current actual implementation:** RHAR Training 001 and 002, and planned Training 003, use ordinary LoRA supervised fine-tuning (SFT) on GSM8K responses or reference rationales, with a correct final answer and explicit thinking boundaries. This is an *established training baseline*, **NOT an invented RHAR compression algorithm**. RHAR modules RPS, RPD and TPC are hypotheses; there is no proven implementation. Existing Eval 002 observed 137 vs 512 tokens on one question, but the trained adapter answered 4.5 instead of 6 hours. Therefore it does **not** establish accuracy-preserving compression. Do not call the implementation novel, world-first, or an improvement on BottleCapAI metrics.

**Documented nearby research (citations and methods to check for overlap):**
- *Less is More Tokens: Efficient Math Reasoning via Difficulty-Aware Chain-of-Thought Distillation* (2025), https://arxiv.org/abs/2509.05226 : difficulty-proportional traces and SFT + preference optimization.
- *Making Small Language Models Efficient Reasoners: Intervention, Supervision, Reinforcement* (2025), https://arxiv.org/abs/2505.07961 : stopping-time and length-regularized RL.
- *Towards Structural Understanding of LLM Overthinking* (ACL 2026), https://deepmind.google/research/publications/203490/ : analysis of Qwen-family oververification/overexploration via thought progression graphs.
- *LEASH: Adaptive Length Penalty and Reward Shaping* (ACL 2026), https://aclanthology.org/2026.acl-long.129/ : adaptive length reward.
- *When Internalization Fails: Finding Better Targets for Reasoning Compression* (ACL Findings 2026), https://aclanthology.org/2026.findings-acl.734/ : alternatives for CoT shortening targets.
- *Keypoint-based Progressive Chain-of-Thought Distillation* (ICML 2024), https://proceedings.mlr.press/v235/feng24e.html : emphasis on reasoning keypoints.
- *AutoL2S: Auto Long-Short Reasoning* (2025), https://arxiv.org/abs/2505.22662 : adaptive short/long traces.

**Novelty gate:** Before presenting an RHAR mechanism as original, write an executable definition (inputs, outputs, learning signal, objective), cite the nearest prior method, state the actual difference and devise an ablation: plain SFT vs RHAR candidate on identical training data, base model and evaluation protocol; measure total tokens AND correctness, including task transfer. A renamed loss, another wrapper/validator or simple shortest-correct trace selection **does not satisfy novelty by itself**. Any originality assertion is provisional: one literature check cannot exclude unpublished/prior work. Continue Training 003 **only as a disclosed SFT control baseline**, not as the final novel algorithm. The official submission can transparently report negative results.
