"""RHAR 003: offline structure metrics for existing reasoning probe JSONL.

CPU-only, standard library only, no model imports, no network, no training.
Heuristics describe text structure; they cannot identify unnecessary reasoning.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

WORDS = re.compile(r"\b\w+\b", re.UNICODE)
THINK = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def analyze_record(record):
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    required = ("id", "correct", "total_tokens", "reasoning_tokens",
                "final_tokens", "split_status", "truncated", "full_generated_text")
    if any(k not in record for k in required):
        raise ValueError("missing required reasoning probe fields")
    total = record["total_tokens"]
    reasoning = record["reasoning_tokens"]
    final = record["final_tokens"]
    if type(total) is not int or total < 0:
        raise ValueError("invalid token count")
    if reasoning is not None and (type(reasoning) is not int or reasoning < 0):
        raise ValueError("invalid reasoning count")
    if final is not None and (type(final) is not int or final < 0):
        raise ValueError("invalid final count")
    if reasoning is not None and final is not None and reasoning + final != total:
        raise ValueError("token accounting mismatch")
    raw = record["full_generated_text"]
    if not isinstance(raw, str):
        raise ValueError("invalid generated text")
    matches = THINK.findall(raw)
    recognized = record["split_status"] in (
        "generated_think_block", "prefilled_think_block"
    )
    if recognized and len(matches) != 1:
        raise ValueError("recognized thinking split but text markers are missing")
    reasoning_text = matches[0] if recognized else None
    words = WORDS.findall(reasoning_text.casefold()) if reasoning_text is not None else []
    fourgrams = Counter(tuple(words[i:i + 4]) for i in range(max(len(words) - 3, 0)))
    repeat_occurrences = sum(count - 1 for count in fourgrams.values() if count > 1)
    sections = [x.strip() for x in re.split(r"\n\s*\n", reasoning_text or "") if x.strip()]
    return {
        "id": record["id"],
        "correct": record["correct"],
        "truncated": record["truncated"],
        "split_status": record["split_status"],
        "total_tokens": total,
        "reasoning_tokens": reasoning,
        "final_tokens": final,
        "reasoning_share_pct": round(reasoning / total * 100, 2)
        if total and reasoning is not None else None,
        "reasoning_word_count": len(words) if recognized else None,
        "paragraph_count": len(sections) if recognized else None,
        "repeated_fourgram_occurrences": repeat_occurrences if recognized else None,
        "repetition_is_waste_proof": False,
        "semantic_step_quality_assessed": False,
    }


def analyze_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(analyze_record(json.loads(line)))
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"line {line_number}: {exc}") from exc
    if not rows:
        raise ValueError("no records in file")
    return {
        "status": "offline_structure_audit",
        "record_count": len(rows),
        "gpu_used": False,
        "training_performed": False,
        "official_benchmark": False,
        "interpretation": "Structural heuristics only; no proof of redundant reasoning.",
        "records": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="Existing records.jsonl")
    parser.add_argument("--out", type=Path, help="New JSON report; never overwrite")
    args = parser.parse_args(argv)
    result = analyze_jsonl(args.records)
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out is not None:
        if args.out.resolve() == args.records.resolve():
            parser.error("cannot overwrite source records")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
