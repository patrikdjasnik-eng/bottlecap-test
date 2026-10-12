"""RHAR Training 004: wall-clock bounded long SFT control.

Build a stronger Qwen3-0.6B LoRA baseline from pinned GSM8K main/train while
excluding all known historical/review/holdout exposure. CPU dry-run is the
default validation path; CUDA training requires explicit --approve-training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from pathlib import Path

from .cep002_history_overlap import QUESTION_ID_RE, extract_references, load_jsonl
from .rhar_train_003 import prepare_pool, reject_overlap
from .rhar_teacher_train_002 import encode_teacher
from .reasoning_probe import BASE_MODEL, BASE_REVISION
from .safe_start_data import (
    DATASET_REVISION,
    TRAIN_SHA256,
    normalize_question,
    parse_gold,
    read_eval_prompts,
    read_parquet,
)
from .safe_start_plan import build_prompt

HISTORICAL_TRAIN = 1000
HISTORICAL_LOSS_VALIDATION = 100
HISTORICAL_PAIRED_EVALUATION = 80
HISTORICAL_SEED = 42
CEP002_REVIEW_COUNT = 12
CEP002_HOLDOUT_COUNT = 60
SAFE_START_COUNT = 12


def load_manifest_ids(path: Path, expected_count: int, label: str) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} manifest missing: {path}")
    rows = load_jsonl(path)
    ids = []
    for row in rows:
        task_id = row.get("question_id")
        if not isinstance(task_id, str) or not QUESTION_ID_RE.fullmatch(task_id):
            raise ValueError(f"{label} has invalid question_id")
        ids.append(task_id)
    if len(ids) != expected_count or len(set(ids)) != expected_count:
        raise ValueError(f"{label} must contain exactly {expected_count} unique GSM8K IDs")
    return set(ids)


def historical_partition_ids(source_rows: list[dict]) -> set[str]:
    old_train, old_tail = prepare_pool(
        source_rows,
        HISTORICAL_TRAIN,
        HISTORICAL_LOSS_VALIDATION + HISTORICAL_PAIRED_EVALUATION,
        HISTORICAL_SEED,
    )
    return {row["question_id"] for row in old_train + old_tail}


def historical_run_gsm8k_ids(history_root: Path) -> set[str]:
    if not history_root.is_dir():
        raise FileNotFoundError(f"history root missing: {history_root}")
    result: set[str] = set()
    for path in sorted(history_root.glob("**/records.jsonl")):
        for row in load_jsonl(path):
            ids, _, _ = extract_references(row)
            result.update(task_id for task_id in ids if QUESTION_ID_RE.fullmatch(task_id))
    return result


def teacher_rows(source_rows: list[dict]) -> list[dict]:
    rows = []
    used = set()
    for idx, source in enumerate(source_rows):
        question = source.get("question")
        if not isinstance(question, str) or not question.strip():
            continue
        if "final answer:" in question.casefold():
            continue
        try:
            gold = parse_gold(source.get("answer"))
        except ValueError:
            continue
        rationale = source["answer"].split("####", 1)[0].strip()
        rationale = re.sub(r"<<[^<>\n]*>>", "", rationale).strip()
        if not rationale or "<think>" in rationale or "</think>" in rationale:
            continue
        normalized = normalize_question(question)
        if normalized in used:
            continue
        used.add(normalized)
        rows.append({
            "question_id": f"gsm8k-train-{idx:05d}",
            "question": question.strip(),
            "gold_answer": gold,
            "prompt": [{"role": "user", "content": build_prompt(question)}],
            "completion": "<think>\n" + rationale + "\n</think>\nFinal answer: " + gold,
        })
    return rows


def prepare_long_pool(
    source_rows: list[dict],
    protected_ids: set[str],
    n_train: int,
    n_val: int,
    seed: int,
) -> tuple[list[dict], list[dict], int]:
    if n_train < 8 or n_val < 8:
        raise ValueError("train and validation sizes must both be >= 8")
    rows = teacher_rows(source_rows)
    known_ids = {row["question_id"] for row in rows}
    missing = protected_ids - known_ids
    if missing:
        raise ValueError(f"protected GSM8K IDs are absent from pinned source: {len(missing)}")
    available = [row for row in rows if row["question_id"] not in protected_ids]
    rng = random.Random(seed)
    rng.shuffle(available)
    if len(available) < n_train + n_val:
        raise ValueError("insufficient clean examples after protected-ID exclusions")
    train = available[:n_train]
    validation = available[n_train:n_train + n_val]
    if ({row["question_id"] for row in train} & protected_ids
            or {row["question_id"] for row in validation} & protected_ids):
        raise RuntimeError("protected ID escaped exclusion")
    if {row["question_id"] for row in train} & {row["question_id"] for row in validation}:
        raise RuntimeError("train/validation overlap")
    return train, validation, len(available)


def deadline_reached(start_monotonic: float, max_minutes: float, now_monotonic: float) -> bool:
    if max_minutes <= 0:
        raise ValueError("max_minutes must be positive")
    return now_monotonic - start_monotonic >= max_minutes * 60.0


def build_protected_ids(
    source_rows: list[dict],
    intake: Path,
    holdout: Path,
    safe_start_questions: Path,
    history_root: Path,
) -> tuple[set[str], dict]:
    historic_partition = historical_partition_ids(source_rows)
    review_ids = load_manifest_ids(intake, CEP002_REVIEW_COUNT, "CEP002 review")
    holdout_ids = load_manifest_ids(holdout, CEP002_HOLDOUT_COUNT, "CEP002 holdout")
    safe_start_ids = load_manifest_ids(safe_start_questions, SAFE_START_COUNT, "Safe Start")
    run_ids = historical_run_gsm8k_ids(history_root)
    protected = historic_partition | review_ids | holdout_ids | safe_start_ids | run_ids
    return protected, {
        "historical_partition_ids": len(historic_partition),
        "cep002_review_ids": len(review_ids),
        "cep002_holdout_ids": len(holdout_ids),
        "safe_start_review_ids": len(safe_start_ids),
        "historical_run_gsm8k_ids": len(run_ids),
        "protected_unique_ids": len(protected),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet", type=Path,
                   default=Path("data/safe-start/raw/gsm8k-train.parquet"))
    p.add_argument("--eval-questions", type=Path,
                   default=Path("questions/questions.jsonl"))
    p.add_argument("--intake", type=Path,
                   default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    p.add_argument("--holdout", type=Path,
                   default=Path("runs/cep002-data-intake-001/holdout-reservation.jsonl"))
    p.add_argument("--safe-start-questions", type=Path,
                   default=Path("data/safe-start/questions.jsonl"))
    p.add_argument("--history-root", type=Path, default=Path("runs"))
    p.add_argument("--train-size", type=int, default=2500)
    p.add_argument("--val-size", type=int, default=100)
    p.add_argument("--seed", type=int, default=404)
    p.add_argument("--max-length", type=int, default=1024)
    p.add_argument("--epochs", type=float, default=3.0)
    p.add_argument("--max-minutes", type=float, default=120.0)
    p.add_argument("--checkpoint-steps", type=int, default=50)
    p.add_argument("--eval-steps", type=int, default=50)
    p.add_argument("--learning-rate", type=float, default=5e-5)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--resume", action="store_true")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--approve-training", action="store_true")
    args = p.parse_args(argv)

    if args.max_length < 256 or not 0 < args.epochs <= 5:
        p.error("invalid sequence length or epochs")
    if args.max_minutes < 5 or args.max_minutes > 240:
        p.error("max-minutes must be between 5 and 240")
    if args.checkpoint_steps < 1 or args.eval_steps < 1:
        p.error("checkpoint/eval steps must be positive")
    if args.learning_rate <= 0 or args.learning_rate > 1e-3:
        p.error("learning rate outside safe bound")
    if not args.raw_parquet.is_file():
        raise FileNotFoundError("local GSM8K train parquet missing")
    if hashlib.sha256(args.raw_parquet.read_bytes()).hexdigest() != TRAIN_SHA256:
        raise ValueError("GSM8K training file SHA mismatch")
    if not args.eval_questions.is_file():
        raise FileNotFoundError("local evaluation prompts needed for overlap screen")

    raw = read_parquet(args.raw_parquet)
    protected, protection = build_protected_ids(
        raw, args.intake, args.holdout, args.safe_start_questions, args.history_root
    )
    train, validation, clean_available = prepare_long_pool(
        raw, protected, args.train_size, args.val_size, args.seed
    )
    eval_prompts = read_eval_prompts(args.eval_questions)
    reject_overlap(train, validation, eval_prompts)

    plan = {
        "status": "plan_only" if args.dry_run else "training",
        "experiment": "RHAR Training 004 long SFT control",
        "model": BASE_MODEL,
        "revision": BASE_REVISION,
        "source": "gsm8k/main/train",
        "source_revision": DATASET_REVISION,
        "source_sha256": TRAIN_SHA256,
        "train_count": len(train),
        "validation_count": len(validation),
        "clean_examples_available": clean_available,
        "seed": args.seed,
        "epochs_ceiling": args.epochs,
        "max_length": args.max_length,
        "max_minutes": args.max_minutes,
        "checkpoint_steps": args.checkpoint_steps,
        "eval_steps": args.eval_steps,
        "learning_rate": args.learning_rate,
        "screened_eval_prompts": len(eval_prompts),
        "heuristic_eval_overlap_screen_only": True,
        "resume_requested": args.resume,
        **protection,
        "protected_ids_verified_excluded": True,
        "gpu_used": False,
        "training_performed": False,
        "official_benchmark": False,
        "cep002_training": False,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainerCallback,
        TrainingArguments,
    )
    from transformers.trainer_utils import get_last_checkpoint

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    resume_checkpoint = None
    if args.out.exists():
        if not args.resume:
            raise FileExistsError("output exists; use --resume explicitly")
        resume_checkpoint = get_last_checkpoint(str(args.out))
        if resume_checkpoint is None:
            raise FileNotFoundError("resume requested but no Trainer checkpoint found")
    elif args.resume:
        raise FileNotFoundError("resume requested but output directory does not exist")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True
    )
    encoded_train = [encode_teacher(row, tokenizer, args.max_length) for row in train]
    encoded_val = [encode_teacher(row, tokenizer, args.max_length) for row in validation]
    train_usable = [row for row in encoded_train if row is not None]
    val_usable = [row for row in encoded_val if row is not None]
    if len(train_usable) < max(8, int(args.train_size * 0.8)):
        raise ValueError("too many training examples exceed max-length")
    if len(val_usable) < max(8, int(args.val_size * 0.8)):
        raise ValueError("too many validation examples exceed max-length")

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        revision=BASE_REVISION,
        local_files_only=True,
        dtype=torch.float16,
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj"],
    ))

    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

    def collate(batch):
        width = max(len(row["input_ids"]) for row in batch)
        result = {}
        for key in ("input_ids", "attention_mask", "labels"):
            fill = -100 if key == "labels" else 0 if key == "attention_mask" else pad
            result[key] = torch.tensor([
                row[key] + [fill] * (width - len(row[key])) for row in batch
            ])
        return result

    started = time.monotonic()

    class WallClockStop(TrainerCallback):
        def on_step_end(self, training_args, state, control, **kwargs):
            if deadline_reached(started, args.max_minutes, time.monotonic()):
                control.should_training_stop = True
                control.should_save = True
            return control

    training_args = TrainingArguments(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        fp16=True,
        bf16=False,
        logging_steps=10,
        save_strategy="steps",
        save_steps=args.checkpoint_steps,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_total_limit=4,
        report_to="none",
        remove_unused_columns=False,
        seed=args.seed,
        data_seed=args.seed,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_usable,
        eval_dataset=val_usable,
        data_collator=collate,
        callbacks=[WallClockStop()],
    )
    result = trainer.train(resume_from_checkpoint=resume_checkpoint)
    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out, safe_serialization=True)
    tokenizer.save_pretrained(args.out)
    metrics = trainer.evaluate()
    elapsed_seconds = time.monotonic() - started
    metadata = {
        **plan,
        "status": "completed",
        "training_performed": True,
        "gpu_used": True,
        "train_usable": len(train_usable),
        "validation_usable": len(val_usable),
        "train_loss": result.training_loss,
        "evaluation_metrics": metrics,
        "elapsed_seconds": elapsed_seconds,
        "global_step": trainer.state.global_step,
        "resume_from_checkpoint": resume_checkpoint,
        "training_method": "LoRA SFT control on pinned GSM8K reference rationales",
        "official_benchmark": False,
        "cep002_training": False,
    }
    (args.out / "training_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print("RHAR Training 004 adapter:", args.out)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
