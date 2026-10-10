"""Offline gates for Stress Test 003; no GPU, downloads or inference."""
import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import stress_test_003 as t


class Stress003Tests(unittest.TestCase):
    def test_six_unique_handwritten_holdouts(self):
        t.validate_tasks()
        self.assertEqual(len(t.TASKS), 6)
        self.assertEqual({x["category"] for x in t.TASKS},
                         {"math", "logic", "adversarial"})

    def test_gold_answers_checked_independently(self):
        self.assertEqual((240 * (1 - 3 / 8) * (1 - .2)) / 6, 20)
        self.assertEqual(180 / 60 + 120 / 40, 6)
        self.assertEqual(["ABCD", "BACD"].__len__(), 2)
        self.assertEqual(100 * 5 + 10 * 3 + 6, 536)
        self.assertEqual(250 * 1.2 * .8, 240)
        self.assertEqual(17 - (17 - 9), 9)
        self.assertEqual([x["gold"] for x in t.TASKS],
                         ["20", "6", "2", "536", "240", "9"])

    def test_each_task_has_exact_pairings(self):
        for i in range(1, 7):
            task, a = t.plan(i)
            self.assertEqual([x["max_new_tokens"] for x in a],
                             [512, 512, 1024, 1024])
            self.assertEqual([x["seed"] for x in a], [9001, 9003, 9001, 9003])

    def test_dry_run_no_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            unused = Path(d) / "unused"
            with patch.object(t, "execute", side_effect=AssertionError("GPU forbidden")):
                with contextlib.redirect_stdout(StringIO()) as output:
                    self.assertEqual(t.main(["--dry-run", "--task-index", "1",
                                             "--out", str(unused)]), 0)
            cfg = json.loads(output.getvalue())
            self.assertEqual(cfg["planned_generations"], 4)
            self.assertFalse(cfg["gpu_used"])
            self.assertFalse(cfg["training_data_allowed"])
            self.assertFalse(unused.exists())

    def test_requires_explicit_gpu_flag(self):
        for args in (["--execute", "--task-index", "1"],
                     ["--dry-run", "--task-index", "1", "--confirm-gpu-4"],
                     ["--dry-run", "--task-index", "7"],
                     ["--execute", "--task-index", "0", "--confirm-gpu-4"]):
            with self.subTest(args=args):
                with contextlib.redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit) as err:
                        t.main(args)
                self.assertEqual(err.exception.code, 2)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(t, "execute", side_effect=AssertionError("GPU forbidden")):
                with contextlib.redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit):
                        t.main(["--execute", "--task-index", "1",
                                "--confirm-gpu-4", "--out", d])


if __name__ == "__main__":
    unittest.main()
