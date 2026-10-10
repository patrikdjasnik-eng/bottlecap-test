"""RHAR Training 003: scalable pinned GSM8K-train SFT with validation.

Only locally cached, SHA-256 pinned GSM8K train data. CPU dry-run; CUDA training
requires explicit --approve-training. Never uses official evaluation questions
for labels or training. Holdout split here is TRAIN-internal validation.
"""
import argparse
import hashlib
import json
import random
import re
from pathlib import Path

from .safe_start_data import (DATASET_REVISION, TRAIN_SHA256, parse_gold,
                              normalize_question, read_parquet)
from .safe_start_plan import build_prompt
from .reasoning_probe import BASE_MODEL, BASE_REVISION
from .rhar_teacher_train_002 import encode_teacher

def prepare_pool(source_rows, n_train=1000, n_val=100, seed=42):
    if n_train < 8 or n_val < 8 or n_train+n_val > len(source_rows):
        raise ValueError("train >=8, val >=8, total within dataset required")
    valid=[]
    used=set()
    for idx,row in enumerate(source_rows):
        question=row.get("question")
        if not isinstance(question,str) or not question.strip() or "final answer:" in question.casefold():
            continue
        try:
            gold=parse_gold(row.get("answer"))
        except ValueError:
            continue
        rationale=row["answer"].split("####",1)[0].strip()
        rationale=re.sub(r"<<[^<>\n]*>>","",rationale).strip()
        if not rationale or "<think>" in rationale or "</think>" in rationale:
            continue
        key=normalize_question(question)
        if key in used:
            continue
        used.add(key)
        valid.append({"question_id":f"gsm8k-train-{idx:05d}",
                      "question":question.strip(), "gold_answer":gold,
                      "prompt":[{"role":"user","content":build_prompt(question)}],
                      "completion":"<think>\n"+rationale+"\n</think>\nFinal answer: "+gold})
    rng=random.Random(seed)
    rng.shuffle(valid)
    if len(valid)<n_train+n_val:
        raise ValueError("insufficient valid nonduplicate data")
    train=valid[:n_train]
    validation=valid[n_train:n_train+n_val]
    assert not ({x["question_id"] for x in train}&{x["question_id"] for x in validation})
    return train,validation

