"""RHAR Stress Test 003: isolated, manually authored diagnostic tasks.

CPU --dry-run is non-mutating and imports no torch. GPU requires --execute,
--confirm-gpu-4 and a separately approved, exactly four-run task batch.
These six task prompts are diagnostic holdout data: NEVER training examples.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from .safe_start_plan import BASE_MODEL, BASE_REVISION
from .reasoning_probe import split_reasoning
from .offline_selector import grade_final

SEEDS = (9001, 9003)
BUDGETS = (512, 1024)
TASKS = (
    {"id": "rhar003-math-01", "category": "math", "gold": "20",
     "question": "A warehouse receives 240 devices. Exactly three eighths are reserved. Of the unreserved devices, 20% are defective and discarded. All remaining devices are sold in packs of six, with no leftovers. How many full packs are sold?"},
    {"id": "rhar003-math-02", "category": "math", "gold": "6",
     "question": "A delivery driver drives 180 km at 60 km/h and then 120 km at 40 km/h. A colleague claims the average speed is exactly 50 km/h. Ignoring stops, how many hours does the entire trip actually take? Give the number of hours, not the average speed."},
    {"id": "rhar003-logic-01", "category": "logic", "gold": "2",
     "question": "Four distinct tasks A, B, C, D must be completed in a strict sequence. Both A and B must precede C, and C must precede D. A and B may occur in either order. How many valid sequences are possible?"},
    {"id": "rhar003-logic-02", "category": "logic", "gold": "536",
     "question": "A three-digit lock code XYZ uses three distinct nonzero digits. X is exactly two greater than Y; Z is exactly twice Y; the sum X+Y+Z is 14. What is the three-digit code, as a number?"},
    {"id": "rhar003-trap-01", "category": "adversarial", "gold": "240",
     "question": "A product initially costs 250 crowns. Its price increases by 20%, then decreases by 20% from the new price. The seller says the changes cancel. What is the actual final price in crowns? Give only a numeric final answer."},
    {"id": "rhar003-trap-02", "category": "adversarial", "gold": "9",
     "question": "A keeper has 17 rabbits. During a storm, all except 9 rabbits escape. A visitor subtracts 9 from 17 to find the remaining animals. How many rabbits actually remain?"},
)
INSTRUCTION = "\n\nOn the last line, write 'Final answer:' followed by a single number."
def task_prompt(task):
    return task["question"] + INSTRUCTION


def validate_tasks():
    assert len(TASKS) == 6 and len({t["id"] for t in TASKS}) == 6
    assert [t["category"] for t in TASKS] == ["math", "math", "logic", "logic",
                                              "adversarial", "adversarial"]
    assert all(t["gold"].isdigit() and t["question"].strip() for t in TASKS)


def plan(index):
    validate_tasks()
    if type(index) is not int or not 1 <= index <= 6:
        raise ValueError("task index must be 1..6")
    task = TASKS[index - 1]
    return task, [{"seed": seed, "max_new_tokens": budget}
                  for budget in BUDGETS for seed in SEEDS]


def dry_config(index):
    task, attempts = plan(index)
    return {"status": "plan_only", "test": "RHAR Stress Test 003",
            "task_index": index, "task_id": task["id"], "category": task["category"],
            "task_sha256": hashlib.sha256(task_prompt(task).encode()).hexdigest(),
            "model": BASE_MODEL, "revision": BASE_REVISION,
            "seeds": list(SEEDS), "budgets": list(BUDGETS),
            "planned_generations": len(attempts), "sampling": {
                "temperature": 0.6, "top_p": 0.95, "top_k": 20},
            "training_data_allowed": False, "training_performed": False,
            "official_benchmark": False, "gpu_used": False,
            "model_generations_performed": 0}


def execute(task, attempts, config, output):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU fallback")
    if output.exists():
        raise FileExistsError("refusing to overwrite " + str(output))
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True,
        dtype=torch.float16).to("cuda").eval()
    open_id = tokenizer.convert_tokens_to_ids("<think>")
    close_id = tokenizer.convert_tokens_to_ids("</think>")
    eos = {int(tokenizer.eos_token_id)}
    cfg_eos = model.generation_config.eos_token_id
    if isinstance(cfg_eos, int):
        eos.add(cfg_eos)
    elif isinstance(cfg_eos, (list, tuple)):
        eos.update(int(x) for x in cfg_eos)
    output.mkdir(parents=True, exist_ok=False)
    config = dict(config, status="running", gpu_used=True,
                  started_utc=datetime.now(timezone.utc).isoformat())
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    results = []
    with (output / "records.jsonl").open("x", encoding="utf-8") as fp:
        for attempt in attempts:
            messages = [{"role": "user", "content": task_prompt(task)}]
            inputs = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                enable_thinking=True, return_tensors="pt", return_dict=True).to("cuda")
            tail = tokenizer.decode(inputs["input_ids"][0][-32:].tolist(),
                                    skip_special_tokens=False)
            prefilled = "<think>" in tail and "</think>" not in tail
            torch.manual_seed(attempt["seed"])
            torch.cuda.manual_seed_all(attempt["seed"])
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(
                    **inputs, do_sample=True,
                    temperature=0.6, top_p=0.95, top_k=20,
                    max_new_tokens=attempt["max_new_tokens"])
            torch.cuda.synchronize()
            duration = time.perf_counter() - start
            ids = generated[0, inputs["input_ids"].shape[1]:].tolist()
            split = split_reasoning(ids, open_id, close_id, eos, prefilled)
            truncated = not ids or ids[-1] not in eos
            raw = tokenizer.decode(ids, skip_special_tokens=False)
            final = tokenizer.decode(split["final_ids"], skip_special_tokens=True)
            correct, error = ((False, "truncated") if truncated
                              else grade_final(final, task["gold"], "number"))
            record = {"task_id": task["id"], "category": task["category"],
                      "seed": attempt["seed"], "budget": attempt["max_new_tokens"],
                      "correct": correct, "grading_error": error,
                      "truncated": truncated, "total_generated_tokens": len(ids),
                      "reasoning_tokens": split["reasoning_tokens"],
                      "final_tokens": split["final_tokens"],
                      "reasoning_split_status": split["split_status"],
                      "generation_seconds": round(duration, 3),
                      "generated_text": raw, "final_text": final,
                      "training_data_allowed": False,
                      "official_benchmark": False}
            if (record["reasoning_tokens"] is not None and
                record["reasoning_tokens"] + record["final_tokens"] != len(ids)):
                raise ValueError("token accounting mismatch")
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            fp.flush()
            results.append(record)
            print(f'{task["id"]} budget={attempt["max_new_tokens"]} seed={attempt["seed"]}: '
                  f'correct={correct} truncated={truncated} tokens={len(ids)}', flush=True)
    summary = {"status": "completed", "task_id": task["id"], "responses": len(results),
               "correct_responses": sum(x["correct"] for x in results),
               "complete_responses": sum(not x["truncated"] for x in results),
               "training_performed": False, "training_data_allowed": False,
               "official_benchmark": False}
    if len(results) != 4:
        raise RuntimeError("incomplete four-run batch")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--task-index", type=int, required=True)
    parser.add_argument("--confirm-gpu-4", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.confirm_gpu_4 and not args.execute:
        parser.error("GPU approval flag is invalid in dry-run")
    if args.execute and not args.confirm_gpu_4:
        parser.error("GPU execution requires --confirm-gpu-4")
    try:
        task, attempts = plan(args.task_index)
    except ValueError as exc:
        parser.error(str(exc))
    cfg = dry_config(args.task_index)
    if args.dry_run:
        print(json.dumps(cfg, indent=2))
        return 0
    out = args.out or Path("runs") / ("stress-003-task-" + str(args.task_index))
    if out.exists():
        parser.error("output exists; refusing overwrite")
    execute(task, attempts, cfg, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
