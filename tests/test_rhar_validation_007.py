"""CPU tests for RHAR Validation 007."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.rhar_validation_007 import (
    VARIANTS,
    load_partial,
    metrics,
    select_fresh_validation,
    summarize,
    validation_fingerprint,
)


def make_rows(count: int) -> list[dict]:
    return [
        {
            "question": f"Worker {i} packs five boxes with two items each. How many items?",
            "answer": "Multiply five by two.\n#### 10",
        }
        for i in range(count)
    ]


class SelectionTests(unittest.TestCase):
    def test_fresh_validation_excludes_training004_split_and_protected_ids(self):
        raw = make_rows(500)
        protected = {f"gsm8k-train-{i:05d}" for i in range(10)}
        selected, stats = select_fresh_validation(
            raw,
            protected,
            count=30,
            training004_train_size=100,
            training004_val_size=20,
            training004_seed=404,
            selection_seed=7007,
        )
        ids = {row["question_id"] for row in selected}
        self.assertFalse(ids & protected)
        self.assertEqual(len(ids), 30)
        self.assertEqual(stats["training004_total_ids_excluded"], 120)

    def test_selection_is_deterministic(self):
        raw = make_rows(500)
        a, _ = select_fresh_validation(
            raw, set(), 20, 100, 20, 404, 7007
        )
        b, _ = select_fresh_validation(
            raw, set(), 20, 100, 20, 404, 7007
        )
        self.assertEqual(
            [row["question_id"] for row in a],
            [row["question_id"] for row in b],
        )

    def test_invalid_count_fails_closed(self):
        with self.assertRaises(ValueError):
            select_fresh_validation(make_rows(500), set(), count=0)

    def test_fingerprint_changes_with_selected_ids(self):
        a = [{"question_id": "gsm8k-train-00001"}]
        b = [{"question_id": "gsm8k-train-00002"}]
        self.assertNotEqual(validation_fingerprint(a), validation_fingerprint(b))


class SummaryTests(unittest.TestCase):
    def test_metrics(self):
        rows = [
            {"correct": True, "truncated": False, "tokens": 10},
            {"correct": False, "truncated": True, "tokens": 20},
        ]
        self.assertEqual(
            metrics(rows),
            {
                "correct": 1,
                "complete": 1,
                "truncated": 1,
                "mean_tokens": 15.0,
                "total_tokens": 30,
            },
        )

    def test_three_way_summary_and_regressions(self):
        records = []
        values = {
            "a": {"base": True, "sft003": False, "sft004": True},
            "b": {"base": False, "sft003": True, "sft004": False},
        }
        for variant in VARIANTS:
            for task_id in ("a", "b"):
                records.append({
                    "variant": variant,
                    "id": task_id,
                    "correct": values[task_id][variant],
                    "truncated": False,
                    "tokens": 10 if variant == "base" else 9 if variant == "sft003" else 8,
                })
        summary = summarize(records)
        self.assertEqual(summary["validation_examples"], 2)
        self.assertEqual(summary["sft004_fixed_vs_sft003"], 1)
        self.assertEqual(summary["sft004_broke_vs_sft003"], 1)
        self.assertEqual(summary["sft004_fixed_vs_base"], 0)
        self.assertEqual(summary["sft004_broke_vs_base"], 0)
        self.assertEqual(summary["tokens_delta_sft004_minus_sft003"], -2)

    def test_unpaired_summary_fails_closed(self):
        records = [
            {"variant": "base", "id": "a", "correct": True, "truncated": False, "tokens": 1},
            {"variant": "sft003", "id": "b", "correct": True, "truncated": False, "tokens": 1},
            {"variant": "sft004", "id": "a", "correct": True, "truncated": False, "tokens": 1},
        ]
        with self.assertRaises(ValueError):
            summarize(records)


class ResumeTests(unittest.TestCase):
    def test_partial_loader_restores_valid_unique_rows(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.partial.jsonl"
            path.write_text(
                json.dumps({"id": "q1", "variant": "base"}) + "\n"
                + json.dumps({"id": "q1", "variant": "sft003"}) + "\n",
                encoding="utf-8",
            )
            rows = load_partial(path, {"q1"})
            self.assertEqual(len(rows), 2)

    def test_partial_loader_rejects_duplicate_key(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.partial.jsonl"
            row = json.dumps({"id": "q1", "variant": "base"}) + "\n"
            path.write_text(row + row, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_partial(path, {"q1"})

    def test_partial_loader_rejects_wrong_validation_id(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.partial.jsonl"
            path.write_text(
                json.dumps({"id": "q2", "variant": "base"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_partial(path, {"q1"})


if __name__ == "__main__":
    unittest.main()
