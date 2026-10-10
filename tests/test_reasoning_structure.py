"""Unit tests for RHAR 003 offline structure analysis."""
import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.reasoning_structure import analyze_jsonl, analyze_record, main


def fixture():
    return {
        "id": "arithmetic_apples", "correct": True, "truncated": False,
        "total_tokens": 12, "reasoning_tokens": 10, "final_tokens": 2,
        "split_status": "generated_think_block",
        "full_generated_text": "<think>one two three four one two three four</think>Final answer: 43",
    }


class StructureTests(unittest.TestCase):
    def test_counts_without_claiming_waste(self):
        result = analyze_record(fixture())
        self.assertEqual(result["repeated_fourgram_occurrences"], 1)
        self.assertEqual(result["reasoning_share_pct"], 83.33)
        self.assertFalse(result["semantic_step_quality_assessed"])
        self.assertFalse(result["repetition_is_waste_proof"])

    def test_reject_mismatched_token_accounting(self):
        row = fixture()
        row["reasoning_tokens"] = 11
        with self.assertRaises(ValueError):
            analyze_record(row)

    def test_reject_falsely_recognized_markers(self):
        row = fixture()
        row["full_generated_text"] = "Final answer: 43"
        with self.assertRaises(ValueError):
            analyze_record(row)

    def test_unknown_split_does_not_invent_metrics(self):
        row = fixture()
        row.update(split_status="missing_think_markers", reasoning_tokens=None,
                   final_tokens=None, full_generated_text="Final answer: 43")
        result = analyze_record(row)
        self.assertIsNone(result["reasoning_word_count"])
        self.assertIsNone(result["reasoning_share_pct"])

    def test_invalid_json_has_line_number(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "records.jsonl"
            source.write_text("{}\nnot-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                analyze_jsonl(source)

    def test_file_read_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "records.jsonl"
            target = Path(root) / "report.json"
            source.write_text(json.dumps(fixture()) + "\n", encoding="utf-8")
            self.assertEqual(main([str(source), "--out", str(target)]), 0)
            self.assertEqual(json.loads(target.read_text())["record_count"], 1)
            with self.assertRaises(FileExistsError):
                main([str(source), "--out", str(target)])
            self.assertEqual(source.read_text(), json.dumps(fixture()) + "\n")


if __name__ == "__main__":
    unittest.main()
