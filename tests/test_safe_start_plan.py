"""Safe Start plan verification: CPU-only, no GPU, model, or network."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from diagnostics.safe_start_plan import (
    BASE_MODEL, BASE_REVISION, INSTRUCTION, MAX_NEW_TOKENS,
    QUESTION_COUNT, SAMPLES_PER_QUESTION, SEEDS, build_prompt,
    main, plan_attempts, read_questions, summary, validate_questions,
)

REVISION = "f" * 40


def questions():
    return [{"question_id": f"gsm8k-{i:03}", "question": f"What is {i}+{i+1}?",
             "gold_answer": str(2 * i + 1), "source": "gsm8k",
             "source_revision": REVISION, "split": "train", "task": "math"}
            for i in range(QUESTION_COUNT)]


class SafeStartPlanTests(unittest.TestCase):
    def test_exactly_twelve_problems_and_thirty_six_attempts(self):
        planned = plan_attempts(questions())
        self.assertEqual((len(planned), QUESTION_COUNT, SAMPLES_PER_QUESTION), (36, 12, 3))
        self.assertEqual(len({(x["question_id"], x["seed"]) for x in planned}), 36)

    def test_all_seeds_and_sampling_consistent(self):
        planned = plan_attempts(questions())
        for i in range(0, 36, 3):
            self.assertEqual(tuple(a["seed"] for a in planned[i:i + 3]), SEEDS)
        for item in planned:
            self.assertTrue(item["thinking_enabled"])
            self.assertTrue(item["plan_only"])
            self.assertEqual(item["model"], BASE_MODEL)
            self.assertEqual(item["model_revision"], BASE_REVISION)
            self.assertEqual(item["max_new_tokens"], MAX_NEW_TOKENS)
            self.assertEqual(item["sampling"], {"temperature": .6, "top_p": .95, "top_k": 20})

    def test_no_gold_or_question_text_in_manifest(self):
        attempts = plan_attempts(questions())
        serialized = json.dumps(attempts)
        self.assertNotIn("gold_answer", serialized)
        self.assertNotIn('"question":', serialized)
        self.assertEqual(len({a["prompt_hash"] for a in attempts}), QUESTION_COUNT)

    def test_prompt_has_no_example_answer_or_shortening(self):
        user_prompt = build_prompt("How much is 2 plus 3?")
        self.assertEqual(user_prompt, "How much is 2 plus 3?\n\n" + INSTRUCTION)
        self.assertNotIn("Final answer: 42", user_prompt)
        self.assertNotIn("shorter", user_prompt.lower())
        self.assertNotIn("skip thinking", user_prompt.lower())

    def test_fail_closed_on_count(self):
        for rows in ([], questions()[:-1], questions() + questions()[:1], None):
            with self.assertRaisesRegex(ValueError, "exactly 12 questions"):
                validate_questions(rows)

    def test_rejects_eval_sources_and_wrong_splits(self):
        for changed in ({"source": "svamp"}, {"source": "mbpp"},
                        {"source": "ifeval"}, {"source": "bfcl"},
                        {"split": "validation"}, {"task": "code"}):
            rows = questions()
            rows[0].update(changed)
            with self.assertRaisesRegex(ValueError, "only GSM8K train/math"):
                plan_attempts(rows)

    def test_requires_pinned_source_revision(self):
        for revision in ("main", "x" * 40, "", None):
            rows = questions()
            rows[0]["source_revision"] = revision
            with self.assertRaisesRegex(ValueError, "pinned 40-hex"):
                validate_questions(rows)
        rows = questions()
        rows[0]["source_revision"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "one pinned source revision"):
            validate_questions(rows)

    def test_rejects_duplicate_ids_and_text(self):
        rows = questions()
        rows[-1]["question_id"] = rows[0]["question_id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_questions(rows)
        rows = questions()
        rows[-1]["question"] = "  WHAT  is 0+1? "
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_questions(rows)

    def test_rejects_bad_answers_and_unknown_fields(self):
        for answer in ("A", "seven", 7, "", "43 apples"):
            rows = questions()
            rows[0]["gold_answer"] = answer
            with self.assertRaisesRegex(ValueError, "numeric string"):
                validate_questions(rows)
        rows = questions()
        rows[0]["prompt"] = "Final answer: 999"
        with self.assertRaisesRegex(ValueError, "exact schema"):
            validate_questions(rows)

    def test_rejects_invalid_id_and_empty_question(self):
        rows = questions()
        rows[0]["question_id"] = "  "
        with self.assertRaisesRegex(ValueError, "invalid question_id"):
            validate_questions(rows)
        rows = questions()
        rows[0]["question"] = "   "
        with self.assertRaisesRegex(ValueError, "empty question"):
            validate_questions(rows)

    def test_dry_run_without_data_does_not_touch_files(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.chdir(folder):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(main(["--dry-run"]), 0)
                result = json.loads(stdout.getvalue())
                self.assertEqual(result["planned_generations"], 36)
                self.assertTrue(result["thinking_enabled"])
                self.assertFalse(result["dataset_downloaded"])
                self.assertFalse(result["gpu_used"])
                self.assertFalse(result["training_performed"])
                self.assertEqual(list(Path(folder).iterdir()), [])

    def test_dry_run_with_existing_local_jsonl(self):
        with tempfile.TemporaryDirectory() as folder:
            input_file = Path(folder) / "questions.jsonl"
            input_file.write_text("".join(json.dumps(r) + "\n" for r in questions()), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                main(["--dry-run", "--questions", str(input_file)])
            out = json.loads(stdout.getvalue())
            self.assertEqual(out["validated_local_questions"], 12)
            self.assertEqual(out["validated_planned_attempts"], 36)
            self.assertEqual(len(out["question_ids"]), 12)
            self.assertEqual(list(Path(folder).iterdir()), [input_file])

    def test_read_jsonl_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            for contents in ('{"ok":true}\n{broken\n', '[1]\n'):
                path.write_text(contents, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "line"):
                    read_questions(path)

    def test_fail_without_dry_run(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                main([])
        self.assertEqual(result.exception.code, 2)

    def test_summary_contains_no_actual_model_results(self):
        result = summary(questions())
        self.assertEqual(result["status"], "plan_only")
        self.assertNotIn("correct_responses", result)
        self.assertNotIn("token_savings", result)
        self.assertFalse(result["official_benchmark"])


if __name__ == "__main__":
    unittest.main()
