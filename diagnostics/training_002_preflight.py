"""CPU-only RHAR Training 002 preflight. Does not claim semantic correctness.

Requires multiple distinct, correctly terminated approved candidates before
a future training approval. Stress holdout and official eval data forbidden.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .training_candidates import FORBIDDEN

def audit(report, minimum=8):
    if report.get("status") != "training_data_candidates_only":
        raise ValueError("training candidate report required")
    selected = report.get("selected")
    if not isinstance(selected, list) or report.get("selected_count") != len(selected):
        raise ValueError("invalid selected candidate count")
    seen_ids, seen_prompts, issues = set(), set(), []
    for n, row in enumerate(selected, 1):
        source = str(row.get("source", "")).lower()
        flat = source.replace("-", "").replace("_", "").replace("+", "")
        if not source or any(s.replace("+","") in flat for s in FORBIDDEN) or "rhar003" in flat:
            issues.append(f"row {n}: forbidden or unspecified source")
        key = row.get("question_id")
        if not isinstance(key, str) or not key or key in seen_ids:
            issues.append(f"row {n}: invalid/duplicate question ID")
        seen_ids.add(key)
        prompt = row.get("prompt")
        if not isinstance(prompt,list) or not prompt or any(
            not isinstance(m,dict) or m.get("role") not in ("user","system") or
            not isinstance(m.get("content"),str) for m in prompt):
            issues.append(f"row {n}: invalid prompt")
            continue
        digest = hashlib.sha256(json.dumps(prompt,sort_keys=True).encode()).hexdigest()
        if digest in seen_prompts:
            issues.append(f"row {n}: duplicate prompt")
        seen_prompts.add(digest)
        text = row.get("completion")
        if (not isinstance(text,str) or text.count("<think>") != 1 or
                text.count("</think>") != 1 or not text.startswith("<think>") or
                text.index("</think>") < text.index("<think>") or
                not text.split("</think>",1)[1].strip() or
                not text.strip().splitlines()[-1].startswith("Final answer:")):
            issues.append(f"row {n}: incomplete or malformed reasoning/final")
        if not isinstance(row.get("total_tokens"),int) or row["total_tokens"] < 1:
            issues.append(f"row {n}: missing token accounting")
    if len(selected) < minimum:
        issues.append(f"insufficient diversity: {len(selected)} distinct examples, minimum {minimum}")
    return {"status":"candidate_gate_passed_manual_review_required" if not issues else "blocked",
            "selected":len(selected),"required_minimum":minimum,"issues":issues,
            "semantic_correctness_independently_verified":False,
            "eval_overlap_exhaustively_ruled_out":False,
            "gpu_used":False,"training_performed":False,"training_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates",type=Path,required=True)
    p.add_argument("--minimum",type=int,default=8)
    args=p.parse_args(argv)
    if args.minimum < 2:
        p.error("minimum must be >= 2")
    report=json.loads(args.candidates.read_text(encoding="utf-8"))
    print(json.dumps(audit(report,args.minimum),indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
