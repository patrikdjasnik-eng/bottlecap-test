import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.reasoning_steps import review_record, analyze_file, main


def sample(text):
    return {"id": "x", "correct": True, "truncated": False, "total_tokens": 12,
            "reasoning_tokens": 10, "final_tokens": 2,
            "split_status": "generated_think_block",
            "full_generated_text": "<think>" + text + "</think>Final answer: 43"}


class ReasoningStepsTests(unittest.TestCase):
    def test_arithmetic_and_repeat(self):
        r = review_record(sample("5 * 12 = 60. Check again. 5 * 12 = 60."))
        self.assertGreaterEqual(r["flag_count"], 2)
        self.assertEqual(len(r["steps"]), 3)
        self.assertTrue(r["steps"][0]["repeated_equation"])
        self.assertFalse(r["semantic_redundancy_proven"])

    def test_bad_equation_is_not_hidden(self):
        r = review_record(sample("5 * 12 = 70."))
        self.assertFalse(r["steps"][0]["equations"][0]["arithmetic_consistent"])

    def test_no_thinking_no_invented_steps(self):
        r = sample("irrelevant")
        r.update(split_status="missing_think_markers", reasoning_tokens=None,
                 final_tokens=None, full_generated_text="Final answer: 43")
        self.assertEqual(review_record(r)["steps"], [])

    def test_invalid_accounting(self):
        r = sample("thinking")
        r["total_tokens"] = 11
        with self.assertRaises(ValueError):
            review_record(r)

    def test_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "records.jsonl"
            target = Path(tmp) / "report.json"
            source.write_text(json.dumps(sample("5 + 2 = 7.")) + "\n", encoding="utf-8")
            self.assertEqual(analyze_file(source)["record_count"], 1)
            self.assertEqual(main([str(source), "--out", str(target)]), 0)
            with self.assertRaises(FileExistsError):
                main([str(source), "--out", str(target)])
            self.assertIn("5 + 2 = 7", source.read_text())


if __name__ == "__main__":
    unittest.main()
