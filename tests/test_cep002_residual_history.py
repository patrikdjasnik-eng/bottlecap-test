"""Regression tests for residual-history ID triage. Synthetic records only."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from diagnostics.cep002_residual_history import inspect_remaining, main_audit
from diagnostics.cep002_history_overlap import load_targets
from diagnostics.safe_start_data import TRAIN_SHA256
from tests.test_cep002_history_overlap import history, manifest, write_jsonl


def fake_dataset(size=100):
    return [
        {"question": f"Synthetic practice task {i}: what is {i} plus zero?",
         "answer": f"The total is {i}.\n#### {i}"}
        for i in range(size)
    ]


def fake_partition():
    prior_training = [{"question_id": "gsm8k-train-00030"}]
    loss = [{"question_id": "gsm8k-train-00031"}] * 100
    validation = [{"question_id": "gsm8k-train-00032"}] * 80
    return prior_training, loss + validation


def setup_case(root):
    intake, reserve = manifest(root)
    safe, runs = history(root)
    write_jsonl(runs / "other-pilot" / "records.jsonl",
                [{"id": f"gsm8k-train-{i:05d}"} for i in range(30, 36)]
                + [{"id": f"test-external-{i}"} for i in range(39)])
    raw = root / "train.parquet"
    raw.touch()
    return raw, intake, reserve, runs, root / "out"


class ResidualHistoryTests(unittest.TestCase):
    def run_scan(self, root: Path):
        _, intake, reserve, runs, _ = setup_case(root)
        targets = load_targets(intake, reserve)
        with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
            return inspect_remaining(fake_dataset(), runs, targets)

    def test_six_source_ids_and_39_other_id_rows(self):
        with TemporaryDirectory() as temp:
            counts, details = self.run_scan(Path(temp))
            self.assertEqual(counts["gsm8k_format_id"], 6)
            self.assertEqual(counts["non_gsm8k_format_id"], 39)
            self.assertEqual(counts["within_old_training"], 1)
            self.assertEqual(counts["within_old_loss_validation"], 1)
            self.assertEqual(counts["within_old_paired_evaluation"], 1)
            self.assertEqual(counts["outside_known_1180"], 3)
            self.assertEqual(counts["gold_not_recorded"], 6)
            self.assertNotIn("Synthetic practice task", json.dumps(details))

    def test_source_index_out_of_range_is_reported(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, intake, reserve, runs, _ = setup_case(root)
            write_jsonl(runs / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-09999"}])
            with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
                counts, _ = inspect_remaining(fake_dataset(), runs, load_targets(intake, reserve))
            self.assertEqual(counts["unresolvable_gsm8k_source_id"], 1)

    def test_review_candidate_id_collision_blocks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, intake, reserve, runs, _ = setup_case(root)
            write_jsonl(runs / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-00001"}])
            with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
                with self.assertRaises(ValueError):
                    inspect_remaining(fake_dataset(), runs, load_targets(intake, reserve))

    def test_reserved_holdout_id_collision_blocks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, intake, reserve, runs, _ = setup_case(root)
            write_jsonl(runs / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-00100"}])
            with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
                with self.assertRaises(ValueError):
                    inspect_remaining(fake_dataset(), runs, load_targets(intake, reserve))

    def test_recorded_gold_mismatch_is_not_verified(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, intake, reserve, runs, _ = setup_case(root)
            write_jsonl(runs / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-00033", "gold": "Wrong"}])
            with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
                counts, _ = inspect_remaining(fake_dataset(), runs, load_targets(intake, reserve))
            self.assertEqual(counts["gold_mismatch_or_unknown"], 1)

    def test_ambiguous_row_is_not_resolved(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, intake, reserve, runs, _ = setup_case(root)
            write_jsonl(runs / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-00033",
                          "question_sha256": "0" * 64}])
            with patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()):
                counts, _ = inspect_remaining(fake_dataset(), runs, load_targets(intake, reserve))
            self.assertEqual(counts["ambiguous_id_or_hash_only"], 1)

    def test_dry_run_does_not_write_or_train(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            args = setup_case(root)
            with (
                patch("diagnostics.cep002_residual_history.sha256_file", return_value=TRAIN_SHA256),
                patch("diagnostics.cep002_residual_history.read_parquet", return_value=fake_dataset()),
                patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()),
            ):
                result = main_audit(*args, execute=False)
            self.assertEqual(result["historical_gsm8k_id_rows"], 6)
            self.assertEqual(result["historical_non_gsm8k_id_rows"], 39)
            self.assertFalse(result["training_approved"])
            self.assertFalse(result["reserved_holdout_questions_selected"])
            self.assertFalse(args[-1].exists())

    def test_execute_creates_only_summary_and_coverage(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            args = setup_case(root)
            with (
                patch("diagnostics.cep002_residual_history.sha256_file", return_value=TRAIN_SHA256),
                patch("diagnostics.cep002_residual_history.read_parquet", return_value=fake_dataset()),
                patch("diagnostics.cep002_residual_history.prepare_pool", return_value=fake_partition()),
            ):
                result = main_audit(*args, execute=True)
                with self.assertRaises(FileExistsError):
                    main_audit(*args, execute=True)
            self.assertEqual(result["mode"], "execute")
            summary = (args[-1] / "summary.json").read_text(encoding="utf-8")
            self.assertNotIn("Synthetic practice task", summary)
            self.assertNotIn("test-external-0", summary)
            self.assertTrue((args[-1] / "coverage.json").is_file())

    def test_missing_historical_validations_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            args = setup_case(root)
            (args[3] / "rhar-validation-005" / "records.jsonl").unlink()
            with patch("diagnostics.cep002_residual_history.sha256_file", return_value=TRAIN_SHA256):
                with self.assertRaises(FileNotFoundError):
                    main_audit(*args, execute=False)


if __name__ == "__main__":
    unittest.main()
