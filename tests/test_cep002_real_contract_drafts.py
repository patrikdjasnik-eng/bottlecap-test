"""Source-pinned, CPU-only checks for three real GSM8K CEP-002 draft contracts."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.cep002_real_contract_drafts import (
    DRAFT_SPECS, create_draft, make_drafts,
)


QUESTIONS = (
    "To let Ruth know how long her fish will live, her father tells her that well-cared fish can live 2 years longer than dogs live. On average, dogs live 4 times as long as hamsters live. And hamsters live an average of 2.5 years. How long can a fish live?",
    "Janet has 1/3 of a bottle of rose shampoo and 1/4 of a bottle of jasmine shampoo. If she uses 1/12 of a bottle of shampoo per day, how many days will her shampoo last?",
    "Malcolm has 240 followers on Instagram and 500 followers on Facebook. The number of followers he has on Twitter is half the number of followers he has on Instagram and Facebook combined. Meanwhile, the number of followers he has on TikTok is 3 times the number of followers is has on Twitter, and he has 510 more followers on Youtube than he has on TikTok. How many followers does Malcolm have on all his social media?",
)


def source_record(i: int) -> dict:
    spec = DRAFT_SPECS[i]
    return {
        "question_id": spec["question_id"],
        "question_sha256": spec["question_sha256"],
        "question": QUESTIONS[i],
        "gold_answer": spec["gold_answer"],
        "source": "gsm8k/main/train",
        "dataset_revision": "740312add88f781978c0658806c59bc2815b9866",
        "status": "REVIEW_REQUIRED",
        "contract": None,
        "approved_for_training": False,
    }


def write_intake(path: Path) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for i in range(3):
            stream.write(json.dumps(source_record(i)) + "\n")


class DraftContractTests(unittest.TestCase):
    def test_all_three_input_question_hashes_match(self):
        from hashlib import sha256
        for i, question in enumerate(QUESTIONS):
            with self.subTest(question_id=DRAFT_SPECS[i]["question_id"]):
                self.assertEqual(sha256(question.encode()).hexdigest(), DRAFT_SPECS[i]["question_sha256"])

    def test_three_exact_arithmetic_drafts_but_none_locked(self):
        for i, spec in enumerate(DRAFT_SPECS):
            with self.subTest(question_id=spec["question_id"]):
                draft = create_draft(source_record(i), spec)
                self.assertTrue(draft["exact_fraction_arithmetic_checked"])
                self.assertEqual(draft["vps_status"], "UNVERIFIED")
                self.assertEqual(draft["manual_semantic_review"], "PENDING")
                self.assertFalse(draft["approved_for_training"])
                self.assertEqual(draft["contract"]["reviewed_by"], "")
                self.assertFalse(draft["contract"]["overlap_screen_passed"])
                self.assertFalse(draft["qwen_generated"])

    def test_changed_question_blocked(self):
        row = source_record(0)
        row["question"] += " Or is it eleven?"
        with self.assertRaises(ValueError):
            create_draft(row, DRAFT_SPECS[0])

    def test_changed_gold_blocked(self):
        row = source_record(1)
        row["gold_answer"] = "8"
        with self.assertRaises(ValueError):
            create_draft(row, DRAFT_SPECS[1])

    def test_training_approved_source_blocked(self):
        row = source_record(2)
        row["approved_for_training"] = True
        with self.assertRaises(ValueError):
            create_draft(row, DRAFT_SPECS[2])

    def test_wrong_source_blocked(self):
        row = source_record(0)
        row["source"] = "SVAMP"
        with self.assertRaises(ValueError):
            create_draft(row, DRAFT_SPECS[0])

    def test_wrong_order_blocked(self):
        with self.assertRaises(ValueError):
            create_draft(source_record(1), DRAFT_SPECS[0])

    def test_wrong_intermediate_formula_blocked(self):
        broken = deepcopy(DRAFT_SPECS[0])
        broken["steps"] = (("dog_years", "hamster_years + dog_multiplier", "10"),
                           ("fish_years", "dog_years + fish_extra", "12"))
        with self.assertRaises(ValueError):
            create_draft(source_record(0), broken)

    def test_dry_run_has_no_side_effects(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            intake = root / "candidates-review.jsonl"
            write_intake(intake)
            report = make_drafts(intake, root / "out", execute=False)
            self.assertEqual(report["status"], "plan_only")
            self.assertEqual(report["draft_count"], 3)
            self.assertEqual(report["locked_experiences"], 0)
            self.assertFalse((root / "out").exists())

    def test_execute_writes_three_review_only_records(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            intake = root / "candidates-review.jsonl"
            write_intake(intake)
            out = root / "out"
            report = make_drafts(intake, out, execute=True)
            self.assertEqual(report["arithmetic_crosschecks_passed"], 3)
            self.assertEqual(report["semantic_contracts_independently_reviewed"], 0)
            self.assertFalse(report["training_performed"])
            self.assertFalse(report["holdout_questions_accessed"])
            records = [json.loads(line) for line in (out / "contract-drafts.jsonl").read_text().splitlines()]
            self.assertEqual(len(records), 3)
            self.assertEqual({r["vps_status"] for r in records}, {"UNVERIFIED"})

    def test_existing_output_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            intake = root / "candidates-review.jsonl"
            write_intake(intake)
            out = root / "out"
            make_drafts(intake, out, execute=True)
            before = (out / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                make_drafts(intake, out, execute=True)
            self.assertEqual(before, (out / "summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
