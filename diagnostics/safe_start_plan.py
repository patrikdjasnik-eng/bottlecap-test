"""CPU-only RHAR Safe Start planning and validation. Never runs a model.

No model/dataset imports or downloads; read-only validation of a local, approved
12-question JSONL file and deterministic construction of 36 proposed attempts.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from .reasoning_probe import BASE_MODEL, BASE_REVISION, SAMPLING

QUESTION_COUNT = 12
SAMPLES_PER_QUESTION = 3
SEEDS = (9001, 9002, 9003)
MAX_NEW_TOKENS = 512
SOURCE = "gsm8k"
INSTRUCTION = "On the last line, write 'Final answer:' followed by your answer."
REQUIRED_FIELDS = frozenset({"question_id", "question", "gold_answer", "source",
                             "source_revision", "split", "task"})
REVISION = re.compile(r"[0-9a-f]{40}\Z")
NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?\Z")


def build_prompt(question):
    """Neutral format instruction: no gold answer and no shortening request."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be non-empty text")
    return question.strip() + "\n\n" + INSTRUCTION


def read_questions(path):
    """Read existing local JSONL; never open a URL, fetch data or write output."""
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_number}: expected an object")
            rows.append(row)
    return rows


def validate_questions(rows):
    """Fail closed on provenance, unknown fields, malformed answers or duplicates."""
    if not isinstance(rows, list) or len(rows) != QUESTION_COUNT:
        raise ValueError(f"exactly {QUESTION_COUNT} questions are required")
    ids, normalized_questions, revisions = set(), set(), set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != REQUIRED_FIELDS:
            raise ValueError(f"question {index}: expected exact schema {sorted(REQUIRED_FIELDS)}")
        qid, question, gold = row["question_id"], row["question"], row["gold_answer"]
        if not isinstance(qid, str) or not qid.strip() or qid != qid.strip():
            raise ValueError(f"question {index}: invalid question_id")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"question {index}: empty question")
        if not isinstance(gold, str) or not NUMBER.fullmatch(gold):
            raise ValueError(f"question {index}: gold_answer must be a numeric string")
        if (row["source"] != SOURCE or row["split"] != "train"
                or row["task"] != "math"):
            raise ValueError(f"question {index}: only GSM8K train/math is allowed in Safe Start")
        revision = row["source_revision"]
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            raise ValueError(f"question {index}: source_revision must be a pinned 40-hex commit")
        norm = " ".join(question.casefold().split())
        if qid in ids or norm in normalized_questions:
            raise ValueError(f"question {index}: duplicate question_id or question text")
        ids.add(qid)
        normalized_questions.add(norm)
        revisions.add(revision)
    if len(revisions) != 1:
        raise ValueError("all questions must use one pinned source revision")
    # Exact duplicate checking does not prove absence of benchmark overlap.
    return True


def plan_attempts(rows):
    """Deterministic read-only manifest; no question, gold or reasoning in output."""
    validate_questions(rows)
    result = []
    for row in rows:
        digest = hashlib.sha256(build_prompt(row["question"]).encode("utf-8")).hexdigest()
        for sample, seed in enumerate(SEEDS):
            result.append({"question_id": row["question_id"], "source": SOURCE,
                           "source_revision": row["source_revision"], "split": "train",
                           "task": "math", "sample": sample, "seed": seed,
                           "model": BASE_MODEL, "model_revision": BASE_REVISION,
                           "thinking_enabled": True, "sampling": dict(SAMPLING),
                           "max_new_tokens": MAX_NEW_TOKENS,
                           "prompt_hash": "sha256:" + digest, "plan_only": True})
    assert len(result) == QUESTION_COUNT * SAMPLES_PER_QUESTION
    return result


def summary(rows=None):
    """A plan, not observations from a model."""
    result = {"status": "plan_only", "question_count": QUESTION_COUNT,
              "samples_per_question": SAMPLES_PER_QUESTION,
              "planned_generations": QUESTION_COUNT * SAMPLES_PER_QUESTION,
              "seeds": list(SEEDS), "source": SOURCE, "split": "train",
              "model": BASE_MODEL, "model_revision": BASE_REVISION,
              "thinking_enabled": True, "sampling": dict(SAMPLING),
              "max_new_tokens": MAX_NEW_TOKENS,
              "dataset_downloaded": False, "gpu_used": False,
              "training_performed": False, "official_benchmark": False}
    if rows is not None:
        attempts = plan_attempts(rows)
        result["validated_local_questions"] = len(rows)
        result["validated_planned_attempts"] = len(attempts)
        result["question_ids"] = [r["question_id"] for r in rows]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print proposed settings only")
    parser.add_argument("--questions", type=Path, help="Existing, separately approved local JSONL")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("Safe Start planner only supports --dry-run (no execution)")
    rows = read_questions(args.questions) if args.questions is not None else None
    print(json.dumps(summary(rows), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
