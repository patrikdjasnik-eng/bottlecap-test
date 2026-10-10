"""RHAR Dataset Builder 002 — CPU-only audited training-question worklist.

Uses existing, independently audited 12 GSM8K train questions. Never generates
reasoning, fabricates answers, downloads models or authorizes training.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .safe_start_generate import load_approved_inputs
from .safe_start_plan import build_prompt, BASE_MODEL, BASE_REVISION, SEEDS

def worklist(questions, attempts, *, exclude_ids=()):
    excluded = set(exclude_ids)
    if len(excluded) != len(list(exclude_ids)):
        raise ValueError("duplicate excluded ID")
    valid_ids = {q["question_id"] for q in questions}
    if not excluded <= valid_ids:
        raise ValueError("excluded ID not in audited GSM8K selection")
    items = []
    for q in questions:
        if q["question_id"] in excluded:
            continue
        subset = [x for x in attempts if x["question_id"] == q["question_id"]]
        if len(subset) != 3 or {x["seed"] for x in subset} != set(SEEDS):
            raise ValueError("missing or duplicated attempts")
        items.append({
            "question_id": q["question_id"],
            "source": q["source"], "source_revision": q["source_revision"],
            "split": q["split"], "task": q["task"],
            "prompt_sha256": hashlib.sha256(build_prompt(q["question"]).encode()).hexdigest(),
            "seeds": list(SEEDS), "generation_attempts": len(SEEDS),
            "gold_answer_exported": False,
            "question_text_exported": False,
            "status": "awaiting_generation_and_independent_grading"
        })
    return {"status": "plan_only", "research_only": True,
            "source": "gsm8k", "split": "train", "model": BASE_MODEL,
            "model_revision": BASE_REVISION, "question_count": len(items),
            "planned_generations": sum(x["generation_attempts"] for x in items),
            "questions": items, "training_performed": False, "gpu_used": False,
            "official_benchmark": False, "training_authorized": False,
            "candidate_count": 0, "eligible_for_training_now": False,
            "eval_overlap_exhaustively_ruled_out": False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--questions",type=Path,default=Path("data/safe-start/questions.jsonl"))
    p.add_argument("--selection",type=Path,default=Path("data/safe-start/selection-report.json"))
    p.add_argument("--audit",type=Path,default=Path("data/safe-start/overlap-audit.json"))
    p.add_argument("--exclude-id",action="append",default=[])
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    if args.out.exists():
        p.error("refusing overwrite")
    questions, attempts=load_approved_inputs(args.questions,args.selection,args.audit)
    report=worklist(questions,attempts,exclude_ids=args.exclude_id)
    report["input_sha256"]={str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (args.questions,args.selection,args.audit)}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k!="questions"},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
