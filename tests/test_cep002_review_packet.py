"""Fail-closed CPU tests for the three-question manual semantic review packet."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from diagnostics.cep002_real_contract_drafts import DRAFT_SPECS, create_draft, make_drafts
from diagnostics.cep002_review_packet import prepare_review_packet, review_sections
from tests.test_cep002_real_contract_drafts import source_record


def sample_data() -> tuple[list[dict], list[dict]]:
    candidates = [source_record(index) for index in range(3)]
    drafts = [
        create_draft(candidates[index], DRAFT_SPECS[index])
        for index in range(3)
    ]
    return candidates, drafts


def write_rows(path: Path, records: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


class SemanticReviewPacketTests(unittest.TestCase):
    def test_review_packet_contains_original_questions_and_all_relations(self):
        candidates, drafts = sample_data()
        sections = review_sections(candidates, drafts)
        self.assertEqual(len(sections), 3)
        for index, section in enumerate(sections):
            self.assertIn(candidates[index]["question"], section)
            self.assertIn(DRAFT_SPECS[index]["question_id"], section)
            self.assertIn("**Decision:** PENDING", section)
            self.assertIn("- [ ] Every input quantity", section)
            for target, expression, answer in DRAFT_SPECS[index]["steps"]:
                self.assertIn(f"{target} = {expression} => {answer}", section)

    def test_no_semantic_review_is_automatically_approved(self):
        candidates, drafts = sample_data()
        review_sections(candidates, drafts)
        self.assertTrue(all(draft["manual_semantic_review"] == "PENDING"
                            and draft["vps_status"] == "UNVERIFIED"
                            and not draft["approved_for_training"] for draft in drafts))

    def test_jsonl_round_trip_preserves_contract_comparison(self):
        candidates, drafts = sample_data()
        restored = [json.loads(json.dumps(draft)) for draft in drafts]
        self.assertIsInstance(restored[0]["contract"]["rules"], list)
        self.assertEqual(len(review_sections(candidates, restored)), 3)

    def test_end_to_end_persisted_drafts_can_build_review_packet(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            intake = root / "candidates-review.jsonl"
            draft_dir = root / "contract-drafts"
            output = draft_dir / "review-packet.md"
            candidates, _ = sample_data()
            write_rows(intake, candidates)
            make_drafts(intake, draft_dir, execute=True)
            result = prepare_review_packet(
                intake, draft_dir / "contract-drafts.jsonl", output, execute=True
            )
            self.assertEqual(result["draft_count"], 3)
            self.assertEqual(result["contract_semantic_approvals"], 0)
            self.assertEqual(result["xp_locks_created"], 0)
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_text(encoding="utf-8").count("**Original question:**"), 3)

    def test_tampered_gold_rejected(self):
        candidates, drafts = sample_data()
        candidates[0]["gold_answer"] = "11"
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts)

    def test_tampered_draft_rejected(self):
        candidates, drafts = sample_data()
        drafts[1]["suggested_trace"] = "Final answer: 7"
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts)

    def test_premature_approval_rejected(self):
        candidates, drafts = sample_data()
        drafts[2]["approved_for_training"] = True
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts)

    def test_changed_question_provenance_rejected(self):
        candidates, drafts = sample_data()
        candidates[0]["question"] += " EXTRA"
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts)

    def test_swapped_drafts_rejected(self):
        candidates, drafts = sample_data()
        drafts[0], drafts[1] = drafts[1], drafts[0]
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts)

    def test_incomplete_records_rejected(self):
        candidates, drafts = sample_data()
        with self.assertRaises(ValueError):
            review_sections(candidates[:2], drafts)
        with self.assertRaises(ValueError):
            review_sections(candidates, drafts[:2])

    def test_dry_run_creates_nothing(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            candidates, drafts = sample_data()
            intake, draft_path, output = root / "intake.jsonl", root / "drafts.jsonl", root / "packet.md"
            write_rows(intake, candidates)
            write_rows(draft_path, drafts)
            report = prepare_review_packet(intake, draft_path, output, execute=False)
            self.assertEqual(report["status"], "plan_only")
            self.assertFalse(output.exists())

    def test_execute_creates_only_manual_review_document(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            candidates, drafts = sample_data()
            intake, draft_path, output = root / "intake.jsonl", root / "drafts.jsonl", root / "packet.md"
            write_rows(intake, candidates)
            write_rows(draft_path, drafts)
            report = prepare_review_packet(intake, draft_path, output, execute=True)
            self.assertEqual(report["contract_semantic_approvals"], 0)
            self.assertEqual(report["xp_locks_created"], 0)
            self.assertEqual(report["training_records_exported"], 0)
            self.assertFalse(report["training_performed"])
            text = output.read_text(encoding="utf-8")
            self.assertEqual(text.count("**Original question:**"), 3)
            self.assertIn("REVIEW ONLY", text)
            self.assertNotIn("VERIFIED_LOCKED", text)

    def test_existing_output_never_overwritten(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            candidates, drafts = sample_data()
            intake, draft_path, output = root / "intake.jsonl", root / "drafts.jsonl", root / "packet.md"
            write_rows(intake, candidates)
            write_rows(draft_path, drafts)
            prepare_review_packet(intake, draft_path, output, execute=True)
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare_review_packet(intake, draft_path, output, execute=True)
            self.assertEqual(original, output.read_bytes())

    def test_malformed_jsonl_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            intake, drafts, output = root / "intake.jsonl", root / "drafts.jsonl", root / "packet.md"
            intake.write_text("not-json\n", encoding="utf-8")
            write_rows(drafts, sample_data()[1])
            with self.assertRaises(json.JSONDecodeError):
                prepare_review_packet(intake, drafts, output, execute=True)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
