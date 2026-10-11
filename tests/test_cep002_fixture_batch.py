"""CPU-only regression checks for the 12 CEP-002 synthetic examples."""

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.cep002_cpu import CandidateTrace, ExperienceLedger, verify
from diagnostics.cep002_fixture_batch import CASES, fixtures, run_batch


class CEP002FixtureBatchTests(unittest.TestCase):
    def test_twelve_distinct_fixture_problems(self):
        examples = fixtures()
        self.assertEqual(len(examples), 12)
        self.assertEqual(len({e.contract.task_id for e in examples}), 12)
        self.assertEqual(len({e.question for e in examples}), 12)

    def test_each_fixture_is_verified(self):
        for example in fixtures():
            with self.subTest(task=example.contract.task_id):
                self.assertEqual(verify(example.contract, example.candidate).status, "VERIFIED")

    def test_each_bad_intermediate_is_invalid(self):
        for example in fixtures():
            with self.subTest(task=example.contract.task_id):
                altered = example.candidate.raw_text.replace("=> ", "=> 999999", 1)
                candidate = replace(example.candidate, raw_text=altered)
                self.assertEqual(verify(example.contract, candidate).status, "INVALID")

    def test_each_wrong_final_is_invalid(self):
        for example in fixtures():
            with self.subTest(task=example.contract.task_id):
                altered = example.candidate.raw_text.rsplit("Final answer:", 1)[0] + "Final answer: 999999"
                self.assertEqual(verify(example.contract, replace(example.candidate, raw_text=altered)).status, "INVALID")

    def test_equivalent_but_unreviewed_relation_is_not_automatically_verified(self):
        for example in fixtures():
            with self.subTest(task=example.contract.task_id):
                first = example.contract.rules[0]
                before = f"{first.target} = {first.expression} =>"
                after = f"{first.target} = ({first.expression}) + 0 =>"
                altered = example.candidate.raw_text.replace(before, after, 1)
                self.assertNotEqual(altered, example.candidate.raw_text)
                self.assertEqual(verify(example.contract, replace(example.candidate, raw_text=altered)).status, "UNVERIFIED")

    def test_incomplete_or_narrative_trace_not_locked(self):
        example = fixtures()[0]
        incomplete = replace(example.candidate, completed=False)
        narrative = replace(example.candidate, raw_text="It looks correct.\n" + example.candidate.raw_text)
        self.assertEqual(verify(example.contract, incomplete).status, "TRUNCATED")
        self.assertEqual(verify(example.contract, narrative).status, "UNVERIFIED")

    def test_changed_gold_requires_new_review(self):
        example = fixtures()[0]
        self.assertEqual(verify(replace(example.contract, gold_answer="999"), example.candidate).status, "UNVERIFIED")

    def test_eval_source_is_never_accepted(self):
        example = fixtures()[0]
        for source in ("SVAMP", "MBPP+", "BFCL", "IFEval"):
            with self.subTest(source=source):
                altered = replace(example.contract, source=source)
                self.assertEqual(verify(altered, example.candidate).status, "UNVERIFIED")

    def test_token_measurement_not_fabricated(self):
        self.assertTrue(all(example.candidate.measured_tokens is None for example in fixtures()))

    def test_batch_produces_only_synthetic_report(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic"
            report = run_batch(output)
            self.assertEqual(report["verified"], 12)
            self.assertEqual(report["nonverified"], 0)
            self.assertFalse(report["training_performed"])
            self.assertFalse(report["independent_semantic_audit_performed"])
            self.assertFalse(report["benchmark_dataset_used"])
            self.assertTrue((output / "xp-history.jsonl").is_file())
            with (output / "records.jsonl").open(encoding="utf-8") as stream:
                records = [json.loads(line) for line in stream]
            self.assertEqual(len(records), 12)
            self.assertTrue(all(record["xp_records"] == 1 for record in records))

    def test_existing_results_are_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic"
            run_batch(output)
            before = (output / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run_batch(output)
            self.assertEqual(before, (output / "summary.json").read_bytes())

    def test_xp_records_only_passed_candidates(self):
        with TemporaryDirectory() as tmp:
            ledger = ExperienceLedger(Path(tmp) / "experiences.jsonl")
            example = fixtures()[0]
            ledger.record(example.contract, example.candidate)
            invalid = replace(
                example.candidate,
                candidate_id="wrong",
                raw_text=example.candidate.raw_text.replace("Final answer: 43", "Final answer: 42"),
            )
            ledger.record(example.contract, invalid)
            self.assertEqual(len(ledger.xp(example.contract.task_id)), 1)
            self.assertEqual(ledger.xp(example.contract.task_id)[0]["candidate_id"], example.candidate.candidate_id)


if __name__ == "__main__":
    unittest.main()
