"""CPU-only tests: no real download, no Qwen, no benchmark execution."""
from contextlib import redirect_stderr
from io import BytesIO, StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import safe_start_data as d


def rows(n=30):
    # Deliberately different synthetic statements so de-dup does not classify
    # each nearby numeric variant as a paraphrase of the same question.
    result = []
    for i in range(n):
        key = hashlib.sha256(str(i).encode()).hexdigest()
        question = (f"At {key[:12]} in {key[12:24]}, scientist {key[24:36]} "
                    f"counts {i+7} specimen, then adds three to the collection "
                    f"at {key[36:48]}. What is the final collection size?")
        result.append({"question": question, "answer": f"Add {i+7} and three. #### {i+10}"})
    return result


class SafeStartDataTests(unittest.TestCase):
    def test_revision_and_sha_are_pinned(self):
        self.assertEqual(len(d.DATASET_REVISION), 40)
        self.assertEqual(len(d.TRAIN_SHA256), 64)
        self.assertIn(d.DATASET_REVISION, d.TRAIN_URL)
        self.assertIn("main/train-00000-of-00001.parquet", d.TRAIN_URL)
        self.assertNotIn("/test-", d.TRAIN_URL)

    def test_gold_extraction_ignores_reference_reasoning(self):
        self.assertEqual(d.parse_gold("Reasoning contains 999. #### 1,200"), "1200")
        self.assertEqual(d.parse_gold("blah #### -3.5"), "-3.5")
        for value in ("42", "#### 42 things", "#### 1 #### 2", None):
            with self.assertRaises(ValueError):
                d.parse_gold(value)

    def test_deterministic_twelve_and_validates_planner(self):
        one, stats = d.pick_questions(rows())
        two, _ = d.pick_questions(list(rows()))
        self.assertEqual(one, two)
        self.assertEqual(len(one), 12)
        self.assertEqual(len({x["question_id"] for x in one}), 12)
        self.assertTrue(all(x["source_revision"] == d.DATASET_REVISION for x in one))
        self.assertFalse(stats["local_eval_audit_performed"])

    def test_ranking_does_not_consider_answer_value_or_model_success(self):
        base = rows()
        altered = [{**r, "answer": "Different chain. #### 900"} for r in base]
        a, _ = d.pick_questions(base)
        b, _ = d.pick_questions(altered)
        self.assertEqual([x["question_id"] for x in a], [x["question_id"] for x in b])

    def test_rejects_duplicates_and_too_small_a_source(self):
        with self.assertRaisesRegex(ValueError, "need 12"):
            d.pick_questions(rows(10))
        sample = rows(20)
        sample[1]["question"] = "  " + sample[0]["question"].upper() + "  "
        selected, _ = d.pick_questions(sample)
        self.assertEqual(len(selected), 12)
        self.assertNotEqual(len({d.normalize_question(x["question"]) for x in selected}), 11)

    def test_eval_exact_overlap_is_blocked(self):
        baseline, _ = d.pick_questions(rows())
        q = baseline[0]["question"]
        selected, stats = d.pick_questions(rows(), [d.normalize_question(q)])
        self.assertNotIn(q, [r["question"] for r in selected])
        self.assertEqual(stats["rejected_overlap_with_local_eval"], 1)
        self.assertTrue(stats["local_eval_audit_performed"])
        self.assertFalse(stats["overlap_audit_exhaustive"])

    def test_eval_near_overlap_is_blocked(self):
        baseline, _ = d.pick_questions(rows())
        q = baseline[0]["question"]
        self.assertTrue(d.close_match(d.normalize_question(q), d.normalize_question(q + "!")))
        selected, _ = d.pick_questions(rows(), [d.normalize_question(q + "!")])
        self.assertNotIn(q, [r["question"] for r in selected])

    def test_invalid_gold_and_answer_leakage_skipped(self):
        cases = rows(30)
        cases[0]["answer"] = "silly #### uncertain"
        cases[1]["question"] += " Final answer: 42"
        results, st = d.pick_questions(cases)
        self.assertEqual(len(results), 12)
        self.assertTrue(all("Final answer:" not in r["question"] for r in results))
        self.assertTrue(all(r["gold_answer"].lstrip("-").isdigit() for r in results))

    def test_eval_jsonl_reader_rejects_missing_messages(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "official.jsonl"
            p.write_text('{"id":"a"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing messages"):
                d.read_eval_prompts(p)

    def test_eval_jsonl_reader_only_user_prompts(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "official.jsonl"
            p.write_text(json.dumps({"answer": "top secret", "messages": [
                {"role": "user", "content": "How many marbles?"},
                {"role": "system", "content": "Do not leak"}]}) + "\n", encoding="utf-8")
            self.assertEqual(d.read_eval_prompts(p), ["how many marbles"])

    def test_cached_file_requires_matching_checksum(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "local.parquet"
            p.write_bytes(b"right")
            with patch.object(d, "TRAIN_SHA256", hashlib.sha256(b"right").hexdigest()):
                self.assertEqual(d.download_train(p), "verified_cached")
            with self.assertRaisesRegex(ValueError, "incorrect SHA"):
                d.download_train(p)
            self.assertEqual(p.read_bytes(), b"right")

    def test_content_hash_verified_download_without_network(self):
        payload = b"verified parquet bytes in unit test"
        expected = hashlib.sha256(payload).hexdigest()
        called = []
        def opener(url, timeout=None):
            called.append(url)
            return BytesIO(payload)
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "train.parquet"
            with patch.object(d, "TRAIN_SHA256", expected):
                self.assertEqual(d.download_train(p, opener=opener), "downloaded_and_verified")
            self.assertEqual(p.read_bytes(), payload)
            self.assertEqual(called, [d.TRAIN_URL])

    def test_bad_checksum_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "train.parquet"
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                d.download_train(p, opener=lambda *_args, **_kwargs: BytesIO(b"bad"))
            self.assertFalse(p.exists())
            self.assertEqual(list(Path(path).iterdir()), [])

    def test_create_review_only_outputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as path:
            out = Path(path) / "dataset"
            selected, stats = d.pick_questions(rows())
            result = d.create_review_files(out, selected, stats, "verified_cached")
            self.assertFalse(result["training_approved"])
            self.assertFalse(result["gpu_used"])
            self.assertEqual(result["overlap_audit_status"], "pending_local_eval_corpus")
            self.assertEqual(result["planned_generations"], 36)
            self.assertEqual(len((out / "questions.jsonl").read_text().splitlines()), 12)
            with self.assertRaises(FileExistsError):
                d.create_review_files(out, selected, stats, "verified_cached")

    def test_cli_requires_explicit_download(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as exc:
                d.main([])
        self.assertEqual(exc.exception.code, 2)

    def test_cli_end_to_end_all_io_mocked(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "out"
            with patch.object(d, "download_train", return_value="downloaded_and_verified"), \
                 patch.object(d, "read_parquet", return_value=rows()), \
                 patch("sys.stdout", new_callable=StringIO) as captured:
                self.assertEqual(d.main(["--download", "--out-dir", str(p)]), 0)
            self.assertEqual(len((p / "questions.jsonl").read_text().splitlines()), 12)
            self.assertIn('"status": "review_only"', captured.getvalue())
            self.assertFalse(json.loads((p / "selection-report.json").read_text())["training_approved"])


if __name__ == "__main__":
    unittest.main()
