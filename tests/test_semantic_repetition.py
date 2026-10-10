"""RHAR 005 offline repetition detector tests."""
import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.semantic_repetition import analyze, analyze_file, normalized_operations


def sample(text, gold="43"):
    return {"id": "math", "expected": gold, "correct": True, "truncated": False,
            "total_tokens": 12, "reasoning_tokens": 10, "final_tokens": 2,
            "split_status": "generated_think_block",
            "full_generated_text": f"<think>{text}</think>Final answer: {gold}"}


class RepetitionTests(unittest.TestCase):
    def test_equivalent_spelling(self):
        ops = normalized_operations("5 × 12, 5*12, 5 times 12")
        self.assertEqual(len(ops), 3)
        self.assertEqual(len({x["canonical"] for x in ops}), 1)

    def test_commutative_and_noncommutative(self):
        ops = normalized_operations("5+12; 12 plus 5; 60 minus 17; 17 minus 60")
        self.assertEqual(ops[0]["canonical"], ops[1]["canonical"])
        self.assertNotEqual(ops[2]["canonical"], ops[3]["canonical"])

    def test_repeat_count(self):
        result = analyze(sample("5*12 is 60. Check again: 5 times 12 is 60."))
        self.assertEqual(result["repeat_count"], 1)
        self.assertFalse(result["semantic_redundancy_proven"])
        self.assertFalse(result["early_stop_safety_verified"])

    def test_unknown_gold(self):
        result = analyze(sample("5*12 is 60.", gold=""))
        self.assertIsNone(result["first_answer_step"])

    def test_missing_thinking(self):
        record = sample("")
        record.update(split_status="missing_think_markers", reasoning_tokens=None,
                      final_tokens=None, full_generated_text="Final answer: 43")
        self.assertEqual(analyze(record)["operations"], [])

    def test_file_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "records.jsonl"
            original = json.dumps(sample("60 minus 17 gives 43.")) + "\n"
            source.write_text(original, encoding="utf-8")
            self.assertEqual(analyze_file(source)["record_count"], 1)
            self.assertEqual(source.read_text(), original)


if __name__ == "__main__":
    unittest.main()
