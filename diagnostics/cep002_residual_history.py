"""CEP-002: triage residual historical record IDs, without GPU/training.

Read only prior runs after excluding paired validations 005/006. Resolve strict
GSM8K-train-NNNNN IDs to the pinned main/train source and classify other
identifiers as unknown-source. This is a partial screen, not a license to train.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .cep002_history_overlap import (
    REQUIRED_RUNS, QUESTION_ID_RE, extract_references, load_jsonl, load_targets,
)
from .rhar_train_003 import prepare_pool
from .safe_start_data import TRAIN_SHA256, read_parquet, sha256_file, parse_gold

PINNED_SEED = 42
TRAIN = 1000
LOSS_VAL = 100
PAIRED = 80


def inspect_remaining(
    dataset_rows: list[dict],
    history_root: Path,
    candidates: dict,
) -> tuple[dict, list[dict]]:
    train, rest = prepare_pool(dataset_rows, TRAIN, LOSS_VAL + PAIRED, PINNED_SEED)
    historic_train = {row["question_id"] for row in train}
    historic_loss = {row["question_id"] for row in rest[:LOSS_VAL]}
    historic_eval = {row["question_id"] for row in rest[LOSS_VAL:]}

    counts = Counter()
    per_file = []
    for path in sorted(history_root.glob("**/records.jsonl")):
        rel = path.relative_to(history_root).as_posix()
        if rel in REQUIRED_RUNS:
            continue
        current = Counter()
        for row in load_jsonl(path):
            ids, hashes, texts = extract_references(row)
            if texts:
                current["with_original_question_text"] += 1
                continue
            if not ids and not hashes:
                raise ValueError(f"historical row without reference: {rel}")
            if len(ids) != 1 or hashes:
                # Uncertainty must not be disguised as a resolvable source.
                current["ambiguous_id_or_hash_only"] += 1
                continue

            task_id = next(iter(ids))
            if QUESTION_ID_RE.fullmatch(task_id):
                current["gsm8k_format_id"] += 1
                if task_id in candidates:
                    raise ValueError("historical ID overlaps reserved or reviewed CEP-002 data")
                raw_index = int(task_id.rsplit("-", 1)[1])
                if raw_index >= len(dataset_rows) or raw_index < 0:
                    current["unresolvable_gsm8k_source_id"] += 1
                    continue
                dataset_question = dataset_rows[raw_index].get("question")
                if not isinstance(dataset_question, str) or not dataset_question.strip():
                    current["unresolvable_gsm8k_source_id"] += 1
                    continue

                if task_id in historic_train:
                    current["within_old_training"] += 1
                elif task_id in historic_loss:
                    current["within_old_loss_validation"] += 1
                elif task_id in historic_eval:
                    current["within_old_paired_evaluation"] += 1
                else:
                    current["outside_known_1180"] += 1

                if "gold" in row:
                    try:
                        expected = parse_gold(dataset_rows[raw_index]["answer"])
                        if not isinstance(row["gold"], str) or row["gold"] != expected:
                            current["gold_mismatch_or_unknown"] += 1
                        else:
                            current["gold_confirmed"] += 1
                    except (KeyError, ValueError, TypeError):
                        current["gold_mismatch_or_unknown"] += 1
                else:
                    current["gold_not_recorded"] += 1
            else:
                current["non_gsm8k_format_id"] += 1
        counts.update(current)
        per_file.append({"file": "runs/" + rel, **{
            key: current[key] for key in (
                "gsm8k_format_id", "within_old_training", "within_old_loss_validation",
                "within_old_paired_evaluation", "outside_known_1180",
                "unresolvable_gsm8k_source_id", "gold_confirmed",
                "gold_not_recorded", "gold_mismatch_or_unknown",
                "non_gsm8k_format_id", "ambiguous_id_or_hash_only",
                "with_original_question_text",
            )
        }})
    return dict(counts), per_file


def main_audit(raw: Path, intake: Path, reservations: Path,
               history_root: Path, out: Path, execute: bool) -> dict:
    if execute and out.exists():
        raise FileExistsError("refusing to overwrite previous gap audit")
    if not raw.is_file() or sha256_file(raw) != TRAIN_SHA256:
        raise ValueError("pinned GSM8K main/train is missing or SHA-256 is wrong")
    if not history_root.is_dir():
        raise FileNotFoundError("historical runs root not found")
    for required in REQUIRED_RUNS:
        if not (history_root / required).is_file():
            raise FileNotFoundError("missing historical validation: " + required)

    target = load_targets(intake, reservations)
    counts, details = inspect_remaining(read_parquet(raw), history_root, target)
    # Every ID-only record outside the fully reconstructed 005/006 validation
    # remains pending provenance review. The earlier formula counted only malformed
    # or conflicting IDs and misleadingly returned zero despite unreviewed rows.
    # These categories are mutually exclusive at the record level, so there is
    # no double-counting of missing gold or unknown partition membership.
    total_pending = (counts.get("gsm8k_format_id", 0)
                     + counts.get("non_gsm8k_format_id", 0)
                     + counts.get("ambiguous_id_or_hash_only", 0))
    categorised = (counts.get("within_old_training", 0)
                   + counts.get("within_old_loss_validation", 0)
                   + counts.get("within_old_paired_evaluation", 0)
                   + counts.get("outside_known_1180", 0)
                   + counts.get("unresolvable_gsm8k_source_id", 0))
    if categorised != counts.get("gsm8k_format_id", 0):
        raise ValueError("historic GSM8K ID categorisation is incomplete")
    summary = {
        "status": "partial_residual_history_classification",
        "mode": "execute" if execute else "dry_run",
        "dataset_sha256": TRAIN_SHA256,
        "historical_gsm8k_id_rows": counts.get("gsm8k_format_id", 0),
        "historical_non_gsm8k_id_rows": counts.get("non_gsm8k_format_id", 0),
        "source_ids_valid_but_outside_known_1180": counts.get("outside_known_1180", 0),
        "known_old_training_ids": counts.get("within_old_training", 0),
        "known_old_loss_validation_ids": counts.get("within_old_loss_validation", 0),
        "known_old_paired_evaluation_ids": counts.get("within_old_paired_evaluation", 0),
        "source_ids_unresolvable": counts.get("unresolvable_gsm8k_source_id", 0),
        "recorded_gold_matched": counts.get("gold_confirmed", 0),
        "recorded_gold_missing": counts.get("gold_not_recorded", 0),
        "recorded_gold_mismatch_or_unknown": counts.get("gold_mismatch_or_unknown", 0),
        "ambiguous_id_or_hash_only_rows": counts.get("ambiguous_id_or_hash_only", 0),
        "rows_with_input_text_excluded_from_id_only_triage": counts.get("with_original_question_text", 0),
        "requires_investigation_count": total_pending,
        "unresolved_provenance_id_only_rows": total_pending,
        "requires_manual_provenance_review": total_pending > 0,
        "numeric_id_resolved_does_not_prove_question_identity": True,
        "non_gsm8k_ids_not_semantically_screened": True,
        "old_histories_exhaustively_proven_clean": False,
        "independent_semantic_review_completed": False,
        "reserved_holdout_questions_selected": False,
        "reserved_holdout_texts_exported": False,
        "training_approved": False,
        "training_performed": False,
        "gpu_used": False,
    }
    if execute:
        out.mkdir(parents=True, exist_ok=False)
        (out / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (out / "coverage.json").write_text(
            json.dumps(details, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet", type=Path, required=True)
    p.add_argument("--history-root", type=Path, required=True)
    p.add_argument("--intake", type=Path, default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    p.add_argument("--reservations", type=Path,
                   default=Path("runs/cep002-data-intake-001/holdout-reservation.jsonl"))
    p.add_argument("--out", type=Path, default=Path("runs/cep002-residual-history-001"))
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    print(json.dumps(main_audit(args.raw_parquet, args.intake, args.reservations,
                                args.history_root, args.out, args.execute),
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
