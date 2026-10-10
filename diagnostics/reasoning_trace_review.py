"""CPU-only human review of a selected RHAR reasoning trace.

Outputs the full original reasoning for human inspection. This tool never
certifies semantic correctness, updates the model, or launches GPU.
"""
import argparse
import json
from pathlib import Path


def inspect(records, seed):
    matches = [r for r in records if r.get("seed") == seed]
    if len(matches) != 1:
        raise ValueError("expected exactly one matching seed")
    row = matches[0]
    if row.get("correct") is not True or row.get("truncated") is not False:
        raise ValueError("only complete, correctly graded answers can be reviewed")
    if row.get("reasoning_split_status") != "generated_think_block":
        raise ValueError("unexpected reasoning split")
    content = row.get("generated_text")
    if not isinstance(content, str) or content.count("<think>") != 1 or content.count("</think>") != 1:
        raise ValueError("malformed generated reasoning")
    start, rest = content.split("<think>", 1)
    thinking, final = rest.split("</think>", 1)
    if start.strip() or not thinking.strip() or not final.strip():
        raise ValueError("invalid reasoning or final text")
    return {"question_id": row["question_id"], "seed": seed,
            "total_generated_tokens": row["total_generated_tokens"],
            "reasoning_tokens": row["reasoning_tokens"],
            "automatically_graded_correct": True,
            "semantic_reasoning_verified": False,
            "thinking": thinking, "final": final}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--seed", type=int, default=9003)
    args = parser.parse_args(argv)
    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    report = inspect(records, args.seed)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
