"""RHAR Safe Start: gated 36-response Qwen3 pilot, NOT an authorization to run GPU.

--dry-run is CPU-only and imports no model libraries. GPU execution requires
separate approval and BOTH explicit flags. No training or official evaluation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import time

from .offline_selector import grade_final
from .reasoning_probe import repeated_fourgrams, split_reasoning
from .safe_start_overlap import SOURCES, verify_selection
from .safe_start_plan import (
    BASE_MODEL, BASE_REVISION, MAX_NEW_TOKENS, SEEDS, build_prompt, plan_attempts,
)

DEFAULT_QUESTIONS = Path("data/safe-start/questions.jsonl")
DEFAULT_SELECTION = Path("data/safe-start/selection-report.json")
DEFAULT_AUDIT = Path("data/safe-start/overlap-audit.json")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            digest.update(part)
    return digest.hexdigest()


def verify_audit(report, questions, hashes):
    """Refuse invalid/partial audit evidence; this is not a semantic guarantee."""
    expected = {src["name"]: src for src in SOURCES}
    sources = report.get("sources")
    if (report.get("status") != "review_only"
            or report.get("audit_type") != "heuristic_text_overlap_screen"
            or report.get("audit_result") != "no_matches_in_screened_sources"
            or report.get("training_approved") is not False
            or report.get("screened_all_declared_sources") is not True
            or report.get("screened_source_count") != len(SOURCES)
            or set(report.get("screened_families", [])) != {"SVAMP", "MBPP+", "BFCL", "IFEval"}
            or report.get("question_count") != len(questions)
            or report.get("question_ids") != [q["question_id"] for q in questions]
            or report.get("question_sha256") != hashes
            or report.get("dataset_revision") != questions[0]["source_revision"]
            or report.get("potential_match_count") != 0
            or report.get("potential_matches") != []
            or report.get("overlap_audit_exhaustive") is not False
            or report.get("semantic_paraphrases_ruled_out") is not False
            or report.get("original_candidate_files_modified") is not False
            or not isinstance(sources, list) or len(sources) != len(SOURCES)):
        raise ValueError("untrusted or incomplete evaluation overlap audit")
    seen = set()
    for item in sources:
        if not isinstance(item, dict) or item.get("name") in seen:
            raise ValueError("duplicate or malformed evaluation source")
        name = item.get("name")
        pin = expected.get(name)
        if (pin is None or item.get("family") != pin["family"]
                or item.get("url") != pin["url"]
                or item.get("known_sha256_pin_checked") is not ("expected_sha256" in pin)
                or type(item.get("prompt_count")) is not int or item["prompt_count"] < 1
                or not isinstance(item.get("sha256_of_decoded_bytes"), str)
                or re.fullmatch(r"[0-9a-f]{64}", item["sha256_of_decoded_bytes"]) is None):
            raise ValueError("incorrect pinned evaluation metadata")
        if ("expected_sha256" in pin and
                item["sha256_of_decoded_bytes"] != pin["expected_sha256"]):
            raise ValueError("evaluation source hash mismatch")
        seen.add(name)
    if (seen != set(expected) or
            report.get("screened_prompt_count") != sum(x["prompt_count"] for x in sources)):
        raise ValueError("incomplete evaluation source coverage")
    return True


def load_approved_inputs(questions_path, selection_path, audit_path):
    """Validate pre-existing review inputs; does NOT approve GPU or training."""
    questions, hashes = verify_selection(questions_path, selection_path)
    with Path(audit_path).open(encoding="utf-8") as stream:
        audit = json.load(stream)
    verify_audit(audit, questions, hashes)
    return questions, plan_attempts(questions)


def pilot_three(questions, attempts, question_index=1):
    """One audited question, all three original seeds; retain full-file audit."""
    if len(questions) != 12 or len(attempts) != 36:
        raise ValueError("pilot requires the complete audited 12x3 plan")
    if type(question_index) is not int or not 1 <= question_index <= 12:
        raise ValueError("question_index must be in range 1..12")
    chosen = [questions[question_index - 1]]
    selected = [a for a in attempts if a["question_id"] == chosen[0]["question_id"]]
    if len(selected) != 3 or [a["seed"] for a in selected] != list(SEEDS):
        raise ValueError("pilot seed or attempt mismatch")
    return chosen, selected


def planned_config(questions, attempts, paths):
    return {
        "status": "plan_only", "model": BASE_MODEL, "model_revision": BASE_REVISION,
        "thinking_enabled": True, "question_count": len(questions),
        "planned_generations": len(attempts), "seeds": list(SEEDS),
        "sampling": attempts[0]["sampling"], "max_new_tokens": MAX_NEW_TOKENS,
        "question_ids": [q["question_id"] for q in questions],
        "input_sha256": {label: sha256_file(path) for label, path in paths.items()},
        "gpu_used": False, "model_loaded": False, "model_downloaded": False,
        "training_performed": False, "training_approved": False,
        "official_benchmark": False, "model_generations_performed": 0,
        "research_only": True,
    }


def summarize(records):
    """Exploratory counts only; no token-saving or official-accuracy claim."""
    mean = lambda values: round(statistics.mean(values), 3) if values else None
    known = [r for r in records if r["reasoning_tokens"] is not None]
    return {
        "status": "completed", "responses": len(records),
        "correct_responses": sum(r["correct"] for r in records),
        "complete_terminations": sum(not r["truncated"] for r in records),
        "valid_reasoning_splits": len(known),
        "mean_total_generated_tokens": mean([r["total_generated_tokens"] for r in records]),
        "mean_reasoning_tokens_known_splits_only": mean([r["reasoning_tokens"] for r in known]),
        "mean_final_tokens_known_splits_only": mean([r["final_tokens"] for r in known]),
        "mean_generation_seconds": mean([r["generation_seconds"] for r in records]),
        "training_performed": False, "training_approved": False,
        "official_benchmark": False, "model_updated": False,
        "token_savings_demonstrated": False,
    }


def build_record(row, attempt, ids, open_id, close_id, eos_ids,
                 prefilled_open, tokenizer, seconds):
    """Exact generated-token accounting and strict numeric answer grading."""
    tokens = [int(i) for i in ids]
    if not tokens or not eos_ids:
        raise ValueError("empty generation or missing EOS ids")
    split = split_reasoning(tokens, open_id, close_id, eos_ids, prefilled_open)
    total = len(tokens)
    if (split["reasoning_tokens"] is not None and
            split["reasoning_tokens"] + split["final_tokens"] != total):
        raise ValueError("reasoning+final must equal all generated tokens")
    truncated = tokens[-1] not in eos_ids
    raw = tokenizer.decode(tokens, skip_special_tokens=False)
    final = tokenizer.decode(split["final_ids"], skip_special_tokens=True)
    reason = tokenizer.decode(split["reasoning_body_ids"], skip_special_tokens=True)
    correct, error = ((False, "truncated") if truncated
                      else grade_final(final, row["gold_answer"], "number"))
    return {
        "question_id": row["question_id"], "source": row["source"],
        "source_revision": row["source_revision"], "split": row["split"],
        "task": row["task"], "gold_answer": row["gold_answer"],
        "sample": attempt["sample"], "seed": attempt["seed"],
        "model": attempt["model"], "model_revision": attempt["model_revision"],
        "thinking_enabled": True, "prompt_hash": attempt["prompt_hash"],
        "sampling": attempt["sampling"], "max_new_tokens": attempt["max_new_tokens"],
        "generated_text": raw, "final_text": final,
        "correct": correct, "grading_error": error, "truncated": truncated,
        "reasoning_split_status": split["split_status"],
        "total_generated_tokens": total,
        "reasoning_tokens": split["reasoning_tokens"], "final_tokens": split["final_tokens"],
        "repeated_reasoning_fourgrams": (
            repeated_fourgrams(reason) if split["reasoning_tokens"] is not None else None),
        "generation_seconds": round(seconds, 3),
        "tokens_per_second": round(total / seconds, 3) if seconds > 0 else None,
        "training_approved": False, "research_only": True,
    }


def thinking_ids(tokenizer):
    open_id = tokenizer.convert_tokens_to_ids("<think>")
    close_id = tokenizer.convert_tokens_to_ids("</think>")
    unknown = tokenizer.unk_token_id
    if (not isinstance(open_id, int) or not isinstance(close_id, int)
            or open_id == close_id
            or (unknown is not None and (open_id == unknown or close_id == unknown))):
        raise RuntimeError("tokenizer thinking marker IDs are unavailable")
    return open_id, close_id


def execute(questions, attempts, config, output):
    """Only called after two CLI confirmation flags and separate user approval."""
    import torch  # deliberately lazy: --dry-run never imports torch/transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no automatic CPU fallback")
    device = torch.device("cuda")
    # The previously cached model only; do not fetch weights without approval.
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION, dtype=torch.float16,
        local_files_only=True).to(device).eval()
    open_id, close_id = thinking_ids(tokenizer)
    eos_ids = {int(t) for t in [tokenizer.eos_token_id] if isinstance(t, int)}
    configured_eos = model.generation_config.eos_token_id
    if isinstance(configured_eos, int):
        eos_ids.add(configured_eos)
    elif isinstance(configured_eos, (list, tuple)):
        eos_ids.update(int(t) for t in configured_eos)
    if not eos_ids:
        raise RuntimeError("EOS ids missing; cannot verify response termination")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True, exist_ok=False)
    config.update({"status": "running", "gpu_used": True, "model_loaded": True,
                   "device": str(device), "dtype": "float16",
                   "started_utc": datetime.now(timezone.utc).isoformat()})
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    by_id = {q["question_id"]: q for q in questions}
    records = []
    with (output / "records.jsonl").open("x", encoding="utf-8") as fp:
        for attempt in attempts:
            row = by_id[attempt["question_id"]]
            messages = [{"role": "user", "content": build_prompt(row["question"])}]
            inputs = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                enable_thinking=True, return_tensors="pt", return_dict=True).to(device)
            tail = tokenizer.decode(inputs["input_ids"][0][-32:].tolist(),
                                    skip_special_tokens=False)
            prefilled = "<think>" in tail and "</think>" not in tail
            torch.manual_seed(attempt["seed"])
            torch.cuda.manual_seed_all(attempt["seed"])
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.inference_mode():
                result = model.generate(**inputs, do_sample=True,
                    max_new_tokens=MAX_NEW_TOKENS, **attempt["sampling"])
            torch.cuda.synchronize()
            seconds = time.perf_counter() - started
            token_ids = result[0, inputs["input_ids"].shape[1]:].tolist()
            record = build_record(row, attempt, token_ids, open_id, close_id,
                                  eos_ids, prefilled, tokenizer, seconds)
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            fp.flush()
            records.append(record)
            print(f"{record['question_id']} seed={record['seed']}: "
                  f"correct={record['correct']} total={record['total_generated_tokens']} "
                  f"reasoning={record['reasoning_tokens']} truncated={record['truncated']}",
                  flush=True)
    overview = summarize(records)
    if overview["responses"] != config["planned_generations"]:
        raise RuntimeError("generated record count differs from approved plan")
    (output / "summary.json").write_text(json.dumps(overview, indent=2) + "\n",
                                          encoding="utf-8")
    print(json.dumps(overview, indent=2))
    return overview


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="CPU only, no model imports")
    mode.add_argument("--execute", action="store_true", help="NOT authorized yet")
    parser.add_argument("--question-index", type=int, default=1,
                        help="1-based audited question position for --pilot-3 (1..12)")
    parser.add_argument("--pilot-3", action="store_true",
                        help="Audit all 12 questions, plan only first question x three seeds")
    parser.add_argument("--confirm-gpu-3", action="store_true",
                        help="Explicit GPU consent for --pilot-3 (only with --execute)")
    parser.add_argument("--confirm-gpu-36", action="store_true",
                        help="Second explicit consent gate for 36 GPU generations")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--selection-report", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--overlap-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.question_index <= 12:
        parser.error("--question-index must be between 1 and 12")
    if not args.pilot_3 and args.question_index != 1:
        parser.error("--question-index requires --pilot-3")
    if args.confirm_gpu_3 and (not args.execute or not args.pilot_3):
        parser.error("--confirm-gpu-3 requires --execute --pilot-3")
    if args.confirm_gpu_36 and (not args.execute or args.pilot_3):
        parser.error("--confirm-gpu-36 requires --execute without --pilot-3")
    if args.execute and args.pilot_3 and not args.confirm_gpu_3:
        parser.error("three-generation GPU pilot requires --confirm-gpu-3")
    if args.execute and not args.pilot_3 and not args.confirm_gpu_36:
        parser.error("36-generation GPU pilot requires --confirm-gpu-36")
    paths = {"questions": args.questions, "selection_report": args.selection_report,
             "overlap_audit": args.overlap_audit}
    questions, attempts = load_approved_inputs(*paths.values())
    config = planned_config(questions, attempts, paths)
    if args.pilot_3:
        questions, attempts = pilot_three(questions, attempts, args.question_index)
        config.update({"status": "plan_only", "question_count": 1,
                       "planned_generations": 3, "question_ids": [questions[0]["question_id"]],
                       "pilot_mode": "one_question_three_seeds",
                       "question_index": args.question_index,
                       "full_audit_question_count": 12,
                       "full_audit_attempt_count": 36})
    if args.dry_run:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return 0
    out = args.out or (Path("runs") / "safe-start" /
                       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if out.exists():
        raise SystemExit(f"Output path already exists: {out}")
    execute(questions, attempts, config, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
