#!/usr/bin/env python3
"""Read-only Qwen3 reasoning diagnostic, NOT the official BottleCapAI benchmark.

No training, adapter, prompt-based shortening, or evaluation-suite questions.
PyTorch/Transformers are imported only when main() runs a real inference.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import statistics
import time

BASE_MODEL = "Qwen/Qwen3-0.6B"
BASE_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
SEED = 9001

# Hand-written diagnostic cases; NOT taken from SVAMP, MBPP+, BFCL, or IFEval.
CASES = [
    {"id": "arithmetic_apples", "category": "arithmetic", "answer": "43", "kind": "number",
     "question": "A store has 5 boxes with 12 apples in each. It sells 17 apples. How many remain?"},
    {"id": "logic_triangle", "category": "logic", "answer": "A", "kind": "choice",
     "question": ("Every triangle has three sides. A shape has exactly four sides. "
                  "Can the shape be a triangle? A. No. B. Yes. C. It depends.")},
    {"id": "code_output", "category": "code_comprehension", "answer": "9", "kind": "number",
     "question": ("What number does this Python function return when called with 4? "
                  "def f(x): return x * 2 + 1")},
    {"id": "math_seats", "category": "multistep_arithmetic", "answer": "35", "kind": "number",
     "question": ("A hall has 6 rows with 8 seats each. Thirteen seats are empty. "
                  "How many people are seated?")},
    {"id": "logic_order", "category": "logic", "answer": "C", "kind": "choice",
     "question": ("Anna is taller than Bob. Bob is taller than Clara. Who is shortest? "
                  "A. Anna. B. Bob. C. Clara.")},
    {"id": "code_loop", "category": "code_comprehension", "answer": "6", "kind": "number",
     "question": ("What does this Python code print?\n"
                  "total = 0\nfor n in [1, 2, 3]:\n    total += n\nprint(total)")},
]
FINAL_LINE = re.compile(r"^Final answer:[ \t]*([^\n]+?)[ \t]*$", re.MULTILINE)
NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")


def prompt_for(case):
    """Request only a parseable final answer, without suggesting a value or shorter reasoning."""
    return [{"role": "user", "content": (
        f'{case["question"]}\n\n'
        "On the last line, write 'Final answer:' followed by your answer."
    )}]


def split_reasoning(token_ids, open_id, close_id, eos_ids, prefilled_open=False):
    """Return token lengths; keep unknown/malformed reasoning as None, not zero.

    The counts include boundary marker tokens and EOS in final_tokens; hence
    reasoning_tokens + final_tokens == the total number of generated tokens.
    """
    ids = list(token_ids)
    opens = [i for i, token in enumerate(ids) if token == open_id]
    closes = [i for i, token in enumerate(ids) if token == close_id]
    if opens == [0] and len(closes) == 1 and closes[0] > 0:
        boundary = closes[0] + 1
        status = "generated_think_block"
        reasoning_body = ids[1:closes[0]]
    elif prefilled_open and not opens and len(closes) == 1:
        boundary = closes[0] + 1
        status = "prefilled_think_block"
        reasoning_body = ids[:closes[0]]
    else:
        if not opens and not closes:
            status = "missing_think_markers"
        elif not closes:
            status = "unclosed_think_block"
        else:
            status = "malformed_think_block"
        return {"reasoning_tokens": None, "final_tokens": None,
                "reasoning_body_ids": [], "final_ids": ids, "split_status": status}
    return {"reasoning_tokens": boundary, "final_tokens": len(ids) - boundary,
            "reasoning_body_ids": reasoning_body,
            "final_ids": ids[boundary:], "split_status": status}


def grade_answer(final_text, gold, kind, truncated):
    """Strict, deterministic check of small hand-written diagnostic questions."""
    if truncated:
        return False, "truncated"
    text = final_text.strip()
    matches = FINAL_LINE.findall(text)
    if not matches or not text.splitlines()[-1].startswith("Final answer:"):
        return False, "missing_or_trailing_final_answer"
    answer = matches[-1].strip()
    if kind == "choice":
        if not re.fullmatch(r"[A-Ca-c]", answer):
            return False, "invalid_choice_format"
        return answer.upper() == gold.upper(), None
    if kind == "number":
        if not NUMBER.fullmatch(answer) or not NUMBER.fullmatch(gold):
            return False, "invalid_number_format"
        try:
            return Decimal(answer.replace(",", "")) == Decimal(gold.replace(",", "")), None
        except InvalidOperation:
            return False, "invalid_number_format"
    raise ValueError(f"Unknown kind {kind!r}")


def repeated_fourgrams(text):
    """Exploratory text repetition indicator; NOT a benchmark or quality score."""
    words = re.findall(r"\b\w+\b", text.casefold())
    seen, duplicates = set(), 0
    for i in range(max(0, len(words) - 3)):
        fourgram = tuple(words[i:i + 4])
        if fourgram in seen:
            duplicates += 1
        seen.add(fourgram)
    return duplicates


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3, help="Number of cases, 1-6 (default 3)")
    parser.add_argument("--samples", type=int, default=1, help="Runs per case, 1-8 (default 1)")
    parser.add_argument("--max-new-tokens", type=int, default=512,
                        help="Generation cap (default 512; truncated output counts as incorrect)")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--out", type=Path, help="Output folder; cannot overwrite previous runs")
    parser.add_argument("--dry-run", action="store_true", help="Print settings/cases without loading a model")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= len(CASES):
        parser.error(f"--limit must be between 1 and {len(CASES)}")
    if not 1 <= args.samples <= 8:
        parser.error("--samples must be between 1 and 8")
    if not 1 <= args.max_new_tokens <= 4096:
        parser.error("--max-new-tokens must be between 1 and 4096")
    return args


def summary_of(records):
    """Descriptive local measures; do not mistake these for official accuracy."""
    valid = [x for x in records if x["correct"] is not None]
    split = [x for x in records if x["reasoning_tokens"] is not None]
    mean = lambda values: round(statistics.mean(values), 2) if values else None
    return {
        "responses": len(records),
        "correct_responses": sum(bool(x["correct"]) for x in valid),
        "exploratory_accuracy": mean([float(x["correct"]) for x in valid]),
        "reasoning_split_successes": len(split),
        "mean_total_tokens": mean([x["total_tokens"] for x in records]),
        "mean_reasoning_tokens": mean([x["reasoning_tokens"] for x in split]),
        "mean_final_tokens": mean([x["final_tokens"] for x in split]),
        "mean_seconds": mean([x["generation_seconds"] for x in records]),
        "mean_tokens_per_second": mean([x["tokens_per_second"] for x in records]),
        "official_benchmark": False,
    }


def main(argv=None):
    args = parse_args(argv)
    selected = CASES[:args.limit]
    config = {"model": BASE_MODEL, "revision": BASE_REVISION,
              "thinking_enabled": True, "sampling": SAMPLING, "seed": SEED,
              "samples": args.samples, "max_new_tokens": args.max_new_tokens,
              "device": args.device, "questions": [x["id"] for x in selected],
              "official_benchmark": False, "training_performed": False}
    if args.dry_run:
        print(json.dumps({"config": config, "cases": selected}, indent=2))
        return 0

    from .token_trace import build_token_trace
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available. Try --dry-run or inspect your PyTorch install.")
    device = torch.device(args.device)
    dtype = torch.float16 if args.device == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, revision=BASE_REVISION)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, revision=BASE_REVISION,
                                                dtype=dtype).to(device).eval()
    open_id = tokenizer.convert_tokens_to_ids("<think>")
    close_id = tokenizer.convert_tokens_to_ids("</think>")
    if not isinstance(open_id, int) or not isinstance(close_id, int) or open_id == close_id:
        raise RuntimeError("Tokenizer lacks recognized thinking markers")
    end_ids = {int(t) for t in [tokenizer.eos_token_id] if isinstance(t, int)}
    configured_eos = model.generation_config.eos_token_id
    if isinstance(configured_eos, int):
        end_ids.add(configured_eos)
    elif isinstance(configured_eos, (list, tuple)):
        end_ids.update(int(t) for t in configured_eos)

    output_folder = args.out or Path("runs") / "diagnostics" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if output_folder.exists():
        raise SystemExit(f"Output path already exists: {output_folder}. Set a new --out path.")
    output_folder.mkdir(parents=True)
    config["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    config["torch"] = torch.__version__
    config["gpu"] = torch.cuda.get_device_name(0) if args.device == "cuda" else "CPU"
    (output_folder / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    results = []
    with (output_folder / "records.jsonl").open("w", encoding="utf-8") as fp:
        for i, case in enumerate(selected):
            messages = prompt_for(case)
            inputs = tokenizer.apply_chat_template(messages, tokenize=True,
                                                   add_generation_prompt=True,
                                                   enable_thinking=True,
                                                   return_tensors="pt", return_dict=True).to(device)
            prompt_tail = tokenizer.decode(inputs["input_ids"][0][-12:].tolist(),
                                           skip_special_tokens=False)
            prefilled = "<think>" in prompt_tail and "</think>" not in prompt_tail
            for sample in range(args.samples):
                seed = SEED + i * 1000 + sample
                torch.manual_seed(seed)
                if args.device == "cuda":
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                started = time.perf_counter()
                with torch.inference_mode():
                    out = model.generate(**inputs, do_sample=True,
                                         max_new_tokens=args.max_new_tokens, **SAMPLING)
                if args.device == "cuda":
                    torch.cuda.synchronize()
                elapsed = time.perf_counter() - started
                ids = out[0, inputs["input_ids"].shape[1]:].tolist()
                split = split_reasoning(ids, open_id, close_id, end_ids, prefilled)
                terminal = bool(ids) and ids[-1] in end_ids
                truncated = not terminal  # also catches generation caps and malformed stops
                raw = tokenizer.decode(ids, skip_special_tokens=False)
                final = tokenizer.decode(split["final_ids"], skip_special_tokens=True)
                reason = tokenizer.decode(split["reasoning_body_ids"], skip_special_tokens=True)
                correct, error = grade_answer(final, case["answer"], case["kind"], truncated)
                rec = {"id": case["id"], "category": case["category"], "sample": sample,
                       "seed": seed, "expected": case["answer"], "correct": correct,
                       "grading_error": error, "split_status": split["split_status"],
                       "total_tokens": len(ids), "reasoning_tokens": split["reasoning_tokens"],
                       "final_tokens": split["final_tokens"], "truncated": truncated,
                       "generation_seconds": round(elapsed, 3),
                       "tokens_per_second": round(len(ids) / elapsed, 3) if elapsed else None,
                       "pytorch_allocated_gib": round(torch.cuda.memory_allocated() / 1024**3, 3)
                       if args.device == "cuda" else None,
                       "pytorch_peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3)
                       if args.device == "cuda" else None,
                       "repeated_reasoning_fourgrams": repeated_fourgrams(reason)
                       if split["reasoning_tokens"] is not None else None,
                       "final_text": final, "full_generated_text": raw,
                       "token_trace": build_token_trace(ids, tokenizer, raw,
                                                        model_revision=BASE_REVISION)}
                fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fp.flush()
                results.append(rec)
                print(f'{case["id"]} #{sample+1}: correct={correct} '
                      f'tokens={len(ids)} reasoning={split["reasoning_tokens"]} '
                      f'final={split["final_tokens"]} split={split["split_status"]} '
                      f'time={elapsed:.1f}s', flush=True)
    summary = summary_of(results)
    (output_folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("\nDiagnostic only — NOT an official BottleCapAI benchmark.")
    print(json.dumps(summary, indent=2))
    print(f"Saved to: {output_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
