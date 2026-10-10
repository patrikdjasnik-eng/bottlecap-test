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


## Candidate CEP 002 extension — Verified Procedural Experience Learning (proposal, 2026-10-10)

**User-originated hypothesis:** Do not memorize a final answer to a specific problem. Instead, after solving and independently verifying an allowed training problem, extract the **reusable procedure** and its applicability conditions. Accumulate these verified procedural experiences and distill their use into the Qwen3-0.6B LoRA weights, so that later *new* problems with matching structure can be solved accurately with less repeated reasoning. Informal analogy: the model gains “XP” by learning verified skills.

Proposed pipeline: (1) solve a permitted training problem; (2) check final answer and check intermediate relations when feasible; (3) abstract the procedure, inputs, constraints, and failure conditions rather than storing only a numeric output; (4) validate the generalized procedure on independently generated training-domain variations; (5) retain versioned, provenance-linked verified experience; (6) train the model on applicable short, correct traces and compare against matched SFT and CEP 001 controls on **unseen held-out tasks**. Prefer no runtime retrieval or answer cache in the official evaluation; the claimed improvement must reside in trained weights.

Example: learn the transferable rule `floor(total * (1-reserved_fraction) * (1-defective_fraction) / package_size)`, not the memorized answer `20`. Changing when percentages apply must invalidate the rule; similarity alone is not evidence of applicability.

**Failure guards:** verification of the final number does not prove the reasoning; reject inconsistent intermediate steps and accidental shortcuts. Do not continually train on scored evaluation questions, official benchmarks (SVAMP/MBPP+/BFCL/IFEval), or their solutions. Separate saved experience memory as **training data preparation**, not an inference-time external memory that would distort token counts. Avoid feedback loops, catastrophic forgetting, and claims that each experience automatically improves accuracy. Evaluate correctness *and* total emitted tokens (thinking + final), not token savings alone.

**Status:** Concept only; no procedural XP memory, verification pipeline, or CEP 002 training has been implemented or benchmarked. The general ideas of verified self-training, procedural abstraction, and memory reuse have prior art. Any originality and measurable advantage must be established experimentally.


### 🧠 CEP 002 — REC: Retroactive Experience Correction

**New research hypothesis, not an implemented feature.** If a later, independently verified procedure on an allowed training question (e.g. question 10) conflicts with an earlier stored solution (e.g. question 3), REC would flag the old record for re-verification. Ordinary Qwen inference does **not** remember past independent runs, know that an earlier answer was wrong, or update weights automatically. REC is a working name, not a claim of scientific novelty.

**Proposed offline training-data workflow:**

1. **Provenance and versioning:** save question ID/hash, source/split, original reasoning and final answer, assumptions, verification state and history. Keep **up to three actually available independently verified applicable strategies** per problem structure; never invent a missing third. Alternatively select three broader transferable procedures across allowed training questions.
2. **Retroactive trigger:** a later verified derivation, counterexample or contradiction may flag a prior related record for review. Similarity alone is insufficient. Immediate versus end-of-batch rechecking remains an open design choice with bounded compute cost.
3. **Independent verifier:** re-check the old task, final answer and testable intermediate relations using deterministic arithmetic, constraint solving or executable tests. An LLM judge can flag suspected errors but is not a trusted oracle. Inconclusive cases remain unverified.
4. **Preserve history:** keep the original generation immutable; append a new version with an exact failure cause, independent evidence, corrected procedure and applicability conditions. Track **XP+** (verified correct), **XP−** (verified failure under given conditions) and **REC** (correction history). Accidentally correct final answers with faulty reasoning are not verified positive traces.
5. **Transfer, then train:** test abstraction on new permitted training-domain variations with changed numbers and constraints. Only after separate user approval train a LoRA using verified procedures/preferences, then evaluate on a fresh unseen holdout for correctness, completion, total emitted tokens (thinking and final), false-correction rate and REC overhead.

**BottleCapAI compliance:** REC operates **offline during data preparation**, not as a custom inference-time memory or multiple-answer controller in the official evaluate.py run. The submitted Qwen3-0.6B / LoRA must load in standard Transformers and vLLM; thinking stays enabled; official prompts, sampling and token caps stay unchanged. Never use SVAMP, MBPP+, BFCL or IFEval for training. The **60 reviewed Evaluation 006 questions** are no longer fresh unseen validation examples. If converted to training data, exclude them from any later independent holdout claims; building REC from different allowed training examples is preferable.

**Status:** research proposal/documentation only. No REC code, GPU action, CEP 002 training, or demonstrated effect. Implementation, data selection and compute budget require separate approval.

