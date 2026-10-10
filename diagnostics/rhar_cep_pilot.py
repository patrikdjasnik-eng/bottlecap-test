"""RHAR CEP pilot: evidence-aware token-weighted LoRA SFT.

Controlled intervention vs Training 003: identical data, hyperparameters,
and model; only per-token loss weights differ. This is a *heuristic* pilot,
not verified causal importance or a claimed new algorithm.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .safe_start_data import TRAIN_SHA256, read_parquet, read_eval_prompts
from .rhar_train_003 import prepare_pool, reject_overlap
from .rhar_teacher_train_002 import encode_teacher
from .reasoning_probe import BASE_MODEL, BASE_REVISION

NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?%?")
OPERATOR = re.compile(r"(?<!\w)(?:times|multiplied|divided|minus|plus|remaining|left|total|each|per|percent|fraction|twice|half|third)(?!\w)",re.I)
SYMBOL = re.compile(r"[×÷=*/+\-]")

def anchor_mask(completion,question):
    """Flag numerical quantities from source and explicit arithmetic relations.

    Token positions are aligned through the tokenizer offset map later.
    Pure lexical anchors: not a validity proof of mathematical operations.
    """
    spans=[]
    originals={m.group().replace(",","") for m in NUMBER.finditer(question)}
    for match in NUMBER.finditer(completion):
        if match.group().replace(",","") in originals:
            spans.append(match.span())
    for matcher in (OPERATOR,SYMBOL):
        spans.extend(m.span() for m in matcher.finditer(completion))
    return spans

def encode_cep(row,tokenizer,max_length,boost=2.0):
    result=encode_teacher(row,tokenizer,max_length)
    if result is None:
        return None
    # Offsets for target body (including any Qwen-prefilled <think> handling)
    prefix_size=sum(x == -100 for x in result["labels"])
    body_ids=result["input_ids"][prefix_size:]
    body_text=tokenizer.decode(body_ids,skip_special_tokens=False)
    encoded=tokenizer(body_text,add_special_tokens=False,return_offsets_mapping=True)
    # Retokenization may differ at boundaries; fail closed rather than silently
    # misalign supervision weights.
    if list(encoded["input_ids"]) != body_ids:
        raise ValueError("CEP token alignment mismatch")
    spans=anchor_mask(body_text,row["question"])
    weights=[0.0]*prefix_size
    for start,end in encoded["offset_mapping"]:
        important=any(start<b and end>a for a,b in spans)
        weights.append(boost if important else 1.0)
    if len(weights)!=len(result["labels"]):
        raise AssertionError("CEP weights length mismatch")
    return {**result,"loss_weights":weights}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-parquet",type=Path,default=Path("data/safe-start/raw/gsm8k-train.parquet"))
    p.add_argument("--eval-questions",type=Path,default=Path("questions/questions.jsonl"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--train-size",type=int,default=1000)
    p.add_argument("--val-size",type=int,default=100)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--max-length",type=int,default=1024)
    p.add_argument("--epochs",type=float,default=1.0)
    p.add_argument("--boost",type=float,default=2.0)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run",action="store_true")
    group.add_argument("--approve-training",action="store_true")
    args=p.parse_args(argv)
    if args.max_length<256 or not 0<args.epochs<=3 or not 1<=args.boost<=5:
        p.error("invalid length / epochs / boost")
    if not args.raw_parquet.is_file() or hashlib.sha256(args.raw_parquet.read_bytes()).hexdigest()!=TRAIN_SHA256:
        raise ValueError("pinned GSM8K train parquet SHA mismatch")
    if not args.eval_questions.is_file():
        raise FileNotFoundError("evaluation prompt corpus needed for screening")
    train,val=prepare_pool(read_parquet(args.raw_parquet),args.train_size,args.val_size,args.seed)
    prompts=read_eval_prompts(args.eval_questions)
    reject_overlap(train,val,prompts)
    plan={"status":"plan_only" if args.dry_run else "training",
          "method":"CEP lexical evidence-aware weighted CE pilot",
          "source":"pinned GSM8K train only", "base_model":BASE_MODEL,
          "train_count":len(train),"val_count":len(val),"seed":args.seed,
          "max_length":args.max_length,"epochs":args.epochs,"boost":args.boost,
          "eval_prompts_screened":len(prompts),"screen_not_exhaustive":True,
          "gpu_used":False,"training_performed":False}
    if args.dry_run:
        print(json.dumps(plan,indent=2));return 0
    if args.out.exists():
        raise FileExistsError("refuse to overwrite")
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments
    from peft import get_peft_model,LoraConfig
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    tokenizer=AutoTokenizer.from_pretrained(BASE_MODEL,revision=BASE_REVISION,local_files_only=True)
    tr=[encode_cep(x,tokenizer,args.max_length,args.boost) for x in train]
    va=[encode_teacher(x,tokenizer,args.max_length) for x in val]
    tr=[x for x in tr if x is not None]
    va=[x for x in va if x is not None]
    if len(tr)<max(8,int(args.train_size*.8)) or len(va)<8:
        raise ValueError("too many overlength examples")
    model=AutoModelForCausalLM.from_pretrained(BASE_MODEL,revision=BASE_REVISION,local_files_only=True,dtype=torch.float16)
    model.config.use_cache=False
    model.gradient_checkpointing_enable()
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,bias="none",
                                         task_type="CAUSAL_LM",target_modules=["q_proj","v_proj"]))
    pad=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    def collate(batch):
        n=max(len(x["input_ids"]) for x in batch)
        result={}
        for k in ("input_ids","attention_mask","labels"):
            fill=-100 if k=="labels" else 0 if k=="attention_mask" else pad
            result[k]=torch.tensor([x[k]+[fill]*(n-len(x[k])) for x in batch])
        if "loss_weights" in batch[0]:
            result["loss_weights"]=torch.tensor([x["loss_weights"]+[0.]*(n-len(x["loss_weights"])) for x in batch],dtype=torch.float)
        return result
    class WeightedTrainer(Trainer):
        def compute_loss(self,model,inputs,return_outputs=False,num_items_in_batch=None):
            weights=inputs.pop("loss_weights",None)
            if weights is None:
                return super().compute_loss(model,inputs,return_outputs=return_outputs,
                                            num_items_in_batch=num_items_in_batch)
            labels=inputs["labels"]
            output=model(**{k:v for k,v in inputs.items() if k!="labels"})
            logits=output.logits[:,:-1,:]
            targets=labels[:,1:]
            token_loss=F.cross_entropy(logits.float().reshape(-1,logits.shape[-1]),
                                       targets.reshape(-1),ignore_index=-100,reduction="none").reshape_as(targets)
            valid=(targets!=-100)
            active_weights=weights[:,1:].to(token_loss.device)*valid
            loss=(token_loss*active_weights).sum()/active_weights.sum().clamp_min(1.)
            return (loss,output) if return_outputs else loss
    config=TrainingArguments(output_dir=str(args.out),num_train_epochs=args.epochs,
       per_device_train_batch_size=1,per_device_eval_batch_size=1,gradient_accumulation_steps=4,
       learning_rate=5e-5,fp16=True,bf16=False,save_strategy="epoch",eval_strategy="epoch",
       logging_steps=20,save_total_limit=2,report_to="none",remove_unused_columns=False,seed=args.seed)
    trainer=WeightedTrainer(model=model,args=config,train_dataset=tr,eval_dataset=va,data_collator=collate)
    result=trainer.train()
    args.out.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(args.out,safe_serialization=True)
    tokenizer.save_pretrained(args.out)
    metrics=trainer.evaluate()
    (args.out/"training_metadata.json").write_text(json.dumps({
        **plan,"status":"completed","gpu_used":True,"training_performed":True,
        "train_usable":len(tr),"validation_usable":len(va),
        "train_loss":result.training_loss,"evaluation_metrics":metrics,
        "causal_importance_verified":False,"official_benchmark":False},indent=2)+"\n")
    print("CEP pilot adapter:",args.out)
    print(json.dumps(metrics,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
