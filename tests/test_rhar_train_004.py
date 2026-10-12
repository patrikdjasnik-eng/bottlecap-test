"""CPU tests for RHAR Training 004 long SFT control."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from diagnostics.rhar_train_004 import (
    CEP002_HOLDOUT_COUNT,
    CEP002_REVIEW_COUNT,
    SAFE_START_COUNT,
    deadline_reached,
    historical_partition_ids,
    historical_run_gsm8k_ids,
    load_manifest_ids,
    prepare_long_pool,
)


def make_rows(count: int) -> list[dict]:
    return [
        {
            "question": f"Worker {i} packs five boxes with two items each. How many items?",
            "answer": "Multiply five by two.\n#### 10",
        }
        for i in range(count)
    ]


def write_manifest(path: Path, ids: list[str]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for task_id in ids:
            stream.write(json.dumps({"question_id": task_id}) + "\n")


class ManifestTests(unittest.TestCase):
    def test_review_manifest_requires_exact_unique_count(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.jsonl"
            ids = [f"gsm8k-train-{i:05d}" for i in range(CEP002_REVIEW_COUNT)]
            write_manifest(path, ids)
            self.assertEqual(load_manifest_ids(path, CEP002_REVIEW_COUNT, "review"), set(ids))

    def test_duplicate_manifest_id_fails_closed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "holdout.jsonl"
            ids = [f"gsm8k-train-{i:05d}" for i in range(CEP002_HOLDOUT_COUNT - 1)]
            ids.append(ids[-1])
            write_manifest(path, ids)
            with self.assertRaises(ValueError):
                load_manifest_ids(path, CEP002_HOLDOUT_COUNT, "holdout")

    def test_safe_start_manifest_count_is_enforced(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "safe.jsonl"
            ids = [f"gsm8k-train-{i:05d}" for i in range(SAFE_START_COUNT - 1)]
            write_manifest(path, ids)
            with self.assertRaises(ValueError):
                load_manifest_ids(path, SAFE_START_COUNT, "safe")


class ProtectionTests(unittest.TestCase):
    def test_historical_partition_reconstructs_1180_unique_ids(self):
        ids = historical_partition_ids(make_rows(1600))
        self.assertEqual(len(ids), 1180)

    def test_long_pool_excludes_every_protected_id(self):
        rows = make_rows(1600)
        protected = {f"gsm8k-train-{i:05d}" for i in range(25)}
        train, val, available = prepare_long_pool(rows, protected, 100, 30, 404)
        selected = {row["question_id"] for row in train + val}
        self.assertFalse(selected & protected)
        self.assertEqual(available, 1600 - len(protected))

    def test_long_pool_is_deterministic(self):
        rows = make_rows(500)
        protected = {"gsm8k-train-00001", "gsm8k-train-00002"}
        first = prepare_long_pool(rows, protected, 80, 20, 404)
        second = prepare_long_pool(rows, protected, 80, 20, 404)
        self.assertEqual(
            [row["question_id"] for row in first[0] + first[1]],
            [row["question_id"] for row in second[0] + second[1]],
        )

    def test_long_pool_train_and_validation_are_disjoint(self):
        rows = make_rows(500)
        train, val, _ = prepare_long_pool(rows, set(), 80, 20, 404)
        self.assertFalse(
            {row["question_id"] for row in train}
            & {row["question_id"] for row in val}
        )

    def test_missing_protected_id_fails_closed(self):
        with self.assertRaises(ValueError):
            prepare_long_pool(
                make_rows(200),
                {"gsm8k-train-99999"},
                80,
                20,
                404,
            )

    def test_history_scan_keeps_only_gsm8k_ids(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "old"
            run.mkdir()
            with (run / "records.jsonl").open("w", encoding="utf-8") as stream:
                stream.write(json.dumps({"id": "gsm8k-train-00042"}) + "\n")
                stream.write(json.dumps({"id": "arithmetic_apples"}) + "\n")
            self.assertEqual(
                historical_run_gsm8k_ids(root),
                {"gsm8k-train-00042"},
            )


class DeadlineTests(unittest.TestCase):
    def test_deadline_is_not_reached_early(self):
        self.assertFalse(deadline_reached(100.0, 120.0, 100.0 + 7199.0))

    def test_deadline_is_reached_at_limit(self):
        self.assertTrue(deadline_reached(100.0, 120.0, 100.0 + 7200.0))

    def test_invalid_deadline_fails_closed(self):
        with self.assertRaises(ValueError):
            deadline_reached(0.0, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
