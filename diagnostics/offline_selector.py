"""Offline RHAR v0.1 correctness gate and candidate selection; no model or GPU.

Read already-generated JSONL. Never execute generated text, download data, or train.
The selected.jsonl file is a REVIEW ARTIFACT, not a training dataset.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

# This is a small, CPU-only import: CASES contains six fixed hand-written questions.
# Legacy probe records omit task/kind, so only known cases may be inferred.
from .reasoning_probe import CASES as DIAGNOSTIC_CASES

LEGACY_DIAGNOSTIC_CASES = {case["id"]: case for case in DIAGNOSTIC_CASES}

FINAL_LINE = re.compile(r"^Final answer:[ \t]*([^\n]+?)[ \t]*$", re.MULTILINE)
NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")
OFFICIAL_PREFIXES = ("svamp", "mbpp", "bfcl", "ifeval")
KINDS = {"number": "number", "math": "number", "choice": "choice",
         "multiple_choice": "choice"}


def grade_final(text, gold, kind):
    """Strictly grade final-line math or choice answers, independent of recorded flags."""
    if not isinstance(text, str) or not isinstance(gold, str):
        return False, "missing_answer"
    lines = FINAL_LINE.findall(text.strip())
    if len(lines) != 1 or not text.strip().splitlines()[-1].startswith("Final answer:"):
        return False, "invalid_final_format"
    answer = lines[0].strip()
    if kind == "number":
        if not NUMBER.fullmatch(answer) or not NUMBER.fullmatch(gold):
            return False, "invalid_number_format"
        try:
            result = Decimal(answer.replace(",", "")) == Decimal(gold.replace(",", ""))
        except InvalidOperation:
            return False, "invalid_number_format"
    elif kind == "choice":
        if not re.fullmatch(r"[A-Za-z]", answer) or not re.fullmatch(r"[A-Za-z]", gold):
            return False, "invalid_choice_format"
        result = answer.upper() == gold.upper()
    else:
        return False, "unsupported_task"
    return (True, None) if result else (False, "incorrect_answer")


def assess_record(record):
    """Return a review record; correct is recomputed from the generated final text."""
    label = record.get("question_id", record.get("id"))
    gold = record.get("gold_answer", record.get("expected"))
    task = record.get("task", record.get("kind"))
    kind = KINDS.get(task)
    legacy_kind_inferred = False
    # The earlier reasoning_probe records id/category/expected, but not task/kind.
    # Infer type ONLY for exact built-in diagnostics with no source metadata.
    # This fallback can never turn historical probes into training examples.
    if kind is None and task is None and "source" not in record:
        known = LEGACY_DIAGNOSTIC_CASES.get(record.get("id"))
        if (known is not None and record.get("category") == known["category"]
                and gold == known["answer"]):
            kind = known["kind"]
            task = kind
            legacy_kind_inferred = True
    raw = record.get("generated_text", record.get("full_generated_text"))
    final = record.get("final_text")
    split_status = record.get("reasoning_split_status", record.get("split_status"))
    total = record.get("total_generated_tokens", record.get("total_tokens"))
    reason = record.get("reasoning_tokens")
    conclusion = record.get("final_tokens")
    outcome = {
        "question_id": label, "sample": record.get("sample"), "seed": record.get("seed"),
        "source": record.get("source"), "task": task,
        "legacy_diagnostic_kind_inferred": legacy_kind_inferred,
        "correct": False, "valid_generation": False, "training_eligible": False,
        "selected": False, "reason": None, "total_generated_tokens": total,
    }

    if not isinstance(label, str) or not label.strip() or kind is None or not isinstance(gold, str):
        outcome["reason"] = "invalid_question_metadata"
    elif record.get("truncated") is not False:
        outcome["reason"] = "truncated_or_unknown_termination"
    elif (not isinstance(total, int) or isinstance(total, bool) or total < 1
          or not isinstance(reason, int) or isinstance(reason, bool) or reason < 1
          or not isinstance(conclusion, int) or isinstance(conclusion, bool)
          or conclusion < 1 or total != reason + conclusion):
        outcome["reason"] = "invalid_token_accounting"
    elif not isinstance(raw, str) or not isinstance(final, str):
        outcome["reason"] = "missing_generated_text"
    elif ((split_status == "generated_think_block" and
           not (raw.count("<think>") == 1 and raw.count("</think>") == 1
                and raw.lstrip().startswith("<think>") and
                raw.index("<think>") < raw.index("</think>")))
          or (split_status == "prefilled_think_block" and
              not ("<think>" not in raw and raw.count("</think>") == 1))
          or split_status not in ("generated_think_block", "prefilled_think_block")):
        outcome["reason"] = "invalid_thinking_block"
    elif final.strip() not in raw.split("</think>", 1)[1]:
        outcome["reason"] = "inconsistent_final_text"
    else:
        correct, error = grade_final(final, gold, kind)
        if type(record.get("correct")) is bool and record["correct"] != correct:
            outcome["reason"] = "reported_correctness_mismatch"
        elif not correct:
            outcome["reason"] = error
        else:
            outcome["correct"] = True
            outcome["valid_generation"] = True
            # Diagnostic records without provenance are for inspection, NOT training.
            source = record.get("source")
            revision = record.get("model_revision", record.get("revision"))
            prompt_hash = record.get("prompt_hash")
            if (not isinstance(source, str) or not source.strip()
                or not isinstance(record.get("source_revision"), str)
                or not record["source_revision"]
                or record.get("split") != "train"
                or not isinstance(revision, str) or not revision
                or not isinstance(prompt_hash, str) or not prompt_hash
                or record.get("thinking_enabled") is not True
                or not isinstance(record.get("seed"), int)
                or isinstance(record.get("seed"), bool)):
                outcome["reason"] = "missing_training_provenance"
            elif re.sub(r"[^a-z0-9]", "", source.casefold()).startswith(OFFICIAL_PREFIXES):
                outcome["reason"] = "official_evaluation_source"
            else:
                outcome["training_eligible"] = True
                outcome["reason"] = "eligible_for_comparison"
    return outcome


def select_records(records, min_correct=2):
    """Select at most one shortest *correct* candidate per comparable training question."""
    if type(min_correct) is not int or min_correct < 2:
        raise ValueError("min_correct must be an integer >= 2")
    outcomes = [assess_record(r) for r in records]
    groups = defaultdict(list)
    for index, (record, outcome) in enumerate(zip(records, outcomes)):
        if outcome["training_eligible"]:
            groups[outcome["question_id"]].append(index)
    selected = []
    for indices in groups.values():
        def identity(r):
            return (r.get("source"), r.get("source_revision"),
                    r.get("task", r.get("kind")),
                    r.get("gold_answer", r.get("expected")),
                    r.get("prompt_hash"),
                    r.get("model", "Qwen/Qwen3-0.6B"),
                    r.get("model_revision", r.get("revision")),
                    r.get("thinking_enabled"), r.get("split"))
        if len({identity(records[i]) for i in indices}) != 1:
            for i in indices:
                outcomes[i].update(training_eligible=False, reason="conflicting_question_provenance")
            continue
        seen_seeds = set()
        unique = []
        for i in indices:
            seed = records[i]["seed"]
            if seed in seen_seeds:
                outcomes[i].update(training_eligible=False, reason="duplicate_seed")
                continue
            seen_seeds.add(seed)
            unique.append(i)
        if len(unique) < min_correct:
            for i in unique:
                outcomes[i]["reason"] = "insufficient_correct_comparisons"
            continue
        winner = min(unique, key=lambda i: (outcomes[i]["total_generated_tokens"], i))
        outcomes[winner].update(selected=True, reason="selected_for_review_only")
        for i in unique:
            if i != winner:
                outcomes[i]["reason"] = "longer_correct_comparison"
        selected.append({"question_id": outcomes[winner]["question_id"],
                         "seed": records[winner]["seed"],
                         "total_generated_tokens": outcomes[winner]["total_generated_tokens"],
                         "review_only": True,
                         "record": records[winner]})
    return outcomes, selected


def read_jsonl(path):
    """Fail closed on malformed input without writing partial outputs."""
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {e}") from e
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Existing diagnostic/pilot records.jsonl")
    parser.add_argument("--out", type=Path, default=None, help="Fresh output folder (never overwritten)")
    parser.add_argument("--min-correct", type=int, default=2,
                        help="Distinct correct seeds needed to select a review candidate (min 2)")
    args = parser.parse_args(argv)
    if args.min_correct < 2:
        parser.error("--min-correct must be >= 2")
    data = read_jsonl(args.input)
    outcomes, selected = select_records(data, min_correct=args.min_correct)
    out = args.out or (Path("runs") / "offline" /
                       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if out.exists():
        raise SystemExit(f"Output already exists: {out}")
    out.mkdir(parents=True, exist_ok=False)
    def write_jsonl(name, rows):
        (out / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                            for row in rows), encoding="utf-8")
    write_jsonl("review_records.jsonl", outcomes)
    write_jsonl("selected_for_review.jsonl", selected)
    summary = {"records": len(data), "correct_final_answers": sum(r["correct"] for r in outcomes),
               "training_eligible_candidates": sum(r["training_eligible"] for r in outcomes),
               "selected_for_review": len(selected),
               "reasons": dict(sorted(Counter(x["reason"] for x in outcomes).items())),
               "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
               "input_file": str(args.input), "no_training_performed": True,
               "official_benchmark": False, "review_only": True}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Offline review saved to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
