"""CPU-only conversion tests; no GPU or training."""
import unittest

from diagnostics.safe_start_plan import BASE_REVISION, build_prompt
from diagnostics.safe_start_rollout_adapter import convert
from diagnostics.training_candidates import select
import hashlib


def question():
    return {"question_id": "gsm8k-train-06982", "question": "What is 1+1?",
            "gold_answer": "2", "source": "gsm8k",
            "source_revision": "740312add88f781978c0658806c59bc2815b9866",
            "split": "train", "task": "math"}


def sample(seed=9003, tokens=374, correct=True, truncated=False):
    q = question()
    prompt = build_prompt(q["question"])
    return {"question_id": q["question_id"], "source": "gsm8k",
            "source_revision": q["source_revision"], "split": "train",
            "task": "math", "gold_answer": "2", "prompt_hash": "sha256:" +
            hashlib.sha256(prompt.encode()).hexdigest(),
            "thinking_enabled": True, "research_only": True,
            "model": "Qwen/Qwen3-0.6B", "model_revision": BASE_REVISION,
            "reasoning_split_status": "generated_think_block",
            "generated_text": "<think>1+1=2</think>Final answer: 2",
            "total_generated_tokens": tokens, "seed": seed,
            "correct": correct, "truncated": truncated}


class RolloutAdapterTests(unittest.TestCase):
    def test_select_shorter_correct(self):
        rows = convert([sample(9002, 433), sample(9003, 374)], [question()])
        report = select(rows)
        self.assertEqual(report["selected_count"], 1)
        self.assertEqual(report["selected"][0]["total_tokens"], 374)

    def test_reject_truncation(self):
        rows = convert([sample(9001, 512, False, True)], [question()])
        self.assertEqual(select(rows)["selected_count"], 0)

    def test_reject_unknown_question(self):
        row = sample()
        row["question_id"] = "foreign"
        with self.assertRaises(ValueError):
            convert([row], [question()])

    def test_reject_wrong_gold(self):
        row = sample()
        row["gold_answer"] = "3"
        with self.assertRaises(ValueError):
            convert([row], [question()])

    def test_reject_tampered_prompt(self):
        row = sample()
        row["prompt_hash"] = "sha256:bad"
        with self.assertRaises(ValueError):
            convert([row], [question()])

    def test_reject_bad_provenance(self):
        row = sample()
        row["source"] = "svamp"
        with self.assertRaises(ValueError):
            convert([row], [question()])


if __name__ == "__main__":
    unittest.main()
