"""CEP-002 GSM8K intake unit tests; synthetic rows only, no dataset download."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from diagnostics.cep002_data_intake import (
    intake, select_review_partition, PRIOR_TRAIN, PRIOR_LOSS_VALIDATION,
    PRIOR_PAIRED_EVALUATION, REVIEW_COUNT, RESERVED_HOLDOUT,
)
from diagnostics.safe_start_data import TRAIN_SHA256


def make_rows(count: int) -> list[dict]:
    return [
        {
            "question": f"Worker number {i} packs five boxes. How many boxes are packed?",
            "answer": f"Five boxes are packed by worker {i}.\n#### 5",
        }
        for i in range(count)
    ]


class SplitTests(unittest.TestCase):
    def test_review_and_future_holdout_disjoint_from_historical_split(self):
        review, holdout, excluded = select_review_partition(make_rows(1300))
        self.assertEqual(len(review), REVIEW_COUNT)
        self.assertEqual(len(holdout), RESERVED_HOLDOUT)
        self.assertEqual(len(excluded), PRIOR_TRAIN + PRIOR_LOSS_VALIDATION + PRIOR_PAIRED_EVALUATION)
        review_ids = {row["question_id"] for row in review}
        holdout_ids = {row["question_id"] for row in holdout}
        self.assertFalse(review_ids & excluded)
        self.assertFalse(holdout_ids & excluded)
        self.assertFalse(review_ids & holdout_ids)

    def test_reproducible_partition(self):
        rows = make_rows(1300)
        a = select_review_partition(rows)
        b = select_review_partition(rows)
        self.assertEqual(a, b)

    def test_insufficient_data_fails_closed(self):
        with self.assertRaises(ValueError):
            select_review_partition(make_rows(1100))

    def test_invalid_split_rejected(self):
        with self.assertRaises(ValueError):
            select_review_partition(make_rows(100), train_size=10, validation_size=8,
                                    prior_evaluation_size=-1, review_size=3, reserve_size=3)


class IntakeTests(unittest.TestCase):
    def run_intake(self, root: Path, execute: bool, official: list[str] | None = None):
        raw = root / "dataset.parquet"
        official_path = root / "questions.jsonl"
        raw.touch()
        official_path.touch()
        with (
            patch("diagnostics.cep002_data_intake.sha256_file", return_value=TRAIN_SHA256),
            patch("diagnostics.cep002_data_intake.read_parquet", return_value=make_rows(1300)),
            patch("diagnostics.cep002_data_intake.read_eval_prompts",
                  return_value=official or ["Unrelated official evaluation prompt"]),
        ):
            return intake(raw, official_path, root / "review", execute=execute)

    def test_dry_run_never_writes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self.run_intake(root, execute=False)
            self.assertEqual(report["status"], "plan_only")
            self.assertEqual(report["candidate_count"], 12)
            self.assertFalse((root / "review").exists())

    def test_review_output_has_no_training_approval(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self.run_intake(root, execute=True)
            self.assertEqual(report["status"], "review_only_not_training_eligible")
            self.assertFalse(report["training_performed"])
            self.assertEqual(report["candidate_contracts_verified"], 0)
            self.assertFalse(report["prior_other_pilots_and_review_sets_fully_audited"])
            with (root / "review" / "candidates-review.jsonl").open(encoding="utf-8") as stream:
                candidates = [json.loads(line) for line in stream]
            self.assertEqual(len(candidates), 12)
            self.assertTrue(all(row["contract"] is None and not row["approved_for_training"]
                                for row in candidates))
            with (root / "review" / "holdout-reservation.jsonl").open(encoding="utf-8") as stream:
                holdout = [json.loads(line) for line in stream]
            self.assertEqual(len(holdout), 60)
            self.assertTrue(all(set(row) == {"question_id", "question_sha256"} for row in holdout))
            self.assertFalse(set(row["question_id"] for row in candidates) &
                             set(row["question_id"] for row in holdout))

    def test_existing_run_cannot_be_overwritten(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_intake(root, execute=True)
            before = (root / "review" / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                self.run_intake(root, execute=True)
            self.assertEqual(before, (root / "review" / "summary.json").read_bytes())

    def test_official_prompt_overlap_blocks_writing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            review, _, _ = select_review_partition(make_rows(1300))
            with self.assertRaises(ValueError):
                self.run_intake(root, execute=True, official=[review[0]["question"]])
            self.assertFalse((root / "review").exists())

    def test_dataset_integrity_mismatch_blocks_writing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "dataset.parquet"
            official = root / "questions.jsonl"
            raw.touch()
            official.touch()
            with patch("diagnostics.cep002_data_intake.sha256_file", return_value="wrong"):
                with self.assertRaises(ValueError):
                    intake(raw, official, root / "review", execute=True)
            self.assertFalse((root / "review").exists())

    def test_missing_eval_prompts_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "dataset.parquet"
            raw.touch()
            with patch("diagnostics.cep002_data_intake.sha256_file", return_value=TRAIN_SHA256):
                with self.assertRaises(FileNotFoundError):
                    intake(raw, root / "missing-questions.jsonl", root / "review", execute=True)


if __name__ == "__main__":
    unittest.main()
