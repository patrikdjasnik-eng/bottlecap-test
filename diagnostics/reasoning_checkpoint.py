"""RHAR 006: offline arithmetic checkpoints on existing reasoning records.

Conservative textual evidence only. Character offsets are NOT token counts.
No early-stop, inference, model changes or measured token savings.
"""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from .semantic_repetition import normalized_operations
from .reasoning_structure import THINK
from .reasoning_steps import review_record

NUMBER = r"[-+]?\d+(?:\.\d+)?"
CLAIM = re.compile(
    rf"(?<![\w.])({NUMBER})\s*(?:is|equals|=|gives|would be)\s*({NUMBER})(?![\w.])",
    re.I,
)
RESULT = re.compile(rf"\b(?:remaining|answer|result|be)\s*(?:is|would be|should be)?\s*({NUMBER})(?![\w.])", re.I)


def check_operations(text):
    output = []
    for item in normalized_operations(text):
        tail = text[item["end"]:item["end"] + 35]
        match = re.match(rf"\s*(?:is|equals|=|gives|would be)\s*({NUMBER})(?![\w.])", tail, re.I)
        claimed = match.group(1) if match else None
        canonical = item["canonical"]
        try:
            a, op, b = canonical.split()
            x, y = Decimal(a), Decimal(b)
            computed = {"+": lambda: x + y, "-": lambda: x - y,
                        "*": lambda: x * y, "/": lambda: x / y if y else None}[op]()
            consistent = (computed == Decimal(claimed)) if claimed is not None else None
        except (InvalidOperation, ValueError, ZeroDivisionError):
            consistent = None
        output.append({**item, "claimed_result": claimed,
                       "arithmetic_consistent": consistent})
    return output


def analyze_record(record):
    base = review_record(record)
    matches = THINK.findall(record["full_generated_text"])
    if not matches or base["reasoning_word_count"] is None:
        return {**base, "operations": [], "candidate_checkpoint": None,
                "reasoning_characters_after_checkpoint": None,
                "measured_token_savings": None, "early_stop_safety_verified": False}
    text = matches[0]
    operations = check_operations(text)
    gold = record.get("expected")
    candidate = None
    if isinstance(gold, str) and gold.strip() and record.get("correct") is True:
        for match in RESULT.finditer(text):
            if match.group(1) != gold:
                continue
            preceding = text[:match.end()]
            if len(preceding) < 1:
                continue
            candidate = {"offset_end_char": match.end(),
                         "matched_text": match.group(0),
                         "reason": "first text answer candidate; manual verification required"}
            break
    return {**base, "operations": operations,
            "candidate_checkpoint": candidate,
            "reasoning_characters_after_checkpoint": len(text) - candidate["offset_end_char"]
            if candidate else None,
            "measured_token_savings": None,
            "early_stop_safety_verified": False,
            "semantic_redundancy_proven": False}


def analyze_file(path):
    rows = []
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                rows.append(analyze_record(json.loads(line)))
            except (KeyError, ValueError, TypeError) as error:
                raise ValueError(f"line {line_number}: {error}") from error
    if not rows:
        raise ValueError("no records")
    return {"status": "rhar_006_review_only", "record_count": len(rows),
            "gpu_used": False, "training_performed": False,
            "token_savings_measured": False, "records": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = analyze_file(args.records)
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out is not None:
        if args.out.resolve() == args.records.resolve():
            parser.error("output cannot overwrite input")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
