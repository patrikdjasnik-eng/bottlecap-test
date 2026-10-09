"""CPU-only preparation tests: never download/load a model or start CUDA."""
import contextlib
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import safe_start_generate as g
from diagnostics.offline_selector import assess_record
from diagnostics.safe_start_overlap import SOURCES

REVISION = "740312add88f781978c0658806c59bc2815b9866"
PARQUET_SHA = "ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d"


def candidates():
    return [{"question_id": f"gsm8k-train-{i:05d}",
             "question": f"Math problem {i}: there are {i+30} units and eleven are sold.",
             "gold_answer": str(i+19), "source": "gsm8k",
             "source_revision": REVISION, "split": "train", "task": "math"}
            for i in range(12)]


def fixtures(folder):
    root = Path(folder)
    q, s, a = (root / n for n in
               ("questions.jsonl", "selection-report.json", "overlap-audit.json"))
    rows = candidates()
    q.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    hashes = [hashlib.sha256(x["question"].encode()).hexdigest() for x in rows]
    chosen = {"status": "review_only", "training_approved": False,
              "dataset_revision": REVISION, "train_parquet_sha256": PARQUET_SHA,
              "selected_question_ids": [r["question_id"] for r in rows],
              "selected_question_sha256": hashes}
    sources = [{"name": x["name"], "family": x["family"], "url": x["url"],
                "sha256_of_decoded_bytes": x.get("expected_sha256", "1"*64),
                "known_sha256_pin_checked": "expected_sha256" in x,
                "prompt_count": 100} for x in SOURCES]
    audit = {"status": "review_only", "audit_type": "heuristic_text_overlap_screen",
             "audit_result": "no_matches_in_screened_sources",
             "training_approved": False, "screened_all_declared_sources": True,
             "screened_source_count": 6, "screened_families": ["BFCL","IFEval","MBPP+","SVAMP"],
             "question_count": 12, "question_ids": chosen["selected_question_ids"],
             "question_sha256": hashes, "dataset_revision": REVISION,
             "potential_match_count": 0, "potential_matches": [],
             "overlap_audit_exhaustive": False, "semantic_paraphrases_ruled_out": False,
             "original_candidate_files_modified": False,
             "sources": sources, "screened_prompt_count": 600}
    s.write_text(json.dumps(chosen), encoding="utf-8")
    a.write_text(json.dumps(audit), encoding="utf-8")
    return q, s, a


class ToyTokenizer:
    def decode(self, ids, skip_special_tokens):
        mapping = {10:"<think>", 11:"</think>", 21:"Reasoning steps",
                   22:"\nFinal answer: 19", 23:"\nFinal answer: 20",
                   99:"<|im_end|>", 31:"unfinished"}
        return "".join(mapping[x] for x in ids
                       if not (skip_special_tokens and x in (10, 11, 99)))


def attempt():
    return {"sample":0, "seed":9001, "model":g.BASE_MODEL,
            "model_revision":g.BASE_REVISION, "prompt_hash":"sha256:fixed",
            "sampling":{"temperature":0.6,"top_p":0.95,"top_k":20},
            "max_new_tokens":512}


