"""RHAR 007: conservative offline token-boundary audit.

Retokenization is NOT proof of the original generated token IDs. Only exact
round-tripping token spans are counted; all estimates remain non-causal.
No model inference, training, GPU, network, or automatic early stopping.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .reasoning_checkpoint import analyze_record as checkpoint_record
from .reasoning_probe import BASE_MODEL, BASE_REVISION
from .reasoning_structure import THINK


def audit_record(record, tokenizer):
    result = checkpoint_record(record)
    raw = record["full_generated_text"]
    candidate = result["candidate_checkpoint"]
    output = {
        "id": record["id"],
        "checkpoint": candidate,
        "boundary_status": "no_checkpoint" if candidate is None else "unverified",
        "token_boundary_index": None,
        "retokenized_total": None,
        "recorded_total": record["total_tokens"],
        "retokenized_after_checkpoint": None,
        "potential_saved_tokens": None,
        "measured_token_savings": None,
        "original_token_ids_available": False,
        "early_stop_safety_verified": False,
    }
    if candidate is None:
        return output
    match = THINK.search(raw)
    if not match:
        return output
    checkpoint_end = match.start(1) + candidate["offset_end_char"]
    if not match.start(1) <= checkpoint_end <= match.end(1):
        output["boundary_status"] = "invalid_character_offset"
        return output
    encoded = tokenizer(raw, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = encoded["input_ids"], encoded["offset_mapping"]
    if len(ids) != len(offsets) or not all(len(pair) == 2 for pair in offsets):
        raise ValueError("invalid tokenizer offsets")
    if any(start < 0 or end < start or end > len(raw) for start, end in offsets):
        raise ValueError("invalid offset range")
    output["retokenized_total"] = len(ids)
    # The probe saved decoded text, not original token IDs. Retokenization may
    # split or merge tokens, even if the token count happens to match.
    if len(ids) != record["total_tokens"]:
        output["boundary_status"] = "retokenized_count_mismatch"
        return output
    # Special tokens can have zero-width offsets; fail closed on ambiguous spans.
    if any(start == end for start, end in offsets):
        output["boundary_status"] = "ambiguous_zero_width_offsets"
        return output
    if not offsets or offsets[0][0] != 0 or offsets[-1][1] != len(raw):
        output["boundary_status"] = "incomplete_offsets"
        return output
    if any(offsets[i][1] != offsets[i + 1][0] for i in range(len(offsets) - 1)):
        output["boundary_status"] = "noncontiguous_offsets"
        return output
    boundaries = [0] + [end for _, end in offsets]
    if checkpoint_end not in boundaries:
        output["boundary_status"] = "checkpoint_inside_token"
        return output
    index = boundaries.index(checkpoint_end)
    output["token_boundary_index"] = index
    output["retokenized_after_checkpoint"] = len(ids) - index
    output["boundary_status"] = "retokenized_boundary_only"
    return output


def audit_file(path, tokenizer):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(audit_record(json.loads(line), tokenizer))
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f"line {line_number}: {error}") from error
    if not rows:
        raise ValueError("empty input")
    return {"status": "rhar_007_review_only", "record_count": len(rows),
            "model": BASE_MODEL, "model_revision": BASE_REVISION,
            "token_savings_measured": False, "training_performed": False,
            "gpu_used": False, "records": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.out and args.out.resolve() == args.records.resolve():
        parser.error("output must differ from input")
    # Only the pinned cached tokenizer; never download a model.
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=BASE_REVISION,
        local_files_only=True, use_fast=True,
    )
    if not tokenizer.is_fast:
        raise RuntimeError("fast tokenizer with offset mapping required")
    report = audit_file(args.records, tokenizer)
    report["input_sha256"] = hashlib.sha256(args.records.read_bytes()).hexdigest()
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
