"""RHAR Evaluation 001: strictly exploratory paired Transformers evaluation.

CPU-only --dry-run, opt-in CUDA execution. NOT BottleCapAI official evaluate.py.
Holdout questions are never training samples. Outputs are not official scores.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time

from .safe_start_plan import BASE_MODEL, BASE_REVISION
from .stress_test_003 import TASKS, task_prompt
from .reasoning_probe import split_reasoning
from .offline_selector import grade_final

SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
SEED = 9001
CAP = 512


def make_plan(adapter, task_index):
    if not 1 <= task_index <= len(TASKS):
        raise ValueError("task_index must be between 1 and 6")
    task = TASKS[task_index - 1]
    return {"status": "plan_only", "model": BASE_MODEL, "revision": BASE_REVISION,
            "adapter": str(adapter), "task_id": task["id"], "task_index": task_index,
            "task_sha256": hashlib.sha256(task_prompt(task).encode()).hexdigest(),
            "seed": SEED, "max_new_tokens": CAP, "sampling": SAMPLING,
            "planned_generations": 2, "thinking_enabled": True,
            "official_benchmark": False, "training_data_allowed": False,
            "training_performed": False, "gpu_used": False}


def summarize(records):
    if len(records) != 2 or [x["variant"] for x in records] != ["base", "adapter"]:
        raise ValueError("exactly base and adapter records required")
    base, candidate = records
    if (base["task_id"], base["seed"], base["budget"]) != (candidate["task_id"], candidate["seed"], candidate["budget"]):
        raise ValueError("unpaired records")
    diff = base["total_generated_tokens"] - candidate["total_generated_tokens"]
    return {"status": "completed_exploratory", "official_benchmark": False,
            "sample_count_per_variant": 1, "training_performed": False,
            "base": {"tokens": base["total_generated_tokens"], "correct": base["correct"],
                     "truncated": base["truncated"]},
            "adapter": {"tokens": candidate["total_generated_tokens"], "correct": candidate["correct"],
                        "truncated": candidate["truncated"]},
            "token_difference_base_minus_adapter": diff,
            "token_reduction_pct": round(100 * diff / base["total_generated_tokens"], 2)
                                   if base["total_generated_tokens"] else None,
            "quality_preservation_demonstrated": False,
            "generalization_demonstrated": False}


def execute(adapter, task_index, out):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no silent CPU fallback")
    if out.exists():
        raise FileExistsError("refusing overwrite: " + str(out))
    if not (adapter / "adapter_config.json").is_file() or not list(adapter.glob("*.safetensors")):
        raise ValueError("adapter config and safetensors are required")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, revision=BASE_REVISION, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, revision=BASE_REVISION,
                                                 dtype=torch.float16, local_files_only=True).to("cuda").eval()
    opening = tokenizer.convert_tokens_to_ids("<think>")
    closing = tokenizer.convert_tokens_to_ids("</think>")
    eos_ids = {int(tokenizer.eos_token_id)}
    eos_cfg = model.generation_config.eos_token_id
    if isinstance(eos_cfg, int):
        eos_ids.add(eos_cfg)
    elif isinstance(eos_cfg, (tuple, list)):
        eos_ids.update(map(int, eos_cfg))
    task = TASKS[task_index - 1]
    inputs = tokenizer.apply_chat_template(
        [{"role": "user", "content": task_prompt(task)}], tokenize=True,
        add_generation_prompt=True, enable_thinking=True,
        return_tensors="pt", return_dict=True).to("cuda")
    prompt_tail = tokenizer.decode(inputs["input_ids"][0][-32:].tolist(), skip_special_tokens=False)
    prefilled = "<think>" in prompt_tail and "</think>" not in prompt_tail
    out.mkdir(parents=True, exist_ok=False)
    (out/"plan.json").write_text(json.dumps(dict(make_plan(adapter,task_index),status="running",gpu_used=True,
                                started_utc=datetime.now(timezone.utc).isoformat()), indent=2)+"\n")
    def generate(active_model, variant):
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            output = active_model.generate(**inputs, do_sample=True, max_new_tokens=CAP, **SAMPLING)
        torch.cuda.synchronize()
        seconds = time.perf_counter() - start
        ids = output[0, inputs["input_ids"].shape[1]:].tolist()
        split = split_reasoning(ids, opening, closing, eos_ids, prefilled)
        truncated = not ids or ids[-1] not in eos_ids
        final = tokenizer.decode(split["final_ids"], skip_special_tokens=True)
        correct, error = ((False, "truncated") if truncated else grade_final(final,task["gold"],"number"))
        return {"variant": variant, "task_id": task["id"], "seed": SEED, "budget": CAP,
                "total_generated_tokens": len(ids), "reasoning_tokens": split["reasoning_tokens"],
                "final_tokens": split["final_tokens"], "split_status": split["split_status"],
                "truncated": truncated, "correct": correct, "grading_error": error,
                "seconds": round(seconds,3), "generated_text": tokenizer.decode(ids,skip_special_tokens=False),
                "final_text": final, "official_benchmark": False, "training_data_allowed": False}
    records = [generate(model, "base")]
    # PEFT normally shares the loaded backbone, avoiding a second model copy on 8 GB VRAM.
    model = PeftModel.from_pretrained(model, str(adapter), is_trainable=False).eval()
    records.append(generate(model, "adapter"))
    with (out/"records.jsonl").open("x",encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record,ensure_ascii=False)+"\n")
    result = summarize(records)
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run",action="store_true")
    mode.add_argument("--execute",action="store_true")
    p.add_argument("--approve-gpu-2",action="store_true")
    p.add_argument("--adapter",type=Path,required=True)
    p.add_argument("--task-index",type=int,default=2)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    if args.approve_gpu_2 != args.execute:
        p.error("execution requires --execute --approve-gpu-2; dry-run forbids approval flag")
    try:
        plan=make_plan(args.adapter,args.task_index)
    except ValueError as exc:
        p.error(str(exc))
    if args.dry_run:
        print(json.dumps(plan,indent=2))
        return 0
    if args.out.exists():
        p.error("output exists")
    execute(args.adapter,args.task_index,args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
