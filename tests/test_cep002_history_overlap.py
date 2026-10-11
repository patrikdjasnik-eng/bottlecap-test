"""CEP-002 history overlap regression tests using synthetic JSONL files only."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.cep002_history_overlap import (
    historical_audit, extract_references, load_targets, normalized,
)

SOURCE_QUESTION = (
    "A practice-only worker counted twenty four notebooks at a depot and then "
    "shipped seven notebooks to a different place. How many remain?"
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        for value in records:
            stream.write(json.dumps(value) + "\n")


def make_candidate(index: int) -> dict:
    question = SOURCE_QUESTION + f" This is synthetic example {index}."
    return {
        "question_id": f"gsm8k-train-{index:05d}",
        "question": question,
        "question_sha256": sha256(question.encode()).hexdigest(),
        "source": "gsm8k/main/train",
        "status": "REVIEW_REQUIRED",
        "approved_for_training": False,
    }


def manifest(root: Path) -> tuple[Path, Path]:
    reviews = [make_candidate(i) for i in range(12)]
    reserved = [
        {
            "question_id": f"gsm8k-train-{i:05d}",
            "question_sha256": sha256(f"secret-holdout-{i}".encode()).hexdigest(),
        }
        for i in range(100, 160)
    ]
    intake = root / "candidates-review.jsonl"
    reservations = root / "holdout-reservation.jsonl"
    write_jsonl(intake, reviews)
    write_jsonl(reservations, reserved)
    return intake, reservations


def history(root: Path) -> tuple[Path, Path]:
    safe_start = root / "data" / "safe-start" / "questions.jsonl"
    runs = root / "runs"
    write_jsonl(safe_start, [{"question_id": "gsm8k-train-09000", "question": "Unrelated training item"}])
    write_jsonl(runs / "rhar-validation-005" / "records.jsonl",
                [{"id": "gsm8k-train-08888", "correct": True}])
    write_jsonl(runs / "rhar-validation-006" / "records.jsonl",
                [{"id": "gsm8k-train-07777", "correct": False}])
    write_jsonl(runs / "other-pilot" / "records.jsonl",
                [{"id": "pilot-x", "question": "Separate earlier trial question"}])
    return safe_start, runs


class ReferenceParsingTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalized("A/ B  12?"), "a b 12")

    def test_extract_only_user_input_and_source_ids(self):
        ids, hashes, texts = extract_references({
            "id": "gsm8k-train-00004",
            "messages": [{"role": "assistant", "content": SOURCE_QUESTION},
                         {"role": "user", "content": "Unrelated question"}],
            "gold": SOURCE_QUESTION,
            "generated_text": SOURCE_QUESTION,
        })
        self.assertEqual(ids, {"gsm8k-train-00004"})
        self.assertEqual(hashes, set())
        self.assertEqual(texts, {"Unrelated question"})

    def test_source_question_hash_extracted(self):
        value = sha256(b"question").hexdigest()
        _, hashes, _ = extract_references({"question_sha256": value})
        self.assertEqual(hashes, {value})


class HistoricalAuditTests(unittest.TestCase):
    def prepare(self, root: Path):
        intake, reservations = manifest(root)
        safe_start, runs = history(root)
        out = root / "out"
        return intake, reservations, safe_start, runs, out

    def run_audit(self, args: tuple, execute: bool = False):
        return historical_audit(*args, execute=execute)

    def test_no_overlap_stays_partial_and_unapproved(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            summary = self.run_audit(args)
            self.assertEqual(summary["status"], "partial_historical_screen_no_match")
            self.assertEqual(summary["historical_record_files"], 3)
            self.assertEqual(summary["review_overlaps"], 0)
            self.assertEqual(summary["reserved_holdout_overlaps"], 0)
            self.assertFalse(summary["training_approved"])
            self.assertFalse(summary["historical_sources_fully_screened"])
            self.assertFalse(summary["semantic_duplicate_check_exhaustive"])
            self.assertFalse(summary["holdout_questions_accessed"])
            self.assertFalse(args[-1].exists())

    def test_detects_prior_eval_id(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[3] / "rhar-validation-005" / "records.jsonl",
                        [{"id": "gsm8k-train-00002", "correct": True}])
            summary = self.run_audit(args)
            self.assertEqual(summary["review_overlaps"], 1)
            self.assertEqual(summary["seen_candidate_ids"], ["gsm8k-train-00002"])
            self.assertEqual(summary["status"], "overlap_detected")

    def test_detects_embedded_question_text(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            row = make_candidate(3)
            write_jsonl(args[3] / "other-pilot" / "records.jsonl", [
                {"prompt": [{"role": "user", "content":
                             "Solve carefully: " + row["question"] + " Use full reasoning."}]}
            ])
            summary = self.run_audit(args)
            self.assertEqual(summary["review_overlaps"], 1)
            self.assertEqual(summary["seen_candidate_ids"], ["gsm8k-train-00003"])

    def test_safe_start_is_screened(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[2], [make_candidate(4)])
            summary = self.run_audit(args)
            self.assertEqual(summary["review_overlaps"], 1)

    def test_reserved_holdout_detected_by_hash_not_content(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            held = load_targets(args[0], args[1])["gsm8k-train-00102"]
            write_jsonl(args[3] / "other-pilot" / "records.jsonl", [
                {"question_sha256": held["sha256"], "generated_text": "Not relevant"}
            ])
            summary = self.run_audit(args)
            self.assertEqual(summary["reserved_holdout_overlaps"], 1)
            self.assertEqual(summary["seen_reserved_ids"], ["gsm8k-train-00102"])
            self.assertFalse(summary["holdout_questions_accessed"])

    def test_reserved_holdout_detected_by_id(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[3] / "other-pilot" / "records.jsonl",
                        [{"question_id": "gsm8k-train-00100"}])
            self.assertEqual(self.run_audit(args)["reserved_holdout_overlaps"], 1)

    def test_generated_text_is_not_compared_as_question(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[3] / "other-pilot" / "records.jsonl",
                        [{"id": "other-task", "generated_text": make_candidate(6)["question"]}])
            summary = self.run_audit(args)
            self.assertEqual(summary["review_overlaps"], 0)
            self.assertTrue(summary["question_text_missing_from_some_records"])

    def test_unknown_shapes_are_reported(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[3] / "other-pilot" / "records.jsonl", [{"score": 0.7}])
            summary = self.run_audit(args)
            self.assertEqual(summary["opaque_rows"], 1)
            self.assertTrue(summary["unrecognized_record_shapes_present"])

    def test_invalid_candidate_hash_blocked(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            rows = [make_candidate(i) for i in range(12)]
            rows[0]["question_sha256"] = "0" * 64
            write_jsonl(args[0], rows)
            with self.assertRaises(ValueError):
                self.run_audit(args)

    def test_prematurely_approved_review_blocked(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            rows = [make_candidate(i) for i in range(12)]
            rows[1]["approved_for_training"] = True
            write_jsonl(args[0], rows)
            with self.assertRaises(ValueError):
                self.run_audit(args)

    def test_duplicate_partition_id_blocked(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            reserved = [{"question_id": f"gsm8k-train-{i:05d}",
                         "question_sha256": sha256(f"secret-holdout-{i}".encode()).hexdigest()}
                        for i in range(100, 160)]
            reserved[0]["question_id"] = "gsm8k-train-00000"
            write_jsonl(args[1], reserved)
            with self.assertRaises(ValueError):
                self.run_audit(args)

    def test_missing_validation_file_blocks(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            (args[3] / "rhar-validation-006" / "records.jsonl").unlink()
            with self.assertRaises(FileNotFoundError):
                self.run_audit(args)

    def test_malformed_jsonl_blocks_without_output(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            file = args[3] / "other-pilot" / "records.jsonl"
            file.write_text("{not json}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.run_audit(args, execute=True)
            self.assertFalse(args[-1].exists())

    def test_execute_writes_only_hashes_ids_and_file_paths(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            write_jsonl(args[3] / "other-pilot" / "records.jsonl",
                        [{"question": make_candidate(1)["question"]}])
            report = self.run_audit(args, execute=True)
            self.assertEqual(report["review_overlaps"], 1)
            summary = (args[-1] / "summary.json").read_text(encoding="utf-8")
            matches = (args[-1] / "overlaps.jsonl").read_text(encoding="utf-8")
            self.assertNotIn(SOURCE_QUESTION, summary + matches)
            self.assertNotIn("secret-holdout", summary + matches)
            self.assertFalse(report["official_questions_or_answers_exported"])
            with self.assertRaises(FileExistsError):
                self.run_audit(args, execute=True)

    def test_empty_history_file_fails_closed(self):
        with TemporaryDirectory() as temp:
            args = self.prepare(Path(temp))
            (args[3] / "other-pilot" / "records.jsonl").write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.run_audit(args)


if __name__ == "__main__":
    unittest.main()
