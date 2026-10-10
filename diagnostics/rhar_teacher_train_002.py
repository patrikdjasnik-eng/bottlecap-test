"""Train RHAR LoRA on pinned GSM8K TRAIN reference solutions (not eval datasets).

Reference GSM8K rationales are supervised *teacher* data, NOT sampled Qwen
reasoning; source is restricted to the 12 previously audited train questions.
CPU preparation and explicit opt-in GPU training in one entrypoint.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .safe_start_generate import load_approved_inputs
from .safe_start_data import TRAIN_SHA256, DATASET_REVISION, parse_gold, read_parquet
from .safe_start_plan import build_prompt
from .reasoning_probe import BASE_MODEL, BASE_REVISION

def prepare(questions, parquet_rows, exclude_ids=()):
    excluded=set(exclude_ids)
    if not excluded <= {q["question_id"] for q in questions}:
        raise ValueError("unknown excluded ID")
    result=[]
    for q in questions:
        if q["question_id"] in excluded:
            continue
        if q["source"]!="gsm8k" or q["split"]!="train" or q["source_revision"]!=DATASET_REVISION:
            raise ValueError("unaudited source")
        match=re.fullmatch(r"gsm8k-train-(\d{5})",q["question_id"])
        if not match:
            raise ValueError("unrecognized train source index")
        row=parquet_rows[int(match.group(1))]
        if row["question"].strip()!=q["question"] or parse_gold(row["answer"])!=q["gold_answer"]:
            raise ValueError("dataset provenance/gold mismatch")
        answer=row["answer"]
        if answer.count("####")!=1:
            raise ValueError("invalid answer structure")
        reasoning=answer.split("####",1)[0].strip()
        reasoning=re.sub(r"<<[^<>\n]*>>","",reasoning).strip()
        if not reasoning or "<think>" in reasoning or "</think>" in reasoning:
            raise ValueError("invalid rationale")
        completion="<think>\n"+reasoning+"\n</think>\nFinal answer: "+q["gold_answer"]
        result.append({"question_id":q["question_id"],"source":"gsm8k",
                       "source_revision":DATASET_REVISION,"prompt":[{"role":"user","content":build_prompt(q["question"])}],
                       "completion":completion,"reference_solution":True})
    if not result:
        raise ValueError("no training examples")
    return result

def encode_teacher(row,tokenizer,max_length):
    prefix=tokenizer.apply_chat_template(row["prompt"],tokenize=True,add_generation_prompt=True,
                                        enable_thinking=True)
    if isinstance(prefix,dict):
        prefix=prefix["input_ids"]
    if prefix and isinstance(prefix[0],list):
        prefix=prefix[0]
    prefix=list(prefix)
    prefix_tail=tokenizer.decode(prefix[-8:],skip_special_tokens=False)
    text=row["completion"]
    if "<think>" in prefix_tail and "</think>" not in prefix_tail:
        # Qwen3 can prefill <think> in its chat template. Do not double it.
        text=text[len("<think>"):]
    body=tokenizer(text,add_special_tokens=False)["input_ids"]
    eos=tokenizer.eos_token_id
    if not prefix or not body or eos is None:
        raise ValueError("invalid tokenizer encoding")
    if body[-1]!=eos:
        body=list(body)+[int(eos)]
    if len(prefix)+len(body)>max_length:
        return None
    return {"input_ids":prefix+list(body),"attention_mask":[1]*(len(prefix)+len(body)),
            "labels":[-100]*len(prefix)+list(body)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet",type=Path,default=Path("data/safe-start/raw/gsm8k-train.parquet"))
    p.add_argument("--questions",type=Path,default=Path("data/safe-start/questions.jsonl"))
    p.add_argument("--selection",type=Path,default=Path("data/safe-start/selection-report.json"))
    p.add_argument("--audit",type=Path,default=Path("data/safe-start/overlap-audit.json"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--exclude-id",action="append",default=[])
    p.add_argument("--max-length",type=int,default=1024)
    p.add_argument("--max-steps",type=int,default=60)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run",action="store_true")
    mode.add_argument("--approve-training",action="store_true")
    args=p.parse_args(argv)
    if args.max_length<128 or args.max_steps<1:
        p.error("invalid training bounds")
    questions,_=load_approved_inputs(args.questions,args.selection,args.audit)
    raw=args.raw_parquet
    if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest()!=TRAIN_SHA256:
        raise ValueError("verified pinned GSM8K train parquet required; do not fetch eval data")
    rows=prepare(questions,read_parquet(raw),args.exclude_id)
    plan={"status":"plan_only" if args.dry_run else "training","model":BASE_MODEL,
          "model_revision":BASE_REVISION,"reference_training_examples":len(rows),
          "max_steps":args.max_steps,"max_length":args.max_length,
          "source":"gsm8k/main/train","train_parquet_sha256":TRAIN_SHA256,
          "eval_overlap_exhaustively_ruled_out":False,
          "training_performed":False,"gpu_used":False}
    if args.dry_run:
        print(json.dumps(plan,indent=2))
        return 0
    if args.out.exists():
        raise FileExistsError("refusing overwrite")
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,Trainer,TrainingArguments
    from peft import LoraConfig,get_peft_model
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required, no CPU fallback")
    tokenizer=AutoTokenizer.from_pretrained(BASE_MODEL,revision=BASE_REVISION,local_files_only=True)
    encoded=[encode_teacher(x,tokenizer,args.max_length) for x in rows]
    usable=[x for x in encoded if x is not None]
    if len(usable)<8:
        raise ValueError(f"only {len(usable)} samples fit max_length; need at least 8")
    model=AutoModelForCausalLM.from_pretrained(BASE_MODEL,revision=BASE_REVISION,
                                                local_files_only=True,dtype=torch.float16)
    model.config.use_cache=False
    model.gradient_checkpointing_enable()
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,
                                         bias="none",task_type="CAUSAL_LM",
                                         target_modules=["q_proj","v_proj"]))
    pad=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    def collate(batch):
        n=max(len(x["input_ids"]) for x in batch)
        return {key:torch.tensor([x[key]+[(-100 if key=="labels" else 0 if key=="attention_mask" else pad)]*(n-len(x[key])) for x in batch])
                for key in ("input_ids","attention_mask","labels")}
    training_args=TrainingArguments(output_dir=str(args.out),max_steps=args.max_steps,
                                   per_device_train_batch_size=1,gradient_accumulation_steps=4,
                                   learning_rate=8e-5,fp16=True,bf16=False,logging_steps=5,
                                   save_strategy="no",report_to="none",remove_unused_columns=False)
    trainer=Trainer(model=model,args=training_args,train_dataset=usable,data_collator=collate)
    trainer.train()
    args.out.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(args.out,safe_serialization=True)
    tokenizer.save_pretrained(args.out)
    (args.out/"training_metadata.json").write_text(json.dumps({**plan,"status":"completed",
        "training_performed":True,"gpu_used":True,"usable_examples":len(usable),
        "excluded_overlength":len(rows)-len(usable),"teacher_source":"GSM8K reference rationales",
        "official_benchmark":False},indent=2)+"\n")
    print("RHAR Training 002 adapter:",args.out,"usable samples:",len(usable))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
