"""CPU-only RHAR 002 small batch planner. No inference, training or downloads."""
import argparse
import hashlib
import json
from pathlib import Path

def batch(worklist, size=2, start=0):
    if worklist.get("status") != "plan_only" or worklist.get("gpu_used") is not False or worklist.get("training_authorized") is not False:
        raise ValueError("untrusted worklist")
    rows=worklist.get("questions")
    if not isinstance(rows,list) or len(rows)!=worklist.get("question_count"):
        raise ValueError("worklist count mismatch")
    if type(size) is not int or not 1<=size<=3 or type(start) is not int or not 0<=start<len(rows):
        raise ValueError("size 1..3 and valid start required")
    selected=rows[start:start+size]
    if len(selected)!=size:
        raise ValueError("batch extends past worklist")
    ids=[r.get("question_id") for r in rows]
    if len(set(ids))!=len(ids) or any(not isinstance(x,str) or not x for x in ids):
        raise ValueError("duplicate/invalid IDs")
    if any(r.get("status")!="awaiting_generation_and_independent_grading" or
           r.get("generation_attempts")!=3 or r.get("seeds")!=[9001,9002,9003] or
           r.get("split")!="train" or r.get("source")!="gsm8k" or
           r.get("gold_answer_exported") is not False or
           r.get("question_text_exported") is not False or
           not isinstance(r.get("prompt_sha256"),str) or len(r["prompt_sha256"])!=64
           for r in selected):
        raise ValueError("invalid selected row provenance")
    return {"status":"plan_only","batch_start":start,"batch_size":size,
            "planned_generations":size*3,"question_ids":[r["question_id"] for r in selected],
            "prompt_hashes":[r["prompt_sha256"] for r in selected],
            "seeds":[9001,9002,9003],
            "gpu_used":False,"model_generations_performed":0,
            "training_performed":False,"training_authorized":False,
            "training_candidates_created":0,"official_benchmark":False,
            "next_action":"manual approval required for separately implemented GPU generation"}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worklist",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--size",type=int,default=2)
    p.add_argument("--start",type=int,default=0)
    args=p.parse_args(argv)
    if args.out.exists() or args.worklist.resolve()==args.out.resolve():
        p.error("will not overwrite input or output")
    raw=args.worklist.read_bytes()
    result=batch(json.loads(raw),args.size,args.start)
    result["source_worklist_sha256"]=hashlib.sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,indent=2,ensure_ascii=False)
        fp.write("\n")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
