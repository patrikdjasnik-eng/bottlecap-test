"""CPU-only tests of the RHAR offline correctness gate and review selector."""
import json
import tempfile
import unittest
from pathlib import Path
from diagnostics.offline_selector import assess_record, grade_final, main, read_jsonl, select_records


def sample(**overrides):
    r = {"question_id": "q-1", "source": "gsm8k", "source_revision": "train-rev-1",
         "split": "train", "task": "math", "gold_answer": "43",
         "model": "Qwen/Qwen3-0.6B", "model_revision": "pinned-model-rev",
         "prompt_hash": "sha256:fixed", "thinking_enabled": True,
         "seed": 1, "sample": 0, "generated_text": "<think>5*12=60; 60-17=43</think>\nFinal answer: 43<|im_end|>",
         "final_text": "\nFinal answer: 43", "reasoning_split_status": "generated_think_block",
         "truncated": False, "total_generated_tokens": 40,
         "reasoning_tokens": 34, "final_tokens": 6, "correct": True}
    r.update(overrides)
    return r


class GraderTests(unittest.TestCase):
    def test_strict_math_and_choice(self):
        self.assertEqual(grade_final("Final answer: 43", "43", "number"), (True, None))
        self.assertEqual(grade_final("Final answer: b", "B", "choice"), (True, None))
        self.assertEqual(grade_final("Final answer: 42", "43", "number"),
                         (False, "incorrect_answer"))
        self.assertEqual(grade_final("Final answer: 43 apples", "43", "number")[1],
                         "invalid_number_format")
        self.assertEqual(grade_final("Final answer: 43\nFinal answer: 43", "43", "number")[1],
                         "invalid_final_format")
        self.assertEqual(grade_final("Final answer: A", "A", "code")[1], "unsupported_task")

    def test_untrusted_correctness_flag_is_not_accepted(self):
        r = sample(generated_text="<think>wrong</think>Final answer: 42",
                   final_text="Final answer: 42", correct=True)
        self.assertEqual(assess_record(r)["reason"], "reported_correctness_mismatch")

    def test_missing_and_malformed_thinking_rejected(self):
        for raw in ("Final answer: 43", "<think>hi</think></think>Final answer: 43",
                    "<think>unfinished Final answer: 43"):
            self.assertEqual(assess_record(sample(generated_text=raw))["reason"],
                             "invalid_thinking_block")
        self.assertEqual(assess_record(sample(reasoning_split_status="missing_think_markers"))["reason"],
                         "invalid_thinking_block")

    def test_truncation_and_token_accounting(self):
        self.assertEqual(assess_record(sample(truncated=True))["reason"],
                         "truncated_or_unknown_termination")
        self.assertEqual(assess_record(sample(total_generated_tokens=39))["reason"],
                         "invalid_token_accounting")
        self.assertEqual(assess_record(sample(final_tokens=True))["reason"],
                         "invalid_token_accounting")

    def test_final_text_must_match_generated_body(self):
        self.assertEqual(assess_record(sample(final_text="Final answer: 99"))["reason"],
                         "inconsistent_final_text")

    def test_official_benchmarks_never_training_eligible(self):
        for source in ("svamp", "SVAMP-1", "MBPP+", "mbppplus_release", "bfcl", "BFCL_v4", "IFEVAL"):
            row = assess_record(sample(source=source))
            self.assertFalse(row["training_eligible"])
            self.assertEqual(row["reason"], "official_evaluation_source")

    def test_train_val_and_provenance_controls(self):
        for changes in ({"split":"val"}, {"prompt_hash": None},
                        {"thinking_enabled": False}, {"source_revision": None},
                        {"model_revision": None}):
            self.assertEqual(assess_record(sample(**changes))["reason"],
                             "missing_training_provenance")

    def test_legacy_diagnostic_is_analysis_only(self):
        rec = {"id": "arithmetic_apples", "category": "arithmetic", "expected": "43",
               "sample": 0, "seed": 9001, "correct": False,
               "split_status": "generated_think_block",
               "full_generated_text": "<think>mistake</think>\nFinal answer: 42<|im_end|>",
               "final_text": "\nFinal answer: 42", "truncated": False,
               "total_tokens": 325, "reasoning_tokens": 317, "final_tokens": 8}
        out = assess_record(rec)
        self.assertEqual(out["reason"], "incorrect_answer")
        self.assertTrue(out["legacy_diagnostic_kind_inferred"])
        self.assertEqual(out["task"], "number")
        self.assertFalse(out["training_eligible"])
        rec.update(correct=True, final_text="\nFinal answer: 43",
                   full_generated_text="<think>solution</think>\nFinal answer: 43<|im_end|>")
        out = assess_record(rec)
        self.assertTrue(out["correct"])
        self.assertFalse(out["training_eligible"])
        self.assertEqual(out["reason"], "missing_training_provenance")

    def test_legacy_known_case_with_original_metadata_is_incorrect(self):
        # Actual schema emitted by reasoning_probe.py, with no task/kind/source.
        row = {"id": "arithmetic_apples", "category": "arithmetic",
               "expected": "43", "sample": 0, "seed": 9001, "correct": False,
               "split_status": "generated_think_block",
               "full_generated_text": "<think>60-17=42</think>\n\nFinal answer: 42<|im_end|>",
               "final_text": "\n\nFinal answer: 42", "truncated": False,
               "total_tokens": 325, "reasoning_tokens": 317, "final_tokens": 8}
        outcomes, selected = select_records([row])
        self.assertEqual(outcomes[0]["reason"], "incorrect_answer")
        self.assertTrue(outcomes[0]["legacy_diagnostic_kind_inferred"])
        self.assertFalse(outcomes[0]["correct"])
        self.assertFalse(outcomes[0]["training_eligible"])
        self.assertEqual(selected, [])

    def test_legacy_known_choice_and_code_case(self):
        cases = [("logic_triangle", "logic", "A", "choice"),
                 ("code_output", "code_comprehension", "9", "number")]
        for identifier, category, expected, inferred in cases:
            row = {"id": identifier, "category": category, "expected": expected,
                   "correct": True, "split_status": "generated_think_block",
                   "full_generated_text": f"<think>ok</think>Final answer: {expected}<|im_end|>",
                   "final_text": f"Final answer: {expected}",
                   "truncated": False, "total_tokens": 8,
                   "reasoning_tokens": 4, "final_tokens": 4}
            result = assess_record(row)
            self.assertEqual(result["task"], inferred)
            self.assertTrue(result["correct"])
            self.assertFalse(result["training_eligible"])
            self.assertEqual(result["reason"], "missing_training_provenance")

    def test_legacy_kind_inference_rejects_mismatched_gold_or_category(self):
        original = {"id": "arithmetic_apples", "category": "arithmetic",
                    "expected": "43", "correct": True}
        for edit in ({"expected": "42"}, {"category": "logic"},
                     {"id": "unknown_case"}):
            row = {**original, **edit}
            self.assertEqual(assess_record(row)["reason"], "invalid_question_metadata")

    def test_no_legacy_fallback_when_source_is_supplied(self):
        row = {"id": "arithmetic_apples", "category": "arithmetic",
               "expected": "43", "source": "gsm8k"}
        out = assess_record(row)
        self.assertEqual(out["reason"], "invalid_question_metadata")
        self.assertFalse(out["legacy_diagnostic_kind_inferred"])

    def test_unique_shortest_correct_of_same_question(self):
        a = sample(seed=11, total_generated_tokens=40, reasoning_tokens=34)
        b = sample(seed=12, sample=1, total_generated_tokens=30, reasoning_tokens=24)
        c = sample(seed=13, sample=2, total_generated_tokens=35, reasoning_tokens=29)
        outcome, selected = select_records([a,b,c])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["seed"],12)
        self.assertEqual([v["selected"] for v in outcome], [False,True,False])
        self.assertTrue(selected[0]["review_only"])

    def test_single_correct_is_not_an_improvement(self):
        results, selected = select_records([sample()])
        self.assertFalse(selected)
        self.assertEqual(results[0]["reason"], "insufficient_correct_comparisons")

    def test_same_seed_not_counted_twice(self):
        outcome, selected = select_records([sample(), sample(sample=1)])
        self.assertFalse(selected)
        self.assertEqual(outcome[1]["reason"], "duplicate_seed")

    def test_conflicting_gold_or_prompt_blocks_selection(self):
        for update in ({"prompt_hash": "different"}, {"gold_answer": "44"}):
            outcome, selected = select_records([sample(), sample(seed=2, sample=1, **update)])
            self.assertFalse(selected)
            self.assertTrue(all(not x["selected"] for x in outcome))

    def test_choice_candidates(self):
        def as_choice(seed, total):
            return sample(question_id="qa", source="commonsense_qa", task="multiple_choice",
                          gold_answer="A", seed=seed, sample=seed, total_generated_tokens=total,
                          reasoning_tokens=total-6, generated_text="<think>choice</think>Final answer: a<|im_end|>",
                          final_text="Final answer: a")
        outcomes, selected = select_records([as_choice(1, 32),as_choice(2, 18)])
        self.assertEqual(selected[0]["total_generated_tokens"],18)

    def test_prefilled_thinking_supported(self):
        r = sample(generated_text="solution</think>Final answer: 43<|im_end|>",
                   final_text="Final answer: 43", reasoning_split_status="prefilled_think_block")
        self.assertTrue(assess_record(r)["training_eligible"])

    def test_cli_no_overwrite_and_no_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            inp = Path(directory)/"input.jsonl"
            out = Path(directory)/"out"
            inp.write_text(json.dumps(sample())+"\n",encoding="utf-8")
            self.assertEqual(main([str(inp), "--out", str(out)]),0)
            self.assertEqual(len(read_jsonl(out/"selected_for_review.jsonl")),0)
            self.assertTrue(json.loads((out/"summary.json").read_text())["no_training_performed"])
            with self.assertRaises(SystemExit):
                main([str(inp), "--out", str(out)])

    def test_bad_jsonl_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"x.jsonl"
            p.write_text('{"q":1}\n{broken\n',encoding="utf-8")
            with self.assertRaisesRegex(ValueError,":2: invalid JSON"):
                read_jsonl(p)


if __name__ == "__main__":
    unittest.main()
