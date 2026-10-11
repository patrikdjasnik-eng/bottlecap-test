"""CEP-002: review-only GSM8K intake with explicit historical split boundaries.

Only the pinned GSM8K main/train data may be read. Never train, run CUDA,
emit official evaluation questions, or claim unseen benchmark accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .rhar_train_003 import prepare_pool, reject_overlap
from .safe_start_data import (
    DATASET_REVISION, TRAIN_SHA256, read_eval_prompts, read_parquet, sha256_file,
)

PRIOR_TRAIN = 1000
PRIOR_LOSS_VALIDATION = 100
PRIOR_PAIRED_EVALUATION = 20 + 60
SEED = 42
REVIEW_COUNT = 12
RESERVED_HOLDOUT = 60


def select_review_partition(
    rows: list[dict],
    train_size: int = PRIOR_TRAIN,
    validation_size: int = PRIOR_LOSS_VALIDATION,
    prior_evaluation_size: int = PRIOR_PAIRED_EVALUATION,
    review_size: int = REVIEW_COUNT,
    reserve_size: int = RESERVED_HOLDOUT,
    seed: int = SEED,
) -> tuple[list[dict], list[dict], set[str]]:
    if min(train_size, validation_size, review_size, reserve_size) < 1:
        raise ValueError("partition sizes must be positive")
    if prior_evaluation_size < 0:
        raise ValueError("historical evaluation count must not be negative")
    total_val = validation_size + prior_evaluation_size + review_size + reserve_size
    earlier_train, tail = prepare_pool(rows, train_size, total_val, seed)
    offset = validation_size + prior_evaluation_size
    earlier_ids = {r["question_id"] for r in earlier_train + tail[:offset]}
    review = tail[offset:offset + review_size]
    reserve = tail[offset + review_size:offset + review_size + reserve_size]
    review_ids = {r["question_id"] for r in review}
    reserve_ids = {r["question_id"] for r in reserve}
    if (len(review_ids) != review_size or len(reserve_ids) != reserve_size
            or (earlier_ids & review_ids) or (earlier_ids & reserve_ids)
            or (review_ids & reserve_ids)):
        raise ValueError("historical / review / holdout partitions are not disjoint")
    return review, reserve, earlier_ids


def intake(
    raw_parquet: Path,
    eval_questions: Path,
    out_dir: Path,
    execute: bool = False,
) -> dict:
    if out_dir.exists() and execute:
        raise FileExistsError(f"refusing to overwrite {out_dir}")
    if not raw_parquet.is_file() or sha256_file(raw_parquet) != TRAIN_SHA256:
        raise ValueError("pinned GSM8K main/train parquet is missing or SHA-256 differs")
    if not eval_questions.is_file():
        raise FileNotFoundError("official evaluation prompts required for overlap audit")
    official_prompts = read_eval_prompts(eval_questions)
    rows = read_parquet(raw_parquet)
    review, reserve, historical_ids = select_review_partition(rows)
    reject_overlap(review, reserve, official_prompts)

    candidates = [
        {
            "question_id": record["question_id"],
            "question": record["question"],
            "gold_answer": record["gold_answer"],
            "source": "gsm8k/main/train",
            "dataset_revision": DATASET_REVISION,
            "question_sha256": hashlib.sha256(record["question"].encode()).hexdigest(),
            "status": "REVIEW_REQUIRED",
            "contract": None,
            "approved_for_training": False,
        }
        for record in review
    ]
    holdout_manifest = [
        {
            "question_id": record["question_id"],
            "question_sha256": hashlib.sha256(record["question"].encode()).hexdigest(),
        }
        for record in reserve
    ]
    report = {
        "status": "review_only_not_training_eligible" if execute else "plan_only",
        "candidate_count": len(candidates),
        "reserved_holdout_count": len(holdout_manifest),
        "historical_earlier_count": len(historical_ids),
        "seed": SEED,
        "excluded_prior_train_count": PRIOR_TRAIN,
        "excluded_prior_loss_validation_count": PRIOR_LOSS_VALIDATION,
        "excluded_prior_paired_evaluation_count": PRIOR_PAIRED_EVALUATION,
        "dataset": "openai/gsm8k/main/train",
        "dataset_revision": DATASET_REVISION,
        "dataset_sha256": TRAIN_SHA256,
        "local_official_eval_prompts_screened": len(official_prompts),
        "exact_historical_partition_excluded": True,
        "prior_other_pilots_and_review_sets_fully_audited": False,
        "near_duplicate_screen_exhaustive": False,
        "independent_semantic_contract_review_completed": False,
        "candidate_contracts_verified": 0,
        "gpu_used": False,
        "training_performed": False,
        "training_approved": False,
        "official_benchmark": False,
    }
    if execute:
        out_dir.mkdir(parents=True, exist_ok=False)
        with (out_dir / "candidates-review.jsonl").open("x", encoding="utf-8") as stream:
            for candidate in candidates:
                stream.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        with (out_dir / "holdout-reservation.jsonl").open("x", encoding="utf-8") as stream:
            for candidate in holdout_manifest:
                stream.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        with (out_dir / "summary.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-parquet", type=Path, required=True)
    parser.add_argument("--eval-questions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    result = intake(args.raw_parquet, args.eval_questions, args.out, args.execute)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
