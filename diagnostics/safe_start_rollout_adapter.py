"""CPU-only conversion of audited RHAR Safe Start rollouts to candidate inputs.

This is a data adapter, not training authorization. It validates records against
the original pinned question and audit files before passing to the selector.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .safe_start_generate import load_approved_inputs
from .safe_start_plan import build_prompt
from .training_candidates import select


def convert(records, questions):
    by_id = {q["question_id"]: q for q in questions}
    if len(by_id) != len(questions):
        raise ValueError("duplicate questions")
    output = []
    for row in records:
        qid = row.get("question_id")
        if qid not in by_id:
            raise ValueError("unknown question ID")
        q = by_id[qid]
        for key in ("source", "source_revision", "split", "task", "gold_answer"):
            if row.get(key) != q[key]:
                raise ValueError(f"mismatched {key} for {qid}")
        prompt = build_prompt(q["question"])
        digest = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if row.get("prompt_hash") != digest:
            raise ValueError("prompt hash mismatch")
        if row.get("thinking_enabled") is not True or row.get("research_only") is not True:
            raise ValueError("unexpected generation policy")
        if row.get("model_generations_performed") not in (None, 1):
            raise ValueError("unexpected generation count")
        if row.get("model") != "Qwen/Qwen3-0.6B":
            raise ValueError("wrong model")
        from .safe_start_plan import BASE_REVISION
        if row.get("model_revision") != BASE_REVISION:
            raise ValueError("wrong model revision")
        if row.get("reasoning_split_status") != "generated_think_block":
            # Preserve rejection, do not fabricate missing <think> markers.
            split = row.get("reasoning_split_status")
        else:
            split = "generated_think_block"
        tokens = row.get("total_generated_tokens")
        if type(tokens) is not int or tokens <= 0:
            raise ValueError("invalid token count")
        if row.get("correct") is not True and row.get("correct") is not False:
            raise ValueError("missing independent grading result")
        if type(row.get("truncated")) is not bool:
            raise ValueError("invalid truncation flag")
        output.append({
            "question_id": qid, "source": q["source"],
            "prompt": [{"role": "user", "content": prompt}],
            "full_generated_text": row.get("generated_text"),
            "total_tokens": tokens, "correct": row["correct"],
            "truncated": row["truncated"], "split_status": split,
        })
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--questions", type=Path, default=Path("data/safe-start/questions.jsonl"))
    parser.add_argument("--selection-report", type=Path, default=Path("data/safe-start/selection-report.json"))
    parser.add_argument("--overlap-audit", type=Path, default=Path("data/safe-start/overlap-audit.json"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.resolve() in {args.records.resolve(), args.questions.resolve(),
                              args.selection_report.resolve(), args.overlap_audit.resolve()}:
        parser.error("cannot overwrite input")
    questions, _ = load_approved_inputs(args.questions, args.selection_report, args.overlap_audit)
    rows = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("empty rollout file")
    report = select(convert(rows, questions))
    report["audit_status"] = "review_only_not_exhaustive"
    report["training_approved"] = False
    report["source_records_sha256"] = hashlib.sha256(args.records.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k != "selected"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
