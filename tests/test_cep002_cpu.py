"""Deterministic CPU-only behavior and adversarial safeguards for CEP-002."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.cep002_cpu import (
    CandidateTrace, ExperienceLedger, StepRule, TaskContract,
    parse_expression, verify,
)


def contract() -> TaskContract:
    return TaskContract(
        task_id="manual-boxes-1", source="synthetic/manual",
        facts={"boxes": "5", "per_box": "12", "sold": "17"},
        rules=(StepRule("total", "boxes * per_box"),
               StepRule("remaining", "total - sold")),
        final_target="remaining", gold_answer="43", reviewed_by="manual-test-review",
        overlap_screen_passed=True,
    )


def trace(identifier: str = "correct", raw: str | None = None,
          tokens: int | None = 20) -> CandidateTrace:
    return CandidateTrace(identifier, "manual-boxes-1", raw or (
        "total = boxes * per_box => 60\nremaining = total - sold => 43\nFinal answer: 43"
    ), True, tokens)


class VerifierTests(unittest.TestCase):
    def test_valid_audited_trace(self):
        self.assertEqual(verify(contract(), trace()).status, "VERIFIED")

    def test_false_final(self):
        candidate = trace(raw=trace().raw_text.replace("Final answer: 43", "Final answer: 42"))
        self.assertEqual(verify(contract(), candidate).status, "INVALID")

    def test_wrong_math(self):
        candidate = trace(raw=trace().raw_text.replace("=> 60", "=> 61"))
        self.assertEqual(verify(contract(), candidate).status, "INVALID")

    def test_correct_final_wrong_relation_is_not_verified(self):
        candidate = trace(raw=trace().raw_text.replace("boxes * per_box", "boxes + 55"))
        self.assertEqual(verify(contract(), candidate).status, "UNVERIFIED")

    def test_wrong_relation_and_wrong_intermediate(self):
        candidate = trace(raw=trace().raw_text.replace("boxes * per_box => 60", "boxes + per_box => 60"))
        self.assertEqual(verify(contract(), candidate).status, "INVALID")

    def test_truncated(self):
        self.assertEqual(verify(contract(), replace(trace(), completed=False)).status, "TRUNCATED")

    def test_narrative_unverified(self):
        candidate = trace(raw="I think it is 43.\n" + trace().raw_text)
        self.assertEqual(verify(contract(), candidate).status, "UNVERIFIED")

    def test_missing_step_unverified(self):
        candidate = trace(raw="remaining = total - sold => 43\nFinal answer: 43")
        self.assertEqual(verify(contract(), candidate).status, "UNVERIFIED")

    def test_unreviewed_contract(self):
        self.assertEqual(verify(replace(contract(), reviewed_by=""), trace()).status, "UNVERIFIED")

    def test_official_eval_source_rejected(self):
        self.assertEqual(verify(replace(contract(), source="SVAMP"), trace()).status, "UNVERIFIED")

    def test_overlap_flag_required(self):
        self.assertEqual(verify(replace(contract(), overlap_screen_passed=False), trace()).status, "UNVERIFIED")

    def test_gold_mismatch_contract(self):
        self.assertEqual(verify(replace(contract(), gold_answer="42"), trace()).status, "UNVERIFIED")

    def test_safe_expression_rejects_calls_and_powers(self):
        for expr in ("__import__('os').system('echo X')", "2 ** 9999", "a[0]", "a.__class__"):
            with self.subTest(expr=expr), self.assertRaises(ValueError):
                parse_expression(expr)

    def test_wrong_task(self):
        self.assertEqual(verify(contract(), replace(trace(), task_id="different")).status, "UNVERIFIED")


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.ledger = ExperienceLedger(Path(self.tmp.name) / "xp.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_verified_in_xp_and_best_first(self):
        self.ledger.record(contract(), trace("a", tokens=30))
        self.ledger.record(contract(), trace("b", tokens=15))
        self.ledger.record(contract(), trace("c", tokens=17))
        self.ledger.record(contract(), trace("d", tokens=45))
        bad = trace("bad", trace().raw_text.replace("43", "42"))
        self.ledger.record(contract(), bad)
        self.assertEqual([row["candidate_id"] for row in self.ledger.xp("manual-boxes-1")], ["b"])

    def test_history_is_append_only_and_duplicate_ids_rejected(self):
        self.ledger.record(contract(), trace())
        before = self.ledger.path.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ledger.record(contract(), trace())
        self.assertEqual(before, self.ledger.path.read_text(encoding="utf-8"))

    def test_no_false_correction_of_locked_solution(self):
        self.ledger.record(contract(), trace("old"))
        self.ledger.record(contract(), trace("trigger"))
        self.ledger.propose_recheck("old", "trigger", "New answer says 42")
        candidate = trace("repair", trace().raw_text.replace("43", "42"))
        self.assertEqual(self.ledger.resolve_recheck(contract(), "old", candidate), "REJECTED_CORRECTION")
        self.assertEqual([row["candidate_id"] for row in self.ledger.xp("manual-boxes-1")], ["old"])
        self.assertFalse(any(row["type"] == "attempt" and row["candidate_id"] == "repair" for row in self.ledger.events()))

    def test_verified_repair_of_proven_error(self):
        wrong = trace("old", trace().raw_text.replace("=> 60", "=> 61"))
        self.ledger.record(contract(), wrong)
        self.ledger.record(contract(), trace("trigger"))
        self.ledger.propose_recheck("old", "trigger", "Incorrect multiplication in old trace")
        self.assertEqual(self.ledger.resolve_recheck(contract(), "old", trace("repair")), "ACCEPTED_VERIFIED_REPAIR")
        records = self.ledger.events()
        self.assertEqual([row for row in records if row["type"] == "attempt" and row["candidate_id"] == "old"][0]["raw_text"], wrong.raw_text)
        self.assertIn("repair", [row["candidate_id"] for row in self.ledger.xp("manual-boxes-1")])
        with self.assertRaises(ValueError):
            self.ledger.resolve_recheck(contract(), "old", trace("other-repair"))

    def test_unverified_old_is_not_declared_wrong(self):
        self.ledger.record(contract(), trace("old", raw="Narrative.\n" + trace().raw_text))
        self.ledger.record(contract(), trace("trigger"))
        self.ledger.propose_recheck("old", "trigger", "Suspected incomplete proof")
        self.assertEqual(self.ledger.resolve_recheck(contract(), "old", trace("repair")), "UNVERIFIED")

    def test_changed_contract_disputes_existing_lock(self):
        self.ledger.record(contract(), trace("old"))
        self.ledger.record(contract(), trace("trigger"))
        self.ledger.propose_recheck("old", "trigger", "Mismatched source facts")
        changed = replace(contract(), reviewed_by="different-reviewer")
        self.assertEqual(self.ledger.resolve_recheck(changed, "old", trace("repair")), "LOCK_DISPUTED")
        self.assertEqual(self.ledger.xp("manual-boxes-1"), [])

    def test_unverified_trigger_cannot_request_review(self):
        self.ledger.record(contract(), trace("old"))
        self.ledger.record(contract(), trace("bad", trace().raw_text.replace("43", "42")))
        with self.assertRaises(ValueError):
            self.ledger.propose_recheck("old", "bad", "I think the lock is wrong")

    def test_token_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            self.ledger.record(contract(), trace(tokens=0))


if __name__ == "__main__":
    unittest.main()
