"""RHAR 004: read-only heuristic review of existing reasoning steps.

No model, GPU, network, training, or assertion that a flagged step is wasteful.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

from .reasoning_structure import analyze_record, THINK

SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])|\n+")
EQUATION = re.compile(r"(?<!\w)([-+]?\d+(?:\.\d+)?)\s*([+*×x\-/])\s*([-+]?\d+(?:\.\d+)?)\s*=\s*([-+]?\d+(?:\.\d+)?)(?!\w)")
CUE = re.compile(r"\b(check|verify|double.check|again|alternatively|another way|wait|recalculate|let me)\b", re.I)


def review_record(record):
    metrics = analyze_record(record)
    if metrics["reasoning_word_count"] is None:
        return {**metrics, "steps": [], "flag_count": 0, "review_required": True}
    text = THINK.findall(record["full_generated_text"])[0]
    steps = [part.strip() for part in SENTENCE.split(text) if part.strip()]
    expressions = defaultdict(list)
    result = []
    for index, step in enumerate(steps, 1):
        equations = []
        for m in EQUATION.finditer(step):
            a, op, b, claimed = m.groups()
            x, y, z = float(a), float(b), float(claimed)
            actual = {"+": lambda: x+y, "-": lambda: x-y,
                      "*": lambda: x*y, "×": lambda: x*y, "x": lambda: x*y,
                      "/": lambda: x/y if y else None}[op]()
            expression = f"{a}{op}{b}"
            equations.append({"expression": expression, "claimed": claimed,
                              "arithmetic_consistent": actual is not None and abs(actual-z) < 1e-8})
            expressions[expression].append(index)
        cues = sorted(set(m.group(0).lower() for m in CUE.finditer(step)))
        result.append({"step": index, "excerpt": step[:180], "excerpt_truncated": len(step) > 180,
                       "equations": equations, "review_cues": cues,
                       "repeated_equation": False, "needs_human_review": bool(cues)})
    for item in result:
        item["repeated_equation"] = any(len(expressions[e["expression"]]) > 1
                                       for e in item["equations"])
        item["needs_human_review"] |= item["repeated_equation"]
    return {**metrics, "steps": result,
            "flag_count": sum(bool(s["needs_human_review"]) for s in result),
            "review_required": True, "semantic_redundancy_proven": False}


def analyze_file(path):
    reports = []
    with Path(path).open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                reports.append(review_record(json.loads(line)))
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"line {lineno}: {exc}") from exc
    if not reports:
        raise ValueError("no records")
    return {"status": "rhar_004_review_only", "record_count": len(reports),
            "gpu_used": False, "training_performed": False,
            "semantic_quality_verified": False, "records": reports}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = analyze_file(args.records)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        if args.out.resolve() == args.records.resolve():
            parser.error("output must differ from input")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as f:
            f.write(output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
