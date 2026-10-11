"""No-network CPU tests for reproducible provenance of previous paired validations."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from diagnostics.cep002_validation_provenance import (
    validate_paired_records, classify_other_id_only, provenance,
)
from diagnostics.safe_start_data import TRAIN_SHA256
from tests.test_cep002_history_overlap import manifest, history, write_jsonl


def dataset_validation():
    return [
        {"question_id": f"gsm8k-train-{2000+i:05d}",
         "gold_answer": str(200+i)}
        for i in range(180)
    ]


def history_pairs(rows):
    return [
        {"id": row["question_id"], "variant": variant,
         "gold": row["gold_answer"], "correct": True}
        for row in rows for variant in ("sft", "cep")
    ]


def prepared(root: Path):
    intake, reserved = manifest(root)
    safe, runs = history(root)
    validation = dataset_validation()
    write_jsonl(runs / "rhar-validation-005" / "records.jsonl",
                history_pairs(validation[100:120]))
    write_jsonl(runs / "rhar-validation-006" / "records.jsonl",
                history_pairs(validation[120:180]))
    write_jsonl(runs / "other-pilot" / "records.jsonl",
                [{"id": "sandbox-test-1"}, {"id": "sandbox-test-2"},
                 {"id": "gsm8k-train-08000"}])
    parquet = root / "dataset.parquet"
    parquet.touch()
    return parquet, intake, reserved, safe, runs, root / "provenance"


class PairChecks(unittest.TestCase):
    def test_paired_eval_matches_source(self):
        rows = dataset_validation()[100:120]
        report = validate_paired_records(history_pairs(rows), rows)
        self.assertTrue(report["source_identity_verified"])
        self.assertEqual(report["paired_record_count"], 40)
        self.assertEqual(report["unique_question_ids"], 20)

    def test_duplicate_variant_rejected(self):
        rows = dataset_validation()[100:120]
        records = history_pairs(rows)
        records[-1] = records[0].copy()
        with self.assertRaises(ValueError):
            validate_paired_records(records, rows)

    def test_missing_pair_rejected(self):
        rows = dataset_validation()[100:120]
        with self.assertRaises(ValueError):
            validate_paired_records(history_pairs(rows)[:-1], rows)

    def test_wrong_gold_rejected(self):
        rows = dataset_validation()[100:120]
        records = history_pairs(rows)
        records[0]["gold"] = "-99"
        with self.assertRaises(ValueError):
            validate_paired_records(records, rows)

    def test_wrong_variant_rejected(self):
        rows = dataset_validation()[100:120]
        records = history_pairs(rows)
        records[0]["variant"] = "other-model"
        with self.assertRaises(ValueError):
            validate_paired_records(records, rows)

    def test_unexpected_source_id_rejected(self):
        rows = dataset_validation()[100:120]
        records = history_pairs(rows)
        records[0]["id"] = "gsm8k-train-00001"
        with self.assertRaises(ValueError):
            validate_paired_records(records, rows)


class EndToEndProvenanceTests(unittest.TestCase):
    def run_provenance(self, args: tuple, execute: bool = False):
        with (
            patch("diagnostics.cep002_validation_provenance.sha256_file",
                  return_value=TRAIN_SHA256),
            patch("diagnostics.cep002_validation_provenance.read_parquet",
                  return_value=[{"question": "mock-only"}]),
            patch("diagnostics.cep002_validation_provenance.prepare_pool",
                  return_value=([{"question_id": f"mock-train-{i}"} for i in range(1000)],
                                dataset_validation())),
        ):
            return provenance(*args, execute=execute)

    def test_complete_paired_provenance_but_other_files_still_pending(self):
        with TemporaryDirectory() as temp:
            args = prepared(Path(temp))
            result = self.run_provenance(args)
            self.assertEqual(result["status"],
                             "known_validation_ids_verified_remaining_history_partial")
            self.assertEqual(result["prior_validation_rows_with_confirmed_dataset_identity"], 160)
            self.assertEqual(result["prior_validation_distinct_questions"], 80)
            self.assertEqual(result["remaining_other_runs_id_only_rows"], 3)
            self.assertTrue(result["remaining_provenance_needs_review"])
            self.assertFalse(result["reserved_holdout_questions_selected"])
            self.assertFalse(result["reserved_holdout_texts_exported"])
            self.assertFalse(result["training_approved"])
            self.assertFalse(args[-1].exists())

    def test_aggregate_other_run_ids_without_disclosing_raw_ids(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            args = prepared(root)
            totals, paths = classify_other_id_only(args[4])
            self.assertEqual(totals["id_only_records"], 3)
            self.assertEqual(totals["with_gsm8k_train_id"], 1)
            self.assertEqual(totals["with_other_ids_only"], 2)
            self.assertNotIn("sandbox-test-1", json.dumps(paths))

    def test_identity_mismatch_blocks_report(self):
        with TemporaryDirectory() as temp:
            args = prepared(Path(temp))
            path = args[4] / "rhar-validation-006" / "records.jsonl"
            with path.open(encoding="utf-8") as stream:
                rows = [json.loads(line) for line in stream]
            rows[0]["id"] = "gsm8k-train-00001"
            write_jsonl(path, rows)
            with self.assertRaises(ValueError):
                self.run_provenance(args, execute=True)
            self.assertFalse(args[-1].exists())

    def test_candidate_overlap_blocks_report(self):
        with TemporaryDirectory() as temp:
            args = prepared(Path(temp))
            write_jsonl(args[4] / "other-pilot" / "records.jsonl",
                        [{"id": "gsm8k-train-00001"}])
            with self.assertRaises(ValueError):
                self.run_provenance(args, execute=True)

    def test_execute_is_append_only_and_no_source_question_export(self):
        with TemporaryDirectory() as temp:
            args = prepared(Path(temp))
            result = self.run_provenance(args, execute=True)
            self.assertEqual(result["mode"], "execute")
            report = (args[-1] / "summary.json").read_text(encoding="utf-8")
            self.assertNotIn("A practice-only worker", report)
            self.assertNotIn("sandbox-test-1", report)
            self.assertTrue((args[-1] / "other-file-coverage.json").is_file())
            with self.assertRaises(FileExistsError):
                self.run_provenance(args, execute=True)


if __name__ == "__main__":
    unittest.main()
