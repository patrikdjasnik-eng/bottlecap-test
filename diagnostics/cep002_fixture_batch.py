"""CEP-002 synthetic arithmetic smoke batch.

These hand-authored fixtures exercise code paths, not Qwen quality or independent
semantic task validation. No benchmark data, GPU inference, or training is used.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from .cep002_cpu import CandidateTrace, ExperienceLedger, StepRule, TaskContract


@dataclass(frozen=True)
class Example:
    question: str
    contract: TaskContract
    candidate: CandidateTrace


CASES = (
    (
        "Five boxes have twelve apples each. Seventeen apples are sold. How many remain?",
        {"boxes": "5", "per_box": "12", "sold": "17"},
        (("total", "boxes * per_box", "60"), ("remaining", "total - sold", "43")),
        "remaining", "43",
    ),
    (
        "Of 240 items, three eighths are reserved. Twenty percent of what remains is defective. How many full cartons of six good items can be packed?",
        {"items": "240", "reserve_numerator": "3", "reserve_denominator": "8",
         "defect_percent": "20", "hundred": "100", "carton_size": "6"},
        (("reserved", "items * reserve_numerator / reserve_denominator", "90"),
         ("available", "items - reserved", "150"),
         ("defective", "available * defect_percent / hundred", "30"),
         ("good", "available - defective", "120"),
         ("cartons", "good / carton_size", "20")),
        "cartons", "20",
    ),
    (
        "A price of 200 is discounted first by 10 percent and then by 20 percent. What is the final price?",
        {"price": "200", "first_percent": "10", "second_percent": "20", "hundred": "100"},
        (("first_price", "price * (hundred - first_percent) / hundred", "180"),
         ("final_price", "first_price * (hundred - second_percent) / hundred", "144")),
        "final_price", "144",
    ),
    (
        "A worker earns 150 per hour for eight regular hours and 200 per hour for two overtime hours. What is the total?",
        {"hours": "8", "rate": "150", "extra_hours": "2", "extra_rate": "200"},
        (("base_pay", "hours * rate", "1200"),
         ("extra_pay", "extra_hours * extra_rate", "400"),
         ("total_pay", "base_pay + extra_pay", "1600")),
        "total_pay", "1600",
    ),
    (
        "Four child tickets cost 30 each and three adult tickets cost 70 each. What is the total cost?",
        {"children": "4", "child_price": "30", "adults": "3", "adult_price": "70"},
        (("child_cost", "children * child_price", "120"),
         ("adult_cost", "adults * adult_price", "210"),
         ("total_cost", "child_cost + adult_cost", "330")),
        "total_cost", "330",
    ),
    (
        "A tank contains 150 liters. Twenty-five percent is used. How many liters remain?",
        {"volume": "150", "used_percent": "25", "hundred": "100"},
        (("used", "volume * used_percent / hundred", "37.5"),
         ("remaining", "volume - used", "112.5")),
        "remaining", "112.5",
    ),
    (
        "A bill of 125 includes a 25 percent tax on the pre-tax price. What is the pre-tax price?",
        {"gross": "125", "tax_percent": "25", "hundred": "100"},
        (("base_price", "gross * hundred / (hundred + tax_percent)", "100"),),
        "base_price", "100",
    ),
    (
        "A warehouse has eighty parts. What is three eighths of the stock?",
        {"stock": "80", "denominator": "8", "numerator": "3"},
        (("one_eighth", "stock / denominator", "10"),
         ("share", "one_eighth * numerator", "30")),
        "share", "30",
    ),
    (
        "The three test scores are 70, 80 and 90. What is their average?",
        {"score_a": "70", "score_b": "80", "score_c": "90", "count": "3"},
        (("score_sum", "score_a + score_b + score_c", "240"),
         ("average", "score_sum / count", "80")),
        "average", "80",
    ),
    (
        "A vehicle travels 180 km at 40 km/h and then rests for 0.5 hour. How much time passes?",
        {"distance": "180", "speed": "40", "rest": "0.5"},
        (("travel_time", "distance / speed", "4.5"),
         ("elapsed", "travel_time + rest", "5")),
        "elapsed", "5",
    ),
    (
        "Three cartons hold twelve pieces each, plus eight loose pieces. How many pieces are there?",
        {"cartons": "3", "per_carton": "12", "loose": "8"},
        (("packed", "cartons * per_carton", "36"),
         ("total", "packed + loose", "44")),
        "total", "44",
    ),
    (
        "Twelve workers complete four tasks each and the results are shared equally among three teams. How many tasks per team?",
        {"workers": "12", "tasks_each": "4", "teams": "3"},
        (("completed", "workers * tasks_each", "48"),
         ("per_team", "completed / teams", "16")),
        "per_team", "16",
    ),
)


def fixtures() -> tuple[Example, ...]:
    result = []
    for index, (question, facts, raw_rules, final_target, gold) in enumerate(CASES, 1):
        task_id = f"synthetic-cep002-{index:02d}"
        contract = TaskContract(
            task_id=task_id,
            source="synthetic/manual",
            facts=facts,
            rules=tuple(StepRule(target, expr) for target, expr, _ in raw_rules),
            final_target=final_target,
            gold_answer=gold,
            reviewed_by="fixture-author-only-not-independent-audit",
            overlap_screen_passed=True,
        )
        text = "\n".join([f"{target} = {expr} => {value}" for target, expr, value in raw_rules]
                         + [f"Final answer: {gold}"])
        result.append(Example(
            question=question, contract=contract,
            candidate=CandidateTrace(
                candidate_id=f"{task_id}-valid",
                task_id=task_id, raw_text=text, completed=True,
                measured_tokens=None,
            ),
        ))
    return tuple(result)


def run_batch(out: Path) -> dict:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing directory: {out}")
    examples = fixtures()
    if len(examples) != 12 or len({e.contract.task_id for e in examples}) != 12:
        raise RuntimeError("missing or repeated fixtures")
    out.mkdir(parents=True, exist_ok=False)
    ledger = ExperienceLedger(out / "xp-history.jsonl")
    rows = []
    for example in examples:
        verdict = ledger.record(example.contract, example.candidate)
        rows.append({
            "task_id": example.contract.task_id,
            "question": example.question,
            "gold": example.contract.gold_answer,
            "raw_trace": example.candidate.raw_text,
            "verdict": verdict.status,
            "reason": verdict.reason,
            "contract_hash": verdict.contract_hash,
            "xp_records": len(ledger.xp(example.contract.task_id)),
        })
    report = {
        "status": "synthetic_cpu_smoke_only",
        "count": len(rows),
        "verified": sum(row["verdict"] == "VERIFIED" for row in rows),
        "nonverified": sum(row["verdict"] != "VERIFIED" for row in rows),
        "benchmark_dataset_used": False,
        "independent_semantic_audit_performed": False,
        "official_benchmark": False,
        "gpu_used": False,
        "training_performed": False,
        "training_approved": False,
    }
    with (out / "records.jsonl").open("x", encoding="utf-8") as stream:
        for record in rows:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (out / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("runs/cep002-fixture-001"))
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({
            "status": "plan_only", "fixture_count": len(fixtures()),
            "out": str(args.out), "gpu_used": False, "training_performed": False,
        }, indent=2))
        return 0
    report = run_batch(args.out)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
