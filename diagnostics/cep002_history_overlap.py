"""CEP-002 historical overlap screen. CPU-only; never reads reserved holdout questions.

Compares already viewed GSM8K main/train review candidates and hash-only future
holdout reservations against earlier Safe Start questions and all stored
runs/**/records.jsonl under the ORIGINAL research directory.

Important: this is an auditable PARTIAL screen, not independent proof of
semantic non-overlap, and it cannot grant training approval.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

SOURCE = "gsm8k/main/train"
EXPECTED_CANDIDATES = 12
EXPECTED_RESERVED = 60
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
QUESTION_ID_RE = re.compile(r"gsm8k-train-\d{5}\Z")
NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
REQUIRED_RUNS = (
    "rhar-validation-005/records.jsonl",
    "rhar-validation-006/records.jsonl",
)
MAX_JSONL_LINE = 2_000_000


def normalized(text: str) -> str:
    return " ".join(NORMALIZE_RE.sub(" ", text.lower()).split())


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError("required audit file missing: " + str(path))
    items = []
    with path.open(encoding="utf-8") as stream:
        for line_num, line in enumerate(stream, 1):
            if not line.strip():
                continue
            if len(line) > MAX_JSONL_LINE:
                raise ValueError(f"oversized JSONL record in {path} line {line_num}")
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL in {path} line {line_num}") from error
            if not isinstance(item, dict):
                raise ValueError(f"non-object JSONL in {path} line {line_num}")
            items.append(item)
    if not items:
        raise ValueError("empty audit source: " + str(path))
    return items


def load_targets(candidate_path: Path, reservation_path: Path) -> dict:
    candidates = load_jsonl(candidate_path)
    reservations = load_jsonl(reservation_path)
    if len(candidates) != EXPECTED_CANDIDATES or len(reservations) != EXPECTED_RESERVED:
        raise ValueError("unexpected review/holdout partition size")
    target = {}
    for candidate in candidates:
        task_id = candidate.get("question_id")
        question = candidate.get("question")
        digest = candidate.get("question_sha256")
        if (not isinstance(task_id, str) or not QUESTION_ID_RE.fullmatch(task_id)
                or not isinstance(question, str) or not question.strip()
                or not isinstance(digest, str) or not HASH_RE.fullmatch(digest)
                or sha256(question.encode()).hexdigest() != digest
                or candidate.get("source") != SOURCE
                or candidate.get("status") != "REVIEW_REQUIRED"
                or candidate.get("approved_for_training") is not False):
            raise ValueError("invalid or previously approved review candidate")
        if task_id in target:
            raise ValueError("duplicate candidate ID")
        target[task_id] = {"sha256": digest, "normalized": normalized(question), "kind": "review"}
    for row in reservations:
        task_id = row.get("question_id")
        digest = row.get("question_sha256")
        if (not isinstance(task_id, str) or not QUESTION_ID_RE.fullmatch(task_id)
                or not isinstance(digest, str) or not HASH_RE.fullmatch(digest)
                or set(row) != {"question_id", "question_sha256"}
                or task_id in target):
            raise ValueError("invalid or duplicate reserved holdout reference")
        target[task_id] = {"sha256": digest, "normalized": None, "kind": "reserved"}
    hashes = [v["sha256"] for v in target.values()]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate question hashes between partitions")
    return target


def extract_references(row: dict) -> tuple[set[str], set[str], set[str]]:
    """Return task IDs, literal source-question hashes, and potential question text.

    Never inspect generated_text, gold, answer, output, labels or model reasoning.
    """
    task_ids: set[str] = set()
    question_hashes: set[str] = set()
    texts: set[str] = set()
    for key in ("question_id", "task_id", "id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            task_ids.add(value.strip())
    value = row.get("question_sha256")
    if isinstance(value, str) and HASH_RE.fullmatch(value):
        question_hashes.add(value)
    for key in ("question", "prompt", "input"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            texts.add(value.strip())
        elif isinstance(value, list):
            for message in value:
                if (isinstance(message, dict)
                        and message.get("role") == "user"
                        and isinstance(message.get("content"), str)
                        and message["content"].strip()):
                    texts.add(message["content"].strip())
    value = row.get("messages")
    if isinstance(value, list):
        for message in value:
            if (isinstance(message, dict)
                    and message.get("role") == "user"
                    and isinstance(message.get("content"), str)
                    and message["content"].strip()):
                texts.add(message["content"].strip())
    return task_ids, question_hashes, texts


def scan(targets: dict, safe_start: Path, history_root: Path) -> tuple[list[dict], dict]:
    if not history_root.is_dir():
        raise FileNotFoundError("historical runs directory missing")
    run_paths = sorted(history_root.glob("**/records.jsonl"))
    for required in REQUIRED_RUNS:
        if not (history_root / required) in run_paths:
            raise FileNotFoundError("required historical run missing: " + required)
    if not run_paths:
        raise ValueError("no historical records files found")
    sources = [safe_start, *run_paths]
    matches: list[dict] = []
    row_count = 0
    question_text_rows = 0
    id_only_rows = 0
    opaque_rows = 0
    file_details = []
    for source in sources:
        rows = load_jsonl(source)
        has_text = 0
        has_id_without_text = 0
        has_no_reference = 0
        relative = ("data/safe-start/questions.jsonl" if source == safe_start
                    else "runs/" + source.relative_to(history_root).as_posix())
        for row in rows:
            row_count += 1
            task_ids, digests, strings = extract_references(row)
            if strings:
                has_text += 1
                question_text_rows += 1
            elif task_ids or digests:
                has_id_without_text += 1
                id_only_rows += 1
            else:
                has_no_reference += 1
                opaque_rows += 1
            normalized_strings = [normalized(value) for value in strings]
            raw_digests = {sha256(value.encode()).hexdigest() for value in strings}
            for task_id, target in targets.items():
                reasons = []
                if task_id in task_ids:
                    reasons.append("question_id")
                if target["sha256"] in digests or target["sha256"] in raw_digests:
                    reasons.append("question_sha256")
                reference = target["normalized"]
                if reference is not None and reference:
                    if any(reference == string for string in normalized_strings):
                        reasons.append("normalized_question")
                    elif len(reference) >= 70 and any(reference in string for string in normalized_strings):
                        reasons.append("embedded_question")
                if reasons:
                    matches.append({
                        "task_id": task_id,
                        "partition": target["kind"],
                        "history_file": relative,
                        "signals": sorted(set(reasons)),
                    })
        file_details.append({
            "path": relative,
            "records": len(rows),
            "rows_with_question_text": has_text,
            "rows_with_id_only": has_id_without_text,
            "rows_without_recognized_reference": has_no_reference,
        })
    stats = {
        "historical_source_files": len(sources),
        "historical_record_files": len(run_paths),
        "historical_rows": row_count,
        "rows_with_candidate_question_text": question_text_rows,
        "id_or_hash_only_rows": id_only_rows,
        "opaque_rows": opaque_rows,
        "files": file_details,
    }
    return matches, stats


def historical_audit(
    intake: Path,
    reservations: Path,
    safe_start: Path,
    history_root: Path,
    output: Path,
    execute: bool,
) -> dict:
    if execute and output.exists():
        raise FileExistsError("refusing to overwrite historical audit")
    targets = load_targets(intake, reservations)
    matches, stats = scan(targets, safe_start, history_root)
    collided = sorted({row["task_id"] for row in matches})
    review_hits = sorted(task_id for task_id in collided if targets[task_id]["kind"] == "review")
    holdout_hits = sorted(task_id for task_id in collided if targets[task_id]["kind"] == "reserved")
    summary = {
        "status": "overlap_detected" if collided else "partial_historical_screen_no_match",
        "mode": "execute" if execute else "dry_run",
        "review_candidate_count": EXPECTED_CANDIDATES,
        "reserved_holdout_count": EXPECTED_RESERVED,
        "review_overlaps": len(review_hits),
        "reserved_holdout_overlaps": len(holdout_hits),
        "matched_historical_records": len(matches),
        "seen_candidate_ids": review_hits,
        "seen_reserved_ids": holdout_hits,
        **stats,
        "historical_sources_fully_screened": False,
        "question_text_missing_from_some_records": stats["id_or_hash_only_rows"] > 0,
        "unrecognized_record_shapes_present": stats["opaque_rows"] > 0,
        "semantic_duplicate_check_exhaustive": False,
        "official_benchmark": False,
        "official_questions_or_answers_exported": False,
        "holdout_questions_accessed": False,
        "training_approved": False,
        "training_records_exported": 0,
        "gpu_used": False,
        "training_performed": False,
    }
    if execute:
        output.mkdir(parents=True, exist_ok=False)
        with (output / "overlaps.jsonl").open("x", encoding="utf-8") as stream:
            for item in matches:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        with (output / "summary.json").open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path,
                        default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    parser.add_argument("--reservations", type=Path,
                        default=Path("runs/cep002-data-intake-001/holdout-reservation.jsonl"))
    parser.add_argument("--safe-start", type=Path, required=True)
    parser.add_argument("--history-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("runs/cep002-history-audit-001"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    result = historical_audit(
        args.intake, args.reservations, args.safe_start, args.history_root,
        args.out, args.execute,
    )
    console = {key: value for key, value in result.items() if key != "files"}
    print(json.dumps(console, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
