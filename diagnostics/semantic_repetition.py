"""RHAR 005: CPU-only heuristics for repeated arithmetic in saved reasoning.

Detection is not proof that a step can be removed. No inference or training.
"""
import argparse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from .reasoning_steps import review_record
from .reasoning_structure import THINK

NUM = r"[-+]?\d+(?:\.\d+)?"
OP = r"(?:times|multiplied by|plus|minus|divided by|[×*+−/])"
PATTERN = re.compile(rf"(?<![\w.])({NUM})\s*({OP})\s*({NUM})(?![\w.])", re.I)
OPERATORS = {
    "times": "*", "multiplied by": "*", "×": "*", "*": "*",
    "plus": "+", "+": "+", "minus": "-", "−": "-", 
    "divided by": "/", "/": "/",
}


def normalized_operations(text):
    operations = []
    for match in PATTERN.finditer(text):
        left, operator, right = match.groups()
        op = OPERATORS[operator.lower()]
        try:
            a, b = Decimal(left), Decimal(right)
            if op == "/" and b == 0:
                continue
            if op in ("+", "*") and b < a:
                a, b = b, a
            key = f"{a.normalize()} {op} {b.normalize()}"
        except InvalidOperation:
            continue
        operations.append({"expression": match.group(0), "canonical": key,
                           "start": match.start(), "end": match.end()})
    return operations


def analyze(record):
    baseline = review_record(record)
    matches = THINK.findall(record["full_generated_text"])
    if not matches or baseline["reasoning_word_count"] is None:
        return {**baseline, "operations": [], "repeat_count": 0,
                "first_answer_step": None, "post_answer_steps": None,
                "semantic_redundancy_proven": False}
    reasoning = matches[0]
    operations = normalized_operations(reasoning)
    seen = defaultdict(list)
    for operation in operations:
        previous = seen[operation["canonical"]]
        operation["repeat_of_occurrence"] = previous[0] if previous else None
        operation["occurrence"] = len(seen.setdefault(operation["canonical"], [])) + 1
        previous.append(operation["occurrence"])
    gold = record.get("expected")
    first_answer_step = None
    if isinstance(gold, str) and gold.strip():
        for step in baseline["steps"]:
            if re.search(rf"(?<![\w.]){re.escape(gold)}(?![\w.])", step["excerpt"]):
                first_answer_step = step["step"]
                break
    return {**baseline, "operations": operations,
            "repeat_count": sum(op["repeat_of_occurrence"] is not None for op in operations),
            "first_answer_step": first_answer_step,
            "post_answer_steps": len(baseline["steps"]) - first_answer_step
            if first_answer_step is not None else None,
            "semantic_redundancy_proven": False,
            "early_stop_safety_verified": False}


def analyze_file(path):
    records = []
    with Path(path).open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                records.append(analyze(json.loads(line)))
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f"line {number}: {error}") from error
    if not records:
        raise ValueError("empty records")
    return {"status": "rhar_005_review_only", "record_count": len(records),
            "gpu_used": False, "training_performed": False,
            "token_savings_measured": False, "records": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = analyze_file(args.records)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        if args.out.resolve() == args.records.resolve():
            parser.error("cannot overwrite source")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as file:
            file.write(output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
