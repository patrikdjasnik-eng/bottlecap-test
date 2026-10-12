"""RHAR Validation 007: BASE vs SFT 003 vs long SFT 004 on fresh GSM8K TRAIN.

This is a local research diagnostic, not an official BottleCapAI benchmark.
The evaluation set is reconstructed to be disjoint from:
- the historical 1000/100/80 partition and known historical GSM8K runs,
- CEP-002 review and reserved holdout IDs,
- Safe Start review IDs,
- Training 004's exact 2500 train + 100 loss-validation examples.

Official evaluation prompts are used only for contamination screening.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import random
from pathlib import Path

from .offline_selector import grade_final
from .reasoning_probe import BASE_MODEL, BASE_REVISION, split_reasoning
from .rhar_train_003 import reject_overlap
from .rhar_train_004 import build_protected_ids, prepare_long_pool, teacher_rows
from .safe_start_data import TRAIN_SHA256, read_eval_prompts, read_parquet

DEFAULT_SEED = 9001
DEFAULT_COUNT = 40
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
VARIANTS = ("base", "sft003", "sft004")


def select_fresh_validation(
    raw: list[dict],
    protected_ids: set[str],
    count: int = DEFAULT_COUNT,
    training004_train_size: int = 2500,
    training004_val_size: int = 100,
    training004_seed: int = 404,
    selection_seed: int = 7007,
) -> tuple[list[dict], dict]:
    if not 1 <= count <= 200:
        raise ValueError("count must be between 1 and 200")
    train004, val004, _ = prepare_long_pool(
        raw,
        protected_ids,
        training004_train_size,
        training004_val_size,
        training004_seed,
    )
    train004_ids = {row["question_id"] for row in train004 + val004}
    blocked = protected_ids | train004_ids
    candidates = [row for row in teacher_rows(raw) if row["question_id"] not in blocked]
    rng = random.Random(selection_seed)
    rng.shuffle(candidates)
    if len(candidates) < count:
        raise ValueError("insufficient fresh examples after Training 004 exclusion")
    selected = candidates[:count]
    selected_ids = {row["question_id"] for row in selected}
    if selected_ids & blocked:
        raise RuntimeError("fresh validation overlaps protected/training data")
    return selected, {
        "training004_train_ids_excluded": len(train004),
        "training004_loss_validation_ids_excluded": len(val004),
        "training004_total_ids_excluded": len(train004_ids),
        "fresh_candidates_available": len(candidates),
        "selection_seed": selection_seed,
    }


def metrics(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("empty metrics input")
    return {
        "correct": sum(bool(row["correct"]) for row in rows),
        "complete": sum(not bool(row["truncated"]) for row in rows),
        "truncated": sum(bool(row["truncated"]) for row in rows),
        "mean_tokens": round(sum(int(row["tokens"]) for row in rows) / len(rows), 2),
        "total_tokens": sum(int(row["tokens"]) for row in rows),
    }


def summarize(records: list[dict]) -> dict:
    if not records or len(records) % len(VARIANTS):
        raise ValueError("expected complete triple records")
    grouped = {name: [row for row in records if row["variant"] == name] for name in VARIANTS}
    expected_n = len(records) // len(VARIANTS)
    if any(len(grouped[name]) != expected_n for name in VARIANTS):
        raise ValueError("variant counts differ")
    ids = [row["id"] for row in grouped["base"]]
    if any([row["id"] for row in grouped[name]] != ids for name in VARIANTS[1:]):
        raise ValueError("unpaired records")
    out_metrics = {name: metrics(grouped[name]) for name in VARIANTS}
    by_variant = {
        name: {row["id"]: bool(row["correct"]) for row in grouped[name]}
        for name in VARIANTS
    }
    fixed_vs_003 = sum(
        not by_variant["sft003"][task_id] and by_variant["sft004"][task_id]
        for task_id in ids
    )
    broke_vs_003 = sum(
        by_variant["sft003"][task_id] and not by_variant["sft004"][task_id]
        for task_id in ids
    )
    fixed_vs_base = sum(
        not by_variant["base"][task_id] and by_variant["sft004"][task_id]
        for task_id in ids
    )
    broke_vs_base = sum(
        by_variant["base"][task_id] and not by_variant["sft004"][task_id]
        for task_id in ids
    )
    return {
        "status": "completed_exploratory",
        "official_benchmark": False,
        "validation_examples": expected_n,
        "samples_per_question": 1,
        "base": out_metrics["base"],
        "sft003": out_metrics["sft003"],
        "sft004": out_metrics["sft004"],
        "correctness_delta_sft004_minus_base":
            out_metrics["sft004"]["correct"] - out_metrics["base"]["correct"],
        "correctness_delta_sft004_minus_sft003":
            out_metrics["sft004"]["correct"] - out_metrics["sft003"]["correct"],
        "tokens_delta_sft004_minus_base":
            out_metrics["sft004"]["total_tokens"] - out_metrics["base"]["total_tokens"],
        "tokens_delta_sft004_minus_sft003":
            out_metrics["sft004"]["total_tokens"] - out_metrics["sft003"]["total_tokens"],
        "sft004_fixed_vs_base": fixed_vs_base,
        "sft004_broke_vs_base": broke_vs_base,
        "sft004_fixed_vs_sft003": fixed_vs_003,
        "sft004_broke_vs_sft003": broke_vs_003,
        "quality_preservation_demonstrated": False,
        "generalization_demonstrated": False,
    }


def validation_fingerprint(validation: list[dict]) -> str:
    ids = "\n".join(row["question_id"] for row in validation)
    return hashlib.sha256(ids.encode()).hexdigest()


def load_partial(path: Path, allowed_ids: set[str]) -> dict[tuple[str, str], dict]:
    if not path.is_file():
        return {}
    result = {}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row.get("id"), row.get("variant"))
            if key[0] not in allowed_ids or key[1] not in VARIANTS:
                raise ValueError(f"partial row {line_number} does not match current validation")
            if key in result:
                raise ValueError(f"duplicate partial row: {key}")
            result[key] = row
    return result


def adapter_ok(path: Path) -> bool:
    return (path / "adapter_config.json").is_file() and bool(list(path.glob("*.safetensors")))


def run(args, validation: list[dict], out: Path, plan: dict) -> dict:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA needed")
    for adapter in (args.sft003, args.sft004):
        if not adapter_ok(adapter):
            raise FileNotFoundError("missing adapter config or safetensors: " + str(adapter))

    if out.exists() and not args.resume:
        raise FileExistsError("output already exists; use --resume explicitly")
    if args.resume and not out.is_dir():
        raise FileNotFoundError("resume requested but output directory does not exist")

    if not out.exists():
        out.mkdir(parents=True, exist_ok=False)
        (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    else:
        saved = json.loads((out / "plan.json").read_text(encoding="utf-8"))
        keys = (
            "validation_fingerprint",
            "n",
            "seed",
            "cap",
            "sft003_adapter",
            "sft004_adapter",
            "model_revision",
        )
        if any(saved.get(key) != plan.get(key) for key in keys):
            raise ValueError("resume plan differs from original run")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True
    )
    opening = tokenizer.convert_tokens_to_ids("<think>")
    closing = tokenizer.convert_tokens_to_ids("</think>")
    eos_base = {int(tokenizer.eos_token_id)}
    allowed_ids = {row["question_id"] for row in validation}
    journal = out / "records.partial.jsonl"
    results = load_partial(journal, allowed_ids)

    phase_adapters = (
        ("base", None),
        ("sft003", args.sft003),
        ("sft004", args.sft004),
    )
    for name, adapter in phase_adapters:
        pending = [row for row in validation if (row["question_id"], name) not in results]
        if not pending:
            print(f"{name}: already complete, skipping", flush=True)
            continue
        backbone = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            revision=BASE_REVISION,
            local_files_only=True,
            dtype=torch.float16,
        ).to("cuda").eval()
        eos_this = set(eos_base)
        ceos = backbone.generation_config.eos_token_id
        if isinstance(ceos, int):
            eos_this.add(ceos)
        elif isinstance(ceos, (tuple, list)):
            eos_this.update(int(value) for value in ceos)
        active = backbone
        if adapter is not None:
            active = PeftModel.from_pretrained(
                backbone, str(adapter), is_trainable=False
            ).eval()
            if len(active.peft_config) != 1:
                raise RuntimeError("adapter isolation failed: expected one adapter only")

        for row in pending:
            i = next(index for index, item in enumerate(validation) if item["question_id"] == row["question_id"])
            inputs = tokenizer.apply_chat_template(
                row["prompt"],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=True,
                return_tensors="pt",
                return_dict=True,
            ).to("cuda")
            tail = tokenizer.decode(
                inputs["input_ids"][0][-32:].tolist(), skip_special_tokens=False
            )
            prefilled = "<think>" in tail and "</think>" not in tail
            torch.manual_seed(args.seed)
            torch.cuda.manual_seed_all(args.seed)
            with torch.inference_mode():
                output = active.generate(
                    **inputs,
                    do_sample=True,
                    max_new_tokens=args.cap,
                    **SAMPLING,
                )
            ids = output[0, inputs["input_ids"].shape[1]:].tolist()
            split = split_reasoning(ids, opening, closing, eos_this, prefilled)
            truncated = not ids or ids[-1] not in eos_this
            final = tokenizer.decode(split["final_ids"], skip_special_tokens=True)
            correct, error = (
                (False, "truncated")
                if truncated
                else grade_final(final, row["gold_answer"], "number")
            )
            record = {
                "variant": name,
                "id": row["question_id"],
                "seed": args.seed,
                "gold": row["gold_answer"],
                "tokens": len(ids),
                "reasoning_tokens": split["reasoning_tokens"],
                "final_tokens": split["final_tokens"],
                "truncated": truncated,
                "correct": correct,
                "error": error,
                "final_text": final,
                "generated_text": tokenizer.decode(ids, skip_special_tokens=False),
            }
            results[(row["question_id"], name)] = record
            with journal.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
            print(
                f"{name} {i + 1}/{len(validation)} correct={correct} tokens={len(ids)}",
                flush=True,
            )

        if active is not backbone:
            del active
        del backbone
        gc.collect()
        torch.cuda.empty_cache()

    records = [
        results[(row["question_id"], name)]
        for row in validation
        for name in VARIANTS
    ]
    summary = summarize(records)
    with (out / "records.jsonl").open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--raw-parquet",
        type=Path,
        default=Path("data/safe-start/raw/gsm8k-train.parquet"),
    )
    p.add_argument(
        "--eval-questions",
        type=Path,
        default=Path("questions/questions.jsonl"),
    )
    p.add_argument(
        "--intake",
        type=Path,
        default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"),
    )
    p.add_argument(
        "--holdout",
        type=Path,
        default=Path("runs/cep002-data-intake-001/holdout-reservation.jsonl"),
    )
    p.add_argument(
        "--safe-start-questions",
        type=Path,
        default=Path("data/safe-start/questions.jsonl"),
    )
    p.add_argument("--history-root", type=Path, default=Path("runs"))
    p.add_argument("--sft003", type=Path, default=Path("runs/rhar-training-003"))
    p.add_argument(
        "--sft004",
        type=Path,
        default=Path("runs/rhar-training-004-long-sft"),
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--count", type=int, default=DEFAULT_COUNT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--cap", type=int, default=512)
    p.add_argument("--resume", action="store_true")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    p.add_argument("--approve-gpu", action="store_true")
    args = p.parse_args(argv)

    if args.execute != args.approve_gpu:
        p.error("use --execute --approve-gpu, or --dry-run without approval")
    if args.dry_run and args.resume:
        p.error("--resume is only valid with execution")
    if not 128 <= args.cap <= 2048:
        p.error("cap must be between 128 and 2048")
    if not args.raw_parquet.is_file():
        raise FileNotFoundError("verified pinned train parquet required")
    if hashlib.sha256(args.raw_parquet.read_bytes()).hexdigest() != TRAIN_SHA256:
        raise ValueError("GSM8K training file SHA mismatch")
    if not args.eval_questions.is_file():
        raise FileNotFoundError("evaluation prompts required for screening")

    raw = read_parquet(args.raw_parquet)
    protected, protection = build_protected_ids(
        raw,
        args.intake,
        args.holdout,
        args.safe_start_questions,
        args.history_root,
    )
    validation, fresh = select_fresh_validation(raw, protected, args.count)
    eval_prompts = read_eval_prompts(args.eval_questions)
    reject_overlap([], validation, eval_prompts)
    fingerprint = validation_fingerprint(validation)

    plan = {
        "status": "plan_only" if args.dry_run else "running",
        "experiment": "RHAR Validation 007 BASE vs SFT003 vs SFT004",
        "official_benchmark": False,
        "train_source": "GSM8K/main/train",
        "model": BASE_MODEL,
        "model_revision": BASE_REVISION,
        "n": len(validation),
        "planned_generations": len(validation) * len(VARIANTS),
        "seed": args.seed,
        "cap": args.cap,
        "sampling": SAMPLING,
        "sft003_adapter": str(args.sft003),
        "sft004_adapter": str(args.sft004),
        "validation_fingerprint": fingerprint,
        "screened_eval_prompts": len(eval_prompts),
        "heuristic_eval_overlap_screen_only": True,
        "training004_train_and_loss_validation_excluded": True,
        "cep002_reserved_holdout_excluded": True,
        "validation_used_for_loss_in_training004": False,
        "gpu_used": False,
        "training_performed": False,
        **protection,
        **fresh,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    run(args, validation, args.out, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
