"""CPU-only RHAR 006 tests."""
import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.reasoning_checkpoint import analyze_record, analyze_file, check_operations


def fixture(text, correct=True):
    return {"id": "math", "expected": "43", "correct": correct,
            "truncated": False, "total_tokens": 12,
            "reasoning_tokens": 10, "final_tokens": 2,
            "split_status": "generated_think_block",
            "full_generated_text": f"<think>{text}</think>Final answer: 43"}


class CheckpointTests(unittest.TestCase):
    def test_arithmetic_consistency(self):
        found = check_operations("5 times 12 is 60. 60 minus 17 is 43.")
        self.assertEqual([x["arithmetic_consistent"] for x in found], [True, True])

    def test_detect_wrong_arithmetic(self):
        found = check_operations("5 times 12 is 61.")
        self.assertEqual(found[0]["arithmetic_consistent"], False)

    def test_candidate_not_proven_early_stop(self):
        result = analyze_record(fixture("There are 43 remaining. Check again."))
        self.assertIsNotNone(result["candidate_checkpoint"])
        self.assertGreater(result["reasoning_characters_after_checkpoint"], 0)
        self.assertIsNone(result["measured_token_savings"])
        self.assertFalse(result["early_stop_safety_verified"])

    def test_wrong_answer_no_checkpoint(self):
        result = analyze_record(fixture("There are 43 remaining.", correct=False))
        self.assertIsNone(result["candidate_checkpoint"])

    def test_missing_markers(self):
        record = fixture("")
        record.update(split_status="missing_think_markers", reasoning_tokens=None,
                      final_tokens=None, full_generated_text="Final answer: 43")
        self.assertIsNone(analyze_record(record)["candidate_checkpoint"])

    def test_read_only_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            content = json.dumps(fixture("The answer is 43.")) + "\n"
            path.write_text(content, encoding="utf-8")
            self.assertEqual(analyze_file(path)["record_count"], 1)
            self.assertEqual(path.read_text(), content)


if __name__ == "__main__":
    unittest.main()
