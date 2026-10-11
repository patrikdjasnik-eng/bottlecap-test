"""Produce a human review packet for three CEP-002 draft contracts.

The packet never approves training, edits an XP ledger, or marks a contract as
independently verified. The reviewer must compare every claim with the source.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .cep002_real_contract_drafts import DRAFT_SPECS, create_draft

REVIEW_HINTS = {
    "gsm8k-train-00664": {
        "fact_mappings": (
            ("hamster_years", "hamsters live an average of 2.5 years"),
            ("dog_multiplier", "dogs live 4 times as long as hamsters"),
            ("fish_extra", "fish live 2 years longer than dogs"),
        ),
        "pitfall": "Multiplying the extra 2 years, or treating it as a percentage, is wrong.",
    },
    "gsm8k-train-06718": {
        "fact_mappings": (
            ("rose_num, rose_den", "1/3 bottle of rose shampoo"),
            ("jasmine_num, jasmine_den", "1/4 bottle of jasmine shampoo"),
            ("daily_num, daily_den", "1/12 of a bottle per day"),
        ),
        "pitfall": "Fractions must use compatible bottle-size units; never add denominators directly.",
    },
    "gsm8k-train-03644": {
        "fact_mappings": (
            ("instagram", "240 followers on Instagram"),
            ("facebook", "500 followers on Facebook"),
            ("two", "half of Instagram and Facebook combined"),
            ("three", "TikTok has 3 times Twitter's followers"),
            ("youtube_extra", "YouTube has 510 more than TikTok"),
        ),
        "pitfall": "These are per-platform follower counts, not deduplicated individual people.",
    },
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        data = [json.loads(line) for line in stream if line.strip()]
    if any(not isinstance(item, dict) for item in data):
        raise ValueError("JSONL must contain only objects")
    return data


def review_sections(candidates: list[dict], drafts: list[dict]) -> list[str]:
    if len(drafts) != len(DRAFT_SPECS) or len(candidates) < len(DRAFT_SPECS):
        raise ValueError("exactly 3 drafts and at least 3 candidates required")
    if len({d.get("question_id") for d in drafts}) != len(drafts):
        raise ValueError("duplicate draft question ID")
    sections = []
    for index, spec in enumerate(DRAFT_SPECS):
        candidate = candidates[index]
        draft = drafts[index]
        expected = create_draft(candidate, spec)
        if draft != expected:
            raise ValueError(f"draft content or provenance changed: {spec['question_id']}")
        if (draft["vps_status"] != "UNVERIFIED"
                or draft["manual_semantic_review"] != "PENDING"
                or draft["approved_for_training"] is not False):
            raise ValueError("only unapproved drafts can enter review")
        notes = REVIEW_HINTS[spec["question_id"]]
        lines = [
            f"## {index + 1}. {spec['question_id']}",
            "",
            f"**Source:** GSM8K main/train @ {draft['source_revision']}",
            f"**Question SHA-256:** \`{draft['question_sha256']}\`",
            "",
            "**Original question:**",
            "",
            candidate["question"],
            "",
            f"**Reference final:** \`{draft['gold_answer']}\`",
            "",
            "**Proposed mapping from text to facts (check manually):**",
            "",
        ]
        lines += [
            f"- \`{symbol}\` ← {source_phrase}"
            for symbol, source_phrase in notes["fact_mappings"]
        ]
        lines += ["", "**Proposed required relations:**", ""]
        lines += [
            f"- \`{target} = {expression} => {result}\`"
            for target, expression, result in spec["steps"]
        ]
        lines += [
            "",
            f"**Pitfall to audit:** {notes['pitfall']}",
            "",
            "**Human semantic review checklist — leave unchecked until actually checked:**",
            "",
            "- [ ] Every input quantity and unit matches the original question",
            "- [ ] Each relation follows from the language and its conditions",
            "- [ ] Necessary dependencies are preserved; no lucky final number",
            "- [ ] Ambiguity and the noted pitfall were explicitly considered",
            "- [ ] Provenance and historical-dataset overlap were independently checked",
            "",
            "**Decision:** PENDING / REJECTED / NEEDS REVISION (not an approval record)",
            "",
        ]
        sections.append("\n".join(lines))
    return sections


def prepare_review_packet(
    intake_path: Path,
    drafts_path: Path,
    out_path: Path,
    execute: bool,
) -> dict:
    if execute and out_path.exists():
        raise FileExistsError(f"will not overwrite review packet: {out_path}")
    candidates = load_jsonl(intake_path)
    drafts = load_jsonl(drafts_path)
    sections = review_sections(candidates, drafts)
    report = {
        "status": "manual_review_pending" if execute else "plan_only",
        "draft_count": len(sections),
        "contract_semantic_approvals": 0,
        "xp_locks_created": 0,
        "training_records_exported": 0,
        "model_inference_performed": False,
        "training_performed": False,
        "gpu_used": False,
        "holdout_questions_accessed": False,
    }
    if execute:
        if not out_path.parent.is_dir():
            raise FileNotFoundError("review output parent directory must exist")
        heading = (
            "# CEP-002 — manual semantic review packet\n\n"
            "**Status: REVIEW ONLY.** No independent semantic review or training approval "
            "is implied by this document. Do not edit the original source files.\n\n"
        )
        body = heading + "\n".join(sections)
        with out_path.open("x", encoding="utf-8") as stream:
            stream.write(body)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path,
                        default=Path("runs/cep002-data-intake-001/candidates-review.jsonl"))
    parser.add_argument("--drafts", type=Path,
                        default=Path("runs/cep002-contract-drafts-001/contract-drafts.jsonl"))
    parser.add_argument("--out", type=Path,
                        default=Path("runs/cep002-contract-drafts-001/review-packet.md"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    report = prepare_review_packet(args.intake, args.drafts, args.out, args.execute)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