class SafeStartGenerateTests(unittest.TestCase):
    def test_twelve_candidates_make_36_seeded_attempts(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a = fixtures(folder)
            rows, attempts = g.load_approved_inputs(q,s,a)
            self.assertEqual((len(rows),len(attempts)), (12,36))
            self.assertEqual([x["seed"] for x in attempts[:3]],[9001,9002,9003])

    def test_original_question_order_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a = fixtures(folder)
            rows,_=g.load_approved_inputs(q,s,a)
            self.assertEqual([r["question_id"] for r in rows],
                             [r["question_id"] for r in candidates()])

    def test_missing_audit_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder);a.unlink()
            with self.assertRaises(FileNotFoundError):g.load_approved_inputs(q,s,a)

    def test_changed_candidate_question_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            q.write_text(q.read_text().replace("Math problem 0:", "Math problem 999:"))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_audit_with_found_match_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["potential_match_count"]=1
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_audit_wrong_question_hash_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["question_sha256"][0]="0"*64
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_missing_official_source_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["sources"].pop()
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_wrong_svamp_content_hash_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["sources"][0]["sha256_of_decoded_bytes"]="0"*64
            a.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                g.load_approved_inputs(q,s,a)

    def test_source_url_tampering_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["sources"][2]["url"]="https://untrusted/"
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_source_invalid_hash_encoding_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["sources"][2]["sha256_of_decoded_bytes"]="z"*64
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_unexpected_training_approval_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            data=json.loads(a.read_text());data["training_approved"]=True
            a.write_text(json.dumps(data))
            with self.assertRaises(ValueError):g.load_approved_inputs(q,s,a)

    def test_cpu_dry_run_does_not_call_executor_or_write_output(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            before=[p.read_bytes() for p in (q,s,a)]
            output=Path(folder)/"no-output"
            with patch.object(g,"execute",side_effect=AssertionError("GPU forbidden")):
                with contextlib.redirect_stdout(StringIO()) as stdout:
                    self.assertEqual(g.main(["--dry-run","--questions",str(q),
                        "--selection-report",str(s),"--overlap-audit",str(a),
                        "--out",str(output)]),0)
            result=json.loads(stdout.getvalue())
            self.assertEqual(result["planned_generations"],36)
            self.assertFalse(result["model_loaded"])
            self.assertFalse(result["gpu_used"])
            self.assertFalse(result["training_approved"])
            self.assertFalse(output.exists())
            self.assertEqual([p.read_bytes() for p in (q,s,a)],before)

    def test_dry_run_hashes_inputs_not_gold_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            q,s,a=fixtures(folder)
            rows,attempts=g.load_approved_inputs(q,s,a)
            config=g.planned_config(rows,attempts,{"questions":q,"selection_report":s,"overlap_audit":a})
            self.assertEqual(config["input_sha256"]["questions"],hashlib.sha256(q.read_bytes()).hexdigest())
            self.assertEqual(len(config["input_sha256"]),3)
            self.assertNotIn("gold_answer",json.dumps(config))
            self.assertEqual(config["max_new_tokens"],512)

    def test_gpu_execution_requires_both_flags(self):
        with contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as err:g.main(["--execute"])
        self.assertEqual(err.exception.code,2)

    def test_no_implicit_mode(self):
        with contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as err:g.main([])
        self.assertEqual(err.exception.code,2)

    def test_gpu_flag_rejected_on_dry_run(self):
        with contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as err:g.main(["--dry-run","--confirm-gpu-36"])
        self.assertEqual(err.exception.code,2)

    def test_generated_thinking_counts_all_tokens(self):
        r=g.build_record(candidates()[0],attempt(),[10,21,11,22,99],10,11,{99},
                         False,ToyTokenizer(),1.0)
        self.assertTrue(r["correct"])
        self.assertEqual((r["total_generated_tokens"],r["reasoning_tokens"],r["final_tokens"]),(5,3,2))
        self.assertEqual(r["reasoning_split_status"],"generated_think_block")
        self.assertTrue(assess_record(r)["training_eligible"])

    def test_prefilled_think_is_handled(self):
        r=g.build_record(candidates()[0],attempt(),[21,11,22,99],10,11,{99},
                         True,ToyTokenizer(),1.0)
        self.assertTrue(r["correct"])
        self.assertEqual(r["reasoning_split_status"],"prefilled_think_block")
        self.assertEqual(r["reasoning_tokens"]+r["final_tokens"],4)
        self.assertNotIn("<think>",r["generated_text"])
        self.assertTrue(assess_record(r)["training_eligible"])

    def test_truncated_answer_never_correct(self):
        r=g.build_record(candidates()[0],attempt(),[10,21,11,22],10,11,{99},
                         False,ToyTokenizer(),1.0)
        self.assertTrue(r["truncated"])
        self.assertFalse(r["correct"])
        self.assertEqual(r["grading_error"],"truncated")
        self.assertEqual(assess_record(r)["reason"],"truncated_or_unknown_termination")

    def test_missing_thinking_is_unknown_not_zero(self):
        r=g.build_record(candidates()[0],attempt(),[22,99],10,11,{99},
                         False,ToyTokenizer(),1.0)
        self.assertIsNone(r["reasoning_tokens"])
        self.assertIsNone(r["final_tokens"])

    def test_wrong_final_answer_rejected(self):
        r=g.build_record(candidates()[0],attempt(),[10,21,11,23,99],10,11,{99},
                         False,ToyTokenizer(),1.0)
        self.assertFalse(r["correct"])

    def test_summary_only_averages_known_reasoning_splits(self):
        data=[{"correct":True,"truncated":False,"reasoning_tokens":3,"final_tokens":2,
               "total_generated_tokens":5,"generation_seconds":1.0},
              {"correct":False,"truncated":True,"reasoning_tokens":None,"final_tokens":None,
               "total_generated_tokens":9,"generation_seconds":2.0}]
        out=g.summarize(data)
        self.assertEqual(out["mean_total_generated_tokens"],7)
        self.assertEqual(out["mean_reasoning_tokens_known_splits_only"],3)
        self.assertEqual(out["valid_reasoning_splits"],1)
        self.assertFalse(out["token_savings_demonstrated"])

    def test_missing_think_tokens_rejected(self):
        class BadTokenizer:
            unk_token_id=0
            def convert_tokens_to_ids(self, token):return 0
        with self.assertRaisesRegex(RuntimeError,"marker"):
            g.thinking_ids(BadTokenizer())

    def test_no_training_or_benchmark_claim(self):
        report=g.summarize([])
        self.assertFalse(report["training_approved"])
        self.assertFalse(report["training_performed"])
        self.assertFalse(report["official_benchmark"])
        self.assertFalse(report["model_updated"])


if __name__ == "__main__":
    unittest.main()
