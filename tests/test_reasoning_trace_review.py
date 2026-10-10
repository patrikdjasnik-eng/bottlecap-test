import unittest
from diagnostics.reasoning_trace_review import inspect


def sample():
    return {"seed": 9003, "question_id": "gsm8k-train-06982",
            "correct": True, "truncated": False, "total_generated_tokens": 374,
            "reasoning_tokens": 366, "reasoning_split_status": "generated_think_block",
            "generated_text": "<think>1+1=2</think>Final answer: 2"}


class TraceReviewTests(unittest.TestCase):
    def test_outputs_full_trace_without_certifying_it(self):
        report = inspect([sample()], 9003)
        self.assertEqual(report["thinking"], "1+1=2")
        self.assertFalse(report["semantic_reasoning_verified"])

    def test_wrong_answer_rejected(self):
        row = sample()
        row["correct"] = False
        with self.assertRaises(ValueError):
            inspect([row], 9003)

    def test_missing_seed_rejected(self):
        with self.assertRaises(ValueError):
            inspect([sample()], 9002)

    def test_malformed_split_rejected(self):
        row = sample()
        row["generated_text"] = "1+1=2"
        with self.assertRaises(ValueError):
            inspect([row], 9003)


if __name__ == "__main__":
    unittest.main()
