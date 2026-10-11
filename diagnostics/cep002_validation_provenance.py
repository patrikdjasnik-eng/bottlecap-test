"""CPU-only: validate provenance of 005/006 paired evaluation IDs against GSM8K train.

No inference, training, reserved holdout question lookup, or evaluation prompt
export. Does not treat all remaining older ID-only records as verified.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .cep002_history_overlap import (
    REQUIRED_RUNS, extract_references, load_jsonl, load_targets, scan, QUESTION_ID_RE
)
from .rhar_train_003 import prepare_pool
from .safe_start_data import TRAIN_SHA256, DATASET_REVISION, read_parquet, sha256_file

SEED = 42
HISTORIC_TRAIN = 1000
HISTORIC_LOSS_VALIDATION = 100
VALIDATION_005_COUNT = 20
VALIDATION_006_COUNT = 60


def validate_paired_records(records: list[dict], expected_rows: list[dict]) -> dict:
    """Require exactly one SFT and one CEP record per deterministic source ID."""
    expected = {row["question_id"]: row["gold_answer"] for row in expected_rows}
    if len(expected) != len(expected_rows):
        raise ValueError("duplicate expected source IDs")
    if len(records) != 2 * len(expected):
        raise ValueError("wrong number of historical paired records")
    pairs = set()
    for row in records:
        task_id = row.get("id")
        variant = row.get("variant")
        if task_id not in expected or variant not in ("sft", "cep"):
            raise ValueError("unexpected ID or model variant in historical validation")
        if row.get("gold") != expected[task_id]:
            raise ValueError("source gold differs from previous validation record")
        pair = (task_id, variant)
        if pair in pairs:
            raise ValueError("duplicate historical validation pair")
        pairs.add(pair)
    if pairs != {(task_id, variant) for task_id in expected for variant in ("sft", "cep")}:
        raise ValueError("historical model pairs are incomplete")
    return {
        "source_identity_verified": True,
        "paired_record_count": len(records),
        "unique_question_ids": len(expected),
        "paired_variants": ["cep", "sft"],
    }


def classify_other_id_only(history_root: Path) -> tuple[dict, list[dict]]:
    """Count nonvalidation ID-only records, never print unknown raw IDs."""
    other = {
        "id_only_records": 0,
        "with_gsm8k_train_id": 0,
        "with_other_ids_only": 0,
        "with_hash_only": 0,
        "with_multiple_or_ambiguous_refs": 0,
        "opaque_records": 0,
        "records_with_question_text": 0,
    }
    per_file = []
    known_files = set(REQUIRED_RUNS)
    for path in sorted(history_root.glob("**/records.jsonl")):
        rel = path.relative_to(history_root).as_posix()
        if rel in known_files:
            continue
        counts = Counter()
        for row in load_jsonl(path):
            ids, hashes, strings = extract_references(row)
            if strings:
                counts["records_with_question_text"] += 1
            elif ids or hashes:
                counts["id_only_records"] += 1
                if any(QUESTION_ID_RE.fullmatch(task_id) for task_id in ids):
                    counts["with_gsm8k_train_id"] += 1
                elif ids:
                    counts["with_other_ids_only"] += 1
                else:
                    counts["with_hash_only"] += 1
                if len(ids) + len(hashes) > 1:
                    counts["with_multiple_or_ambiguous_refs"] += 1
            else:
                counts["opaque_records"] += 1
        for k in other:
            other[k] += counts[k]
        per_file.append({"file": "runs/" + rel, **{key: counts[key] for key in other}})
    return other, per_file


def provenance(
    raw_parquet: Path,
    intake_path: Path,
    reservations_path: Path,
    safe_start_path: Path,
    history_root: Path,
    out: Path,
    execute: bool,
) -> dict:
    if execute and out.exists():
        raise FileExistsError("refusing to overwrite existing provenance report")
    if not raw_parquet.is_file() or sha256_file(raw_parquet) != TRAIN_SHA256:
        raise ValueError("pinned GSM8K main/train source missing or invalid")
    targets = load_targets(intake_path, reservations_path)
    matches, history_stats = scan(targets, safe_start_path, history_root)
    if matches:
        raise ValueError("historical overlap detected; manual investigation required")
    rows = read_parquet(raw_parquet)
    _, historical_validation = prepare_pool(
        rows, HISTORIC_TRAIN,
        HISTORIC_LOSS_VALIDATION + VALIDATION_005_COUNT + VALIDATION_006_COUNT,
        SEED,
    )
    five = historical_validation[HISTORIC_LOSS_VALIDATION:
                                  HISTORIC_LOSS_VALIDATION + VALIDATION_005_COUNT]
    six = historical_validation[HISTORIC_LOSS_VALIDATION + VALIDATION_005_COUNT:]
    known_ids = {row["question_id"] for row in five + six}
    if known_ids & set(targets):
        raise ValueError("reconstructed prior validation IDs overlap new candidates or holdout")
    checks = {}
    for path, expected in ((REQUIRED_RUNS[0], five), (REQUIRED_RUNS[1], six)):
        checks[path] = validate_paired_records(load_jsonl(history_root / path), expected)
    other, per_file = classify_other_id_only(history_root)
    accounted = sum(item["paired_record_count"] for item in checks.values())
    remaining = other["id_only_records"]
    if accounted + remaining != history_stats["id_or_hash_only_rows"]:
        raise ValueError("historical coverage counts disagree; possible missing file or shape")
    summary = {
        "status": "known_validation_ids_verified_remaining_history_partial",
        "mode": "execute" if execute else "dry_run",
        "dataset": "openai/gsm8k/main/train",
        "dataset_revision": DATASET_REVISION,
        "dataset_sha256": TRAIN_SHA256,
        "split_seed": SEED,
        "reconstructed_historical_train_size": HISTORIC_TRAIN,
        "reconstructed_loss_validation_size": HISTORIC_LOSS_VALIDATION,
        "validation_checks": checks,
        "prior_validation_rows_with_confirmed_dataset_identity": accounted,
        "prior_validation_distinct_questions": len(known_ids),
        "remaining_other_runs_id_only_rows": remaining,
        "other_runs_breakdown": other,
        "historical_source_files": history_stats["historical_source_files"],
        "historical_rows": history_stats["historical_rows"],
        "review_candidates_and_holdout_id_hash_overlap_count": 0,
        "remaining_provenance_needs_review": remaining > 0,
        "historical_screen_exhaustive": False,
        "semantic_duplicate_check_exhaustive": False,
        "independent_semantic_review_completed": False,
        "official_benchmark": False,
        "holdout_question_texts_loaded_or_exported": False,
        "training_approved": False,
        "training_performed": False,
        "gpu_used": False,
    }
    if execute:
        out.mkdir(parents=True, exist_ok=False)
        with (out / "summary.json").open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        with (out / "other-file-coverage.json").open("x", encoding="utf-8") as stream:
            json.dump(per_file, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-parquet", type=Path, required=True)
    parser.add_argument("--intake", type=Path,
                        default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    parser.add_argument("--reservations", type=Path,
                        default=Path("runs/cep002-data-intake-001/holdout-reservation.jsonl"))
    parser.add_argument("--safe-start", type=Path, required=True)
    parser.add_argument("--history-root", type=Path, required=True)
    parser.add_argument("--out", type=Path,
                        default=Path("runs/cep002-validation-provenance-001"))
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    summary = provenance(
        args.raw_parquet, args.intake, args.reservations,
        args.safe_start, args.history_root, args.out, args.execute,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
