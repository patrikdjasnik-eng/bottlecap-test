"""BottleCapAI: CPU-only supervised fine-tuning data builder.

Consumes independently graded rollout JSONL (not eval benchmark data).
No model loading or training; creates verified prompt/completion pairs.
"""
import argparse
import hashlib
import json
from pathlib import Path

FORBIDDEN = {"svamp", "mbpp", "mbpp+", "bfcl", "ifeval"}


def select(records):
    groups = {}
    rejected = {}
    fingerprints = {}
    for row in records:
        source = str(row.get("source", "")).lower()
        source_family = source.replace("-", "").replace("_", "")
        if any(name.replace("+", "") in source_family for name in FORBIDDEN):
            raise ValueError("evaluation-source contamination: " + source)
        required = ("question_id", "prompt", "full_generated_text", "total_tokens",
                    "correct", "truncated", "split_status", "source")
        if any(k not in row for k in required):
            raise ValueError("missing required generation metadata")
        key = row["question_id"]
        if not isinstance(key, str) or not key:
            raise ValueError("invalid question id")
        if not isinstance(row["prompt"], list) or not row["prompt"]:
            raise ValueError("missing chat messages")
        if any(not isinstance(m, dict) or m.get("role") not in ("user", "system") or
               not isinstance(m.get("content"), str) for m in row["prompt"]):
            raise ValueError("invalid prompt")
        prompt_fingerprint = hashlib.sha256(
            json.dumps(row["prompt"], sort_keys=True).encode()
        ).hexdigest()
        prev = groups.get(key)
        if key in fingerprints and fingerprints[key] != prompt_fingerprint:
            raise ValueError("question ID reused for different prompt")
        fingerprints[key] = prompt_fingerprint
        accepted = (row["correct"] is True and row["truncated"] is False and
                    row["split_status"] == "generated_think_block" and
                    isinstance(row["total_tokens"], int) and row["total_tokens"] > 0 and
                    isinstance(row["full_generated_text"], str) and
                    "<think>" in row["full_generated_text"] and
                    "</think>" in row["full_generated_text"])
        if not accepted:
            rejected[key] = rejected.get(key, 0) + 1
            continue
        entry = {"question_id": key, "source": source,
                 "prompt": row["prompt"], "completion": row["full_generated_text"],
                 "total_tokens": row["total_tokens"],
                 "prompt_fingerprint": prompt_fingerprint}
        if prev is None or entry["total_tokens"] < prev["total_tokens"]:
            groups[key] = entry
    selected = [groups[key] for key in sorted(groups)]
    return {"status": "training_data_candidates_only", "selected_count": len(selected),
            "rejected_count": sum(rejected.values()), "training_performed": False,
            "selected": selected}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.records.resolve() == args.out.resolve():
        parser.error("output cannot overwrite input")
    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    if not records:
        raise ValueError("empty input")
    report = select(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "selected"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
