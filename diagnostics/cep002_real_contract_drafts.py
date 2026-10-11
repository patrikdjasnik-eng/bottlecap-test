"""CEP-002: three source-pinned GSM8K contract DRAFTS for manual review.

These hand-derived arithmetic relations are NOT independently reviewed,
training-approved, model generations, or VPS-locked experiences.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from .cep002_cpu import CandidateTrace, StepRule, TaskContract, parse_expression, verify
from .safe_start_data import DATASET_REVISION

DRAFT_SPECS = (
    {
        "question_id": "gsm8k-train-00664",
        "question_sha256": "12dd1a6e1986019e24e1a772c753cfb0b3791579524273a92302207e9775bc28",
        "gold_answer": "12",
        "facts": {"hamster_years": "2.5", "dog_multiplier": "4", "fish_extra": "2"},
        "steps": (("dog_years", "hamster_years * dog_multiplier", "10"),
                  ("fish_years", "dog_years + fish_extra", "12")),
        "final_target": "fish_years",
        "semantic_note": "Fish lifespan is two years greater than dog lifespan; dog lifespan is four times hamster lifespan.",
    },
    {
        "question_id": "gsm8k-train-06718",
        "question_sha256": "636c4c0e11c6af1b92b1ff0d7f976b0f0a8297a402610927aeb6a0db0283dbf3",
        "gold_answer": "7",
        "facts": {"rose_num": "1", "rose_den": "3", "jasmine_num": "1",
                  "jasmine_den": "4", "daily_num": "1", "daily_den": "12"},
        "steps": (("common_den", "rose_den * jasmine_den", "12"),
                  ("rose_units", "rose_num * jasmine_den", "4"),
                  ("jasmine_units", "jasmine_num * rose_den", "3"),
                  ("total_units", "rose_units + jasmine_units", "7"),
                  ("daily_units", "daily_num * common_den / daily_den", "1"),
                  ("days", "total_units / daily_units", "7")),
        "final_target": "days",
        "semantic_note": "Shampoos are quantities of the same bottle volume; fractional quantities are converted to twelfths exactly.",
    },
    {
        "question_id": "gsm8k-train-03644",
        "question_sha256": "b64a96f1391e59f5979aa017c4b871a4cf3c1cdf46153379542d7746076696b3",
        "gold_answer": "3840",
        "facts": {"instagram": "240", "facebook": "500", "two": "2",
                  "three": "3", "youtube_extra": "510"},
        "steps": (("ig_fb", "instagram + facebook", "740"),
                  ("twitter", "ig_fb / two", "370"),
                  ("tiktok", "twitter * three", "1110"),
                  ("youtube", "tiktok + youtube_extra", "1620"),
                  ("all_followers", "ig_fb + twitter + tiktok + youtube", "3840")),
        "final_target": "all_followers",
        "semantic_note": "Sum account follower counts, not deduplicated human users; each platform count contributes separately.",
    },
)


def exact_calculation(node: ast.AST, values: dict[str, Fraction]) -> Fraction:
    """A separate exact-arithmetic check, limited to the parsed safe AST."""
    if isinstance(node, ast.Expression):
        return exact_calculation(node.body, values)
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise ValueError("undefined relation input: " + node.id)
        return values[node.id]
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return Fraction(node.value)
    if isinstance(node, ast.UnaryOp):
        value = exact_calculation(node.operand, values)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
    if isinstance(node, ast.BinOp):
        left = exact_calculation(node.left, values)
        right = exact_calculation(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("division by zero")
            return left / right
    raise ValueError("unsupported arithmetic")


def create_draft(record: dict, spec: dict) -> dict:
    expected_id = spec["question_id"]
    if not isinstance(record, dict) or record.get("question_id") != expected_id:
        raise ValueError("question ID/order differs from pinned candidates")
    question = record.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("missing original question")
    actual_digest = sha256(question.encode()).hexdigest()
    if (record.get("question_sha256") != spec["question_sha256"]
            or actual_digest != spec["question_sha256"]):
        raise ValueError("source question hash mismatch")
    if (record.get("gold_answer") != spec["gold_answer"]
            or record.get("source") != "gsm8k/main/train"
            or record.get("dataset_revision") != DATASET_REVISION
            or record.get("status") != "REVIEW_REQUIRED"
            or record.get("contract") is not None
            or record.get("approved_for_training") is not False):
        raise ValueError("source provenance or review gate mismatch")

    values = {key: Fraction(value) for key, value in spec["facts"].items()}
    for target, expression, expected in spec["steps"]:
        if target in values:
            raise ValueError("duplicate contract variable")
        value = exact_calculation(parse_expression(expression), values)
        if value != Fraction(expected):
            raise ValueError("independent arithmetic cross-check disagrees: " + target)
        values[target] = value
    if values[spec["final_target"]] != Fraction(spec["gold_answer"]):
        raise ValueError("contract disagrees with source gold")

    proposed_contract = TaskContract(
        task_id=expected_id,
        source="gsm8k/main/train",
        facts=spec["facts"],
        rules=tuple(StepRule(target, expression)
                    for target, expression, _ in spec["steps"]),
        final_target=spec["final_target"],
        gold_answer=spec["gold_answer"],
        reviewed_by="",
        overlap_screen_passed=False,
    )
    raw_trace = "\n".join(
        [f"{target} = {expression} => {expected}"
         for target, expression, expected in spec["steps"]]
        + [f"Final answer: {spec['gold_answer']}"]
    )
    candidate = CandidateTrace(
        candidate_id=expected_id + "-draft",
        task_id=expected_id,
        raw_text=raw_trace,
        completed=True,
        measured_tokens=None,
    )
    status = verify(proposed_contract, candidate).status
    if status != "UNVERIFIED":
        raise RuntimeError("draft mistakenly received a verified lock")

    return {
        "question_id": expected_id,
        "question_sha256": actual_digest,
        "source": "gsm8k/main/train",
        "source_revision": DATASET_REVISION,
        "gold_answer": spec["gold_answer"],
        "semantic_note_for_manual_review": spec["semantic_note"],
        "contract": asdict(proposed_contract),
        "suggested_trace": raw_trace,
        "exact_fraction_arithmetic_checked": True,
        "vps_status": status,
        "manual_semantic_review": "PENDING",
        "approved_for_training": False,
        "qwen_generated": False,
    }


def make_drafts(input_path: Path, output_path: Path, execute: bool) -> dict:
    if execute and output_path.exists():
        raise FileExistsError("refusing to overwrite prior review drafts")
    with input_path.open(encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    if len(records) < len(DRAFT_SPECS):
        raise ValueError("incomplete intake review file")
    drafts = [create_draft(records[i], spec) for i, spec in enumerate(DRAFT_SPECS)]
    report = {
        "status": "review_required" if execute else "plan_only",
        "source_intake": str(input_path),
        "draft_count": len(drafts),
        "arithmetic_crosschecks_passed": len(drafts),
        "locked_experiences": 0,
        "semantic_contracts_independently_reviewed": 0,
        "model_generations_performed": 0,
        "training_performed": False,
        "training_approved": False,
        "holdout_questions_accessed": False,
        "official_benchmark": False,
        "gpu_used": False,
    }
    if execute:
        output_path.mkdir(parents=True, exist_ok=False)
        with (output_path / "contract-drafts.jsonl").open("x", encoding="utf-8") as stream:
            for draft in drafts:
                stream.write(json.dumps(draft, ensure_ascii=False) + "\n")
        with (output_path / "summary.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path,
                        default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("runs/cep002-contract-drafts-001"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    report = make_drafts(args.intake, args.out, args.execute)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
