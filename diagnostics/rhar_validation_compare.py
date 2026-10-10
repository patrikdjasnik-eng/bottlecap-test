"""Paired RHAR SFT 003 vs CEP 001 evaluation on disjoint GSM8K TRAIN validation.

No official benchmark scores. The same deterministic validation split used for
both models' loss measurement, not their weight updates. This is NOT a novel
independent test set and must not be used for further training or model selection.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .rhar_train_003 import prepare_pool,reject_overlap
from .safe_start_data import TRAIN_SHA256,read_parquet,read_eval_prompts
from .reasoning_probe import BASE_MODEL,BASE_REVISION,split_reasoning
from .offline_selector import grade_final

SEED=9001
SAMPLING={"temperature":0.6,"top_p":0.95,"top_k":20}

def pick_validation(raw,train_size=1000,val_size=100,seed=42,count=20):
    if not 1<=count<=val_size:
        raise ValueError("count must be between 1 and val-size")
    _,validation=prepare_pool(raw,train_size,val_size,seed)
    return validation[:count]

def summarize(records):
    if not records or len(records)%2:
        raise ValueError("expected complete paired records")
    a=[r for r in records if r["variant"]=="sft"]
    b=[r for r in records if r["variant"]=="cep"]
    if len(a)!=len(b) or [r["id"] for r in a]!=[r["id"] for r in b]:
        raise ValueError("unpaired records")
    def metrics(rows):
        return {"correct":sum(r["correct"] for r in rows),"complete":sum(not r["truncated"] for r in rows),
                "mean_tokens":round(sum(r["tokens"] for r in rows)/len(rows),2),
                "total_tokens":sum(r["tokens"] for r in rows)}
    am,bm=metrics(a),metrics(b)
    return {"status":"completed_exploratory","official_benchmark":False,
            "validation_examples":len(a),"samples_per_question":1,
            "sft":am,"cep":bm,
            "correctness_delta_cep_minus_sft":bm["correct"]-am["correct"],
            "tokens_delta_cep_minus_sft":bm["total_tokens"]-am["total_tokens"],
            "quality_preservation_demonstrated":False,
            "generalization_demonstrated":False}

def run(args,validation,out):
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA needed")
    for a in (args.sft,args.cep):
        if not (a/"adapter_config.json").is_file() or not list(a.glob("*.safetensors")):
            raise FileNotFoundError("missing adapter config or safetensors: "+str(a))
    if out.exists():
        raise FileExistsError("output already exists")
    tokenizer=AutoTokenizer.from_pretrained(BASE_MODEL,revision=BASE_REVISION,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(BASE_MODEL,revision=BASE_REVISION,
                                              local_files_only=True,dtype=torch.float16).to("cuda").eval()
    opening=tokenizer.convert_tokens_to_ids("<think>")
    closing=tokenizer.convert_tokens_to_ids("</think>")
    eos={int(tokenizer.eos_token_id)}
    ceos=model.generation_config.eos_token_id
    if isinstance(ceos,int):eos.add(ceos)
    elif isinstance(ceos,(tuple,list)):eos.update(int(x) for x in ceos)
    out.mkdir(parents=True,exist_ok=False)
    plan={"status":"running","official_benchmark":False,"train_source":"GSM8K/main/train",
          "validation_is_train_split_holdout":True,"model":BASE_MODEL,
          "model_revision":BASE_REVISION,"n":len(validation),"seed":SEED,
          "cap":args.cap,"sampling":SAMPLING,
          "sft_adapter":str(args.sft),"cep_adapter":str(args.cep)}
    (out/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    # Evaluate in two model phases to fit an 8 GB Pascal GPU; maintain order
    # by mapping back to per-question pairs when writing result JSONL.
    results={}
    for name,adapter in (("sft",args.sft),("cep",args.cep)):
        active=PeftModel.from_pretrained(model,str(adapter),is_trainable=False).eval()
        for i,row in enumerate(validation):
            inputs=tokenizer.apply_chat_template(row["prompt"],tokenize=True,add_generation_prompt=True,
                   enable_thinking=True,return_tensors="pt",return_dict=True).to("cuda")
            tail=tokenizer.decode(inputs["input_ids"][0][-32:].tolist(),skip_special_tokens=False)
            prefilled="<think>" in tail and "</think>" not in tail
            torch.manual_seed(SEED)
            torch.cuda.manual_seed_all(SEED)
            with torch.inference_mode():
                output=active.generate(**inputs,do_sample=True,max_new_tokens=args.cap,**SAMPLING)
            ids=output[0,inputs["input_ids"].shape[1]:].tolist()
            split=split_reasoning(ids,opening,closing,eos,prefilled)
            truncated=not ids or ids[-1] not in eos
            final=tokenizer.decode(split["final_ids"],skip_special_tokens=True)
            correct,error=(False,"truncated") if truncated else grade_final(final,row["gold_answer"],"number")
            results[(row["question_id"],name)]={"variant":name,"id":row["question_id"],
                "seed":SEED,"gold":row["gold_answer"],"tokens":len(ids),
                "reasoning_tokens":split["reasoning_tokens"],"final_tokens":split["final_tokens"],
                "truncated":truncated,"correct":correct,"error":error,
                "final_text":final,"generated_text":tokenizer.decode(ids,skip_special_tokens=False)}
            print(f'{name} {i+1}/{len(validation)} correct={correct} tokens={len(ids)}',flush=True)
        model=active.unload()
        del active
        torch.cuda.empty_cache()
    records=[results[(row["question_id"],name)] for row in validation for name in ("sft","cep")]
    summary=summarize(records)
    with (out/"records.jsonl").open("x") as f:
        for record in records:f.write(json.dumps(record,ensure_ascii=False)+"\n")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    return summary

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet",type=Path,default=Path("data/safe-start/raw/gsm8k-train.parquet"))
    p.add_argument("--eval-questions",type=Path,default=Path("questions/questions.jsonl"))
    p.add_argument("--sft",type=Path,default=Path("runs/rhar-training-003"))
    p.add_argument("--cep",type=Path,default=Path("runs/rhar-cep-pilot-001"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--count",type=int,default=20)
    p.add_argument("--cap",type=int,default=512)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run",action="store_true")
    mode.add_argument("--execute",action="store_true")
    p.add_argument("--approve-gpu",action="store_true")
    args=p.parse_args(argv)
    if args.execute!=args.approve_gpu or args.cap<128 or args.cap>2048:
        p.error("use --execute --approve-gpu (or --dry-run without approval); cap 128..2048")
    if not args.raw_parquet.is_file() or hashlib.sha256(args.raw_parquet.read_bytes()).hexdigest()!=TRAIN_SHA256:
        raise ValueError("verified pinned train parquet required")
    if not args.eval_questions.is_file():
        raise FileNotFoundError("evaluation prompts required for screening")
    train,val=prepare_pool(read_parquet(args.raw_parquet),1000,100,42)
    reject_overlap(train,val,read_eval_prompts(args.eval_questions))
    validation=pick_validation(read_parquet(args.raw_parquet),count=args.count)
    if args.dry_run:
        print(json.dumps({"status":"plan_only","n":len(validation),"planned_generations":2*len(validation),
          "seed":SEED,"cap":args.cap,"training_performed":False,"gpu_used":False,
          "official_benchmark":False,"validation_used_for_loss_in_prior_trainings":True,
          "train_and_validation_ids_disjoint":True,"first_id":validation[0]["question_id"]},indent=2))
        return 0
    run(args,validation,args.out)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
