"""RHAR first LoRA SFT pilot. Explicit opt-in; never auto-starts training.

Input: training_candidates.py JSON report from permitted training rollouts.
Does not use BottleCapAI evaluation questions.
"""
import argparse
import json
from pathlib import Path


def encode_example(row, tokenizer, max_length):
    prompt = row["prompt"]
    completion = row["completion"]
    prefix = tokenizer.apply_chat_template(
        prompt, tokenize=True, add_generation_prompt=True, enable_thinking=True
    )
    if isinstance(prefix, dict):
        prefix = prefix["input_ids"]
    if prefix and isinstance(prefix[0], list):
        prefix = prefix[0]
    prefix = list(prefix)
    body = tokenizer(completion, add_special_tokens=False)["input_ids"]
    if body and isinstance(body[0], list):
        body = body[0]
    if not prefix or not body or len(prefix) + len(body) > max_length:
        raise ValueError("empty or overlength training sample; no truncation allowed")
    return {"input_ids": prefix + list(body),
            "attention_mask": [1] * (len(prefix) + len(body)),
            "labels": [-100] * len(prefix) + list(body)}


def load_candidates(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("status") != "training_data_candidates_only":
        raise ValueError("training candidate report required")
    rows = report.get("selected")
    if not isinstance(rows, list) or not rows:
        raise ValueError("at least one validated training candidate required")
    if report.get("selected_count") != len(rows):
        raise ValueError("training candidate count mismatch")
    return rows


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-length", type=int, default=1024)
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--approve-training", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.max_length < 64 or args.max_steps < 1:
        raise ValueError("invalid training bounds")
    rows = load_candidates(args.candidates)
    plan = {"source": str(args.candidates), "samples": len(rows),
            "max_length": args.max_length, "max_steps": args.max_steps,
            "lora_rank": 8, "model": "Qwen/Qwen3-0.6B",
            "training_performed": False}
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    if not args.approve_training:
        raise SystemExit("Refusing to train: pass --approve-training explicitly")
    if args.out.exists():
        raise SystemExit("Refusing to overwrite existing output")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from .reasoning_probe import BASE_MODEL, BASE_REVISION

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA device required for the pilot")
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True
    )
    encoded = [encode_example(row, tokenizer, args.max_length) for row in rows]
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True,
        dtype=torch.float16
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM", target_modules=["q_proj", "v_proj"]
    ))
    pad = tokenizer.pad_token_id
    if pad is None:
        pad = tokenizer.eos_token_id
    if pad is None:
        raise RuntimeError("tokenizer has no padding token")
    def collate(batch):
        length = max(len(x["input_ids"]) for x in batch)
        return {k: torch.tensor([x[k] + [(-100 if k == "labels" else
                                        0 if k == "attention_mask" else pad)] *
                                (length - len(x[k])) for x in batch])
                for k in ("input_ids", "attention_mask", "labels")}
    settings = TrainingArguments(
        output_dir=str(args.out), max_steps=args.max_steps,
        per_device_train_batch_size=1, gradient_accumulation_steps=4,
        learning_rate=1e-4, fp16=True, bf16=False,
        logging_steps=1, save_strategy="no",
        report_to="none", remove_unused_columns=False
    )
    trainer = Trainer(model=model, args=settings,
                      train_dataset=encoded, data_collator=collate)
    trainer.train()
    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out, safe_serialization=True)
    tokenizer.save_pretrained(args.out)
    (args.out / "pilot_metadata.json").write_text(
        json.dumps({**plan, "training_performed": True}, indent=2) + "\n",
        encoding="utf-8"
    )
    print("Pilot adapter saved:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
