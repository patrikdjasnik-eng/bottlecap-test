import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.token_boundaries import audit_record, audit_file


def sample(raw="<think>Answer is 43.</think>Final answer: 43", total=10):
    return {"id": "math", "expected": "43", "correct": True,
            "truncated": False, "total_tokens": total,
            "reasoning_tokens": total - 2, "final_tokens": 2,
            "split_status": "generated_think_block",
            "full_generated_text": raw}


class FakeTokenizer:
    def __init__(self, length_override=None):
        self.length_override = length_override

    def __call__(self, text, **kwargs):
        offsets = [(i, i + 1) for i in range(len(text))]
        if self.length_override is not None:
            offsets = offsets[:self.length_override]
        return {"input_ids": list(range(len(offsets))), "offset_mapping": offsets}


class TokenBoundaryTests(unittest.TestCase):
    def test_mismatch_fails_closed(self):
        r = audit_record(sample(), FakeTokenizer())
        self.assertEqual(r["boundary_status"], "retokenized_count_mismatch")
        self.assertIsNone(r["potential_saved_tokens"])

    def test_matching_character_offsets_do_not_claim_savings(self):
        raw = "<think>Answer is 43. Check again.</think>Final answer: 43"
        r = audit_record(sample(raw, len(raw)), FakeTokenizer())
        self.assertEqual(r["boundary_status"], "retokenized_boundary_only")
        self.assertGreater(r["retokenized_after_checkpoint"], 0)
        self.assertIsNone(r["measured_token_savings"])

    def test_inside_token_fails_closed(self):
        raw = "<think>Answer is 43.</think>Final answer: 43"
        record = sample(raw, 3)
        # Single token covers the entire string, crossing the checkpoint.
        class SingleToken:
            def __call__(self, text, **kwargs):
                return {"input_ids": [7, 8, 9], "offset_mapping": [(0, 19), (19, 30), (30, len(text))]}
        r = audit_record(record, SingleToken())
        self.assertEqual(r["boundary_status"], "checkpoint_inside_token")

    def test_no_checkpoint(self):
        r = sample("<think>Checking.</think>Final answer: 43")
        self.assertEqual(audit_record(r, FakeTokenizer())["boundary_status"], "no_checkpoint")

    def test_invalid_offsets(self):
        record = sample()
        class Invalid:
            def __call__(self, text, **kwargs):
                return {"input_ids": [1], "offset_mapping": [(2, 1)]}
        with self.assertRaises(ValueError):
            audit_record(record, Invalid())

    def test_read_only(self):
        raw = "<think>Answer is 43.</think>Final answer: 43"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "records.jsonl"
            content = json.dumps(sample(raw)) + "\n"
            path.write_text(content)
            self.assertEqual(audit_file(path, FakeTokenizer())["record_count"], 1)
            self.assertEqual(path.read_text(), content)


if __name__ == "__main__":
    unittest.main()
