# 🔬 DEV-NOTES — Development diary

[🇨🇿 Česky](DEV-NOTES.md) · [🇬🇧 English](DEV-NOTES.en.md)

## Collaboration rules

- **The project owner approves important technical decisions, new experiments, and major ideas.** The assistant must first explain the options, benefits, and risks, then ask for approval.
- Do not change the research direction, model, training strategy, benchmark settings, project structure, or make major repository changes without prior approval.
- Routine documentation updates and technical fixes within an explicitly approved scope can proceed if clearly recorded in the diary.
- Distinguish **completed / verified / proposed / awaiting approval / failed**. Never fabricate test success or benchmark results.
- Entries must include date, changes, rationale, verification, and next step. Material decisions must have an explicit approval status.
- **No step forward without green tests** for code changes; verify structure and links for documentation changes.

## Diary

### 2026-10-09 — Collaboration rules and language mirrors

**Status:** rules confirmed by the project owner; bilingual documentation is being added on the development branch.

**Completed:** DEV-NOTES designated as a development diary instead of merely a to-do list. Added approval requirements for major decisions. Started Czech and English documentation mirrors.

**Verification:** previous user-run unit tests: 87 OK, 2 skipped; no new training or benchmarking has been performed as part of these documentation updates.

**Awaiting approval:** specific reasoning-compression algorithm, training approach, first GPU experiment, and any code changes.

## Previous status overview

## Status — October 9, 2026

- [x] Created a standalone repository and development branch `feat/reasoning-compression`.
- [x] Imported the official BottleCapAI Python scripts, tests, and license.
- [x] Documented the actual PC configuration and GPU limitations.
- [x] Prepared the research plan in `IDEA.md`.
- [x] Ran local unit tests (Kali Linux / WSL2, Python 3.14.7): **87 tests OK, 2 skipped** (EvalPlus and BFCL not yet downloaded), duration 0.321 s.
- [x] Set up isolated **Python 3.11.17** in `.venv` on Kali Linux / WSL2; user verified on October 9, 2026.
- [x] `nvidia-smi` in WSL2 detects **NVIDIA GeForce GTX 1070 Ti (8192 MiB)**, driver 582.78, nvidia-smi 580.178.01; 882 MiB in use at the time of checking. The reported `CUDA Version: 13.0` is the driver's capability, not proof that PyTorch works.
- [ ] Verify CUDA calculations with **PyTorch 2.6.0 + cu118** on the GPU (not yet tested); if an error occurs, do not confuse GPU detection with a working CUDA kernel.
- [ ] Install Transformers/Accelerate only after a successful PyTorch CUDA test.
- [ ] Verify the bubblewrap sandbox before MBPP+ evaluation (warning: only a weaker fallback with resource limits is available).
- [ ] Prepare training data without using evaluation benchmarks.
- [ ] Run the baseline smoke test and save run artifacts.
- [ ] Generate correct, concise reasoning traces.
- [ ] Train a LoRA adapter and run validation.
- [ ] Compare the full baseline and candidate evaluations on a supported GPU.
- [ ] Produce a reproducible final report, including negative results.

## Notes

The full project benchmarks use eight samples per question. The complete suite contains 2,759 tasks. Do not confuse synthetic metrics with official evaluation results.

After developing on the feature branch, open a PR to `main` only after validation.
