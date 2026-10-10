"""CPU-only RHAR 003 trace event review. Heuristics are NOT semantic grading.

Reads full local diagnostic holdout records; reports contexts of answer numbers,
explicit self-correction cues and repeated phrases. Never trains or runs GPU.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from collections import Counter

CUES = re.compile(r"\b(?:wait|hold on|mistake|incorrect|wrong|check again|double.check|"
                  r"recheck|recalculate|verify|actually|correcting)\b", re.IGNORECASE)
NUMBERS = re.compile(r"(?<![\w.])(?:28|20)(?![\w.])")


def review_record(row, excerpt=105):
    raw = row.get("generated_text")
    if not isinstance(raw, str) or not raw:
        raise ValueError("missing generated text")
    if row.get("task_id") != "rhar003-math-01":
        raise ValueError("only RHAR 003 math task 01 is supported")
    if type(row.get("seed")) is not int or type(row.get("budget")) is not int:
        raise ValueError("invalid seed or budget")
    if row.get("training_data_allowed") is not False:
        raise ValueError("holdout provenance missing")
    thinking = raw.split("</think>", 1)[0].removeprefix("<think>")
    found = []
    for match in NUMBERS.finditer(thinking):
        lo, hi = max(0, match.start() - excerpt), min(len(thinking), match.end() + excerpt)
        found.append({"number": match.group(), "position": match.start(),
                      "context": thinking[lo:hi]})
    cues = [{"cue": x.group(), "position": x.start(),
             "context": thinking[max(0, x.start()-excerpt):x.end()+excerpt]}
            for x in CUES.finditer(thinking)]
    phrases = re.findall(r"\b[a-z]+\b", thinking.casefold())
    repeated = Counter(tuple(phrases[i:i+6]) for i in range(max(len(phrases)-5, 0)))
    repeated = [{"phrase": " ".join(k), "count": v}
                for k,v in repeated.items() if v > 1]
    repeated.sort(key=lambda x: (-x["count"], x["phrase"]))
    return {"seed": row["seed"], "budget": row["budget"],
            "correct_completed_response": row.get("correct") is True and row.get("truncated") is False,
            "truncated": row.get("truncated"),
            "number_mentions": found, "correction_cues": cues,
            "repeated_six_word_phrases": repeated[:20],
            "possible_answer_revision": any(x["number"] == "28" for x in found) and
                                        any(x["number"] == "20" for x in found),
            "revision_proven": False, "redundancy_proven": False,
            "semantic_reasoning_verified": False,
            "training_data_allowed": False}


def review(records):
    if len(records) != 4:
        raise ValueError("expected exactly four stress task 01 records")
    pairs = {(r.get("seed"), r.get("budget")) for r in records}
    if pairs != {(9001,512),(9003,512),(9001,1024),(9003,1024)}:
        raise ValueError("incomplete or duplicated seed/budget matrix")
    return {"status": "heuristic_review_only", "task_id": "rhar003-math-01",
            "record_count": 4, "gpu_used": False, "training_performed": False,
            "semantic_reasoning_verified": False,
            "training_data_allowed": False,
            "records": [review_record(r) for r in records]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.records.resolve() == args.out.resolve():
        parser.error("cannot overwrite input")
    rows = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    report = review(rows)
    report["source_sha256"] = hashlib.sha256(args.records.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "records": 4,
                      "source_sha256": report["source_sha256"],
                      "training_performed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