def reject_overlap(train, validation, audit_questions):
    # Screen against the available local official prompt corpus, where present.
    from .safe_start_data import normalize_question, close_match
    normalized=[normalize_question(q) for q in audit_questions]
    # Exact matches first; only near-sized texts with shared vocabulary merit
    # expensive near-duplicate scoring. This remains heuristic, not exhaustive.
    exact=set(normalized)
    index={}
    for j,q in enumerate(normalized):
        for word in set(q.split()):
            if len(word)>4:
                index.setdefault(word,set()).add(j)
    for row in train+validation:
        current=normalize_question(row["question"])
        if current in exact:
            raise ValueError("exact evaluation prompt overlap: "+row["question_id"])
        candidates=set()
        for word in set(current.split()):
            if len(word)>4:
                candidates.update(index.get(word,()))
        for j in candidates:
            other=normalized[j]
            if min(len(current),len(other))/max(len(current),len(other)) < 0.75:
                continue
            if close_match(current,other):
                raise ValueError("possible evaluation prompt overlap: "+row["question_id"])

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet",type=Path,default=Path("data/safe-start/raw/gsm8k-train.parquet"))
    p.add_argument("--eval-questions",type=Path,default=Path("questions/questions.jsonl"))
    p.add_argument("--train-size",type=int,default=1000)
    p.add_argument("--val-size",type=int,default=100)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--max-length",type=int,default=1024)
    p.add_argument("--epochs",type=float,default=1.0)
    p.add_argument("--out",type=Path,required=True)
    flags=p.add_mutually_exclusive_group(required=True)
    flags.add_argument("--dry-run",action="store_true")
    flags.add_argument("--approve-training",action="store_true")
    args=p.parse_args(argv)
    if args.max_length<256 or not 0<args.epochs<=3:
        p.error("invalid sequence length or epochs")
    if not args.raw_parquet.is_file():
        raise FileNotFoundError("local GSM8K train parquet missing")
    if hashlib.sha256(args.raw_parquet.read_bytes()).hexdigest()!=TRAIN_SHA256:
        raise ValueError("GSM8K training file SHA mismatch")
    if not args.eval_questions.is_file():
        raise FileNotFoundError("local evaluation prompts needed for overlap screen")
    from .safe_start_data import read_eval_prompts
    eval_prompts=read_eval_prompts(args.eval_questions)
    raw=read_parquet(args.raw_parquet)
    train,val=prepare_pool(raw,args.train_size,args.val_size,args.seed)
    # Local evaluation prompts are used ONLY for contamination screening.
    reject_overlap(train,val,eval_prompts)
    plan={"status":"plan_only" if args.dry_run else "training",
          "model":BASE_MODEL,"revision":BASE_REVISION,
          "source":"gsm8k/main/train","source_revision":DATASET_REVISION,
          "source_sha256":TRAIN_SHA256,"train_count":len(train),
          "validation_count":len(val),"seed":args.seed,"epochs":args.epochs,
          "max_length":args.max_length,"screened_eval_prompts":len(eval_prompts),
          "heuristic_screen_only":True,
          "gpu_used":False,"training_performed":False,"official_benchmark":False}
    if args.dry_run:
        print(json.dumps(plan,indent=2))
        return 0
    if args.out.exists():
        raise FileExistsError("refusing to overwrite existing training run")
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments
    from peft import get_peft_model,LoraConfig
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    tokenizer=AutoTokenizer.from_pretrained(BASE_MODEL,revision=BASE_REVISION,local_files_only=True)
    etrain=[encode_teacher(x,tokenizer,args.max_length) for x in train]
    evals=[encode_teacher(x,tokenizer,args.max_length) for x in val]
    train_encoded=[x for x in etrain if x is not None]
    val_encoded=[x for x in evals if x is not None]
    if len(train_encoded)<max(8,int(args.train_size*0.8)) or len(val_encoded)<8:
        raise ValueError("too many overlength examples")
    model=AutoModelForCausalLM.from_pretrained(BASE_MODEL,revision=BASE_REVISION,
                                               local_files_only=True,dtype=torch.float16)
    model.config.use_cache=False
    model.gradient_checkpointing_enable()
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,bias="none",
                                         task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"]))
    pad=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    def collate(batch):
        n=max(len(x["input_ids"]) for x in batch)
        return {k:torch.tensor([x[k]+[(-100 if k=="labels" else 0 if k=="attention_mask" else pad)]*(n-len(x[k])) for x in batch])
                for k in ("input_ids","attention_mask","labels")}
    args_train=TrainingArguments(output_dir=str(args.out),num_train_epochs=args.epochs,
       per_device_train_batch_size=1,per_device_eval_batch_size=1,gradient_accumulation_steps=4,
       learning_rate=5e-5,fp16=True,bf16=False,save_strategy="epoch",eval_strategy="epoch",
       logging_steps=20,save_total_limit=2,report_to="none",remove_unused_columns=False,
       seed=args.seed)
    trainer=Trainer(model=model,args=args_train,train_dataset=train_encoded,
                    eval_dataset=val_encoded,data_collator=collate)
    result=trainer.train()
    args.out.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(args.out,safe_serialization=True)
    tokenizer.save_pretrained(args.out)
    metrics=trainer.evaluate()
    (args.out/"training_metadata.json").write_text(json.dumps({
       **plan,"status":"completed","training_performed":True,"gpu_used":True,
       "train_usable":len(train_encoded),"validation_usable":len(val_encoded),
       "train_loss":result.training_loss,"evaluation_metrics":metrics,
       "training_method":"LoRA SFT on GSM8K reference rationales",
       "official_benchmark":False},indent=2)+"\n")
    print("RHAR Training 003 adapter:",args.out)
    print(json.dumps(metrics,indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
