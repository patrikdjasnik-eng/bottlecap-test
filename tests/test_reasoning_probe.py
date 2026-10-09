"""CPU-only tests. python -m unittest tests.test_reasoning_probe -v"""
import unittest
from diagnostics.reasoning_probe import (
    CASES, grade_answer, parse_args, prompt_for,
    repeated_fourgrams, split_reasoning, summary_of,
)


class ProbeTests(unittest.TestCase):
    def test_prompt_only_specifies_final_answer_format(self):
        for case in CASES:
            content = prompt_for(case)[0]["content"]
            self.assertIn("Final answer:", content)
            self.assertNotIn("shorter", content)
            self.assertNotIn("skip reasoning", content)
            self.assertNotIn("disable", content)

    def test_prompt_has_no_example_answer_or_answer_leakage(self):
        expected_instruction = (
            "\n\nOn the last line, write 'Final answer:' followed by your answer."
        )
        for case in CASES:
            content = prompt_for(case)[0]["content"]
            self.assertEqual(content, case["question"] + expected_instruction)
            instruction = content[len(case["question"]):]
            self.assertNotIn("Final answer: 42", instruction)
            self.assertNotIn("Final answer: A", instruction)
            self.assertNotIn(case["answer"] if case["kind"] == "number" else "Final answer: " + case["answer"], instruction)

    def test_generated_thinking_block_counts_markers_and_eos(self):
        r = split_reasoning([10, 31, 32, 11, 40, 99], 10, 11, {99})
        self.assertEqual(r["reasoning_tokens"], 4)
        self.assertEqual(r["final_tokens"], 2)
        self.assertEqual(r["reasoning_body_ids"], [31, 32])
        self.assertEqual(r["final_ids"], [40, 99])
        self.assertEqual(r["split_status"], "generated_think_block")

    def test_prefilled_thinking_block(self):
        r = split_reasoning([31, 32, 11, 40, 99], 10, 11, {99}, prefilled_open=True)
        self.assertEqual((r["reasoning_tokens"], r["final_tokens"]), (3, 2))
        self.assertEqual(r["split_status"], "prefilled_think_block")

    def test_missing_markers_does_not_claim_zero_reasoning(self):
        r = split_reasoning([31, 32, 99], 10, 11, {99})
        self.assertIsNone(r["reasoning_tokens"])
        self.assertIsNone(r["final_tokens"])
        self.assertEqual(r["split_status"], "missing_think_markers")

    def test_unclosed_or_malformed(self):
        self.assertEqual(split_reasoning([10, 33], 10, 11, set())["split_status"],
                         "unclosed_think_block")
        self.assertEqual(split_reasoning([11, 33], 10, 11, set())["split_status"],
                         "malformed_think_block")

    def test_exact_grading(self):
        self.assertEqual(grade_answer("Final answer: 43", "43", "number", False),
                         (True, None))
        self.assertEqual(grade_answer("Final answer: 43", "42", "number", False),
                         (False, None))
        self.assertEqual(grade_answer("Final answer: b", "B", "choice", False),
                         (True, None))
        self.assertEqual(grade_answer("Final answer: 43 apples", "43", "number", False)[0], False)
        self.assertEqual(grade_answer("Final answer: 43", "43", "number", True),
                         (False, "truncated"))
        self.assertFalse(grade_answer("Final answer: 43\nmore text", "43", "number", False)[0])

    def test_repeated_fourgrams(self):
        self.assertEqual(repeated_fourgrams("one two three four one two three four"), 1)
        self.assertEqual(repeated_fourgrams("one two three"), 0)

    def test_arg_bounds(self):
        self.assertTrue(parse_args(["--dry-run", "--limit", "2"]).dry_run)
        for args in (["--limit", "0"], ["--samples", "0"], ["--limit", "100"]):
            with self.assertRaises(SystemExit):
                parse_args(args)

    def test_summary_counts_only_defined_splits(self):
        rows = [
            dict(correct=True, reasoning_tokens=10, final_tokens=2,
                 total_tokens=12, generation_seconds=2., tokens_per_second=6.),
            dict(correct=False, reasoning_tokens=None, final_tokens=None,
                 total_tokens=5, generation_seconds=1., tokens_per_second=5.),
        ]
        s = summary_of(rows)
        self.assertEqual(s["reasoning_split_successes"], 1)
        self.assertEqual(s["mean_reasoning_tokens"], 10)
        self.assertEqual(s["mean_total_tokens"], 8.5)
        self.assertEqual(s["exploratory_accuracy"], .5)
        self.assertFalse(s["official_benchmark"])


if __name__ == "__main__":
    unittest.main()
