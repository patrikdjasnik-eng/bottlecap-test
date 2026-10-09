"""Read-only decontamination screen of 12 GSM8K Safe Start candidates.

Explicitly fetches ONLY pinned evaluation source *data* (not graders or models).
Uses question/prompt text, never evaluation answers, references, or test results.
Does not modify the original candidate list, official evaluation or model.
"""

import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import urllib.request

from .safe_start_data import (DATASET_REVISION, close_match, normalize_question)
from .safe_start_plan import read_questions, validate_questions

# Match the unchanged official benchmark's source revisions and integrity pins.
# A source pin is a commit, except MBPP+ v0.2.0, whose decoded SHA-256 is pinned.
SOURCES = (
    {"name": "svamp", "family": "SVAMP", "format": "svamp", "url":
     "https://raw.githubusercontent.com/arkilpatel/SVAMP/78e727689e1c1bebfc4be39c446898e8e10b0518/SVAMP.json",
     "expected_sha256": "5be77703a6d891ae476d7c082787ad361392aa02453b132516cdd5f4e7934e3e"},
    {"name": "mbpp_plus", "family": "MBPP+", "format": "mbpp", "url":
     "https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz",
     "expected_sha256": "b54e762755248ca411b523c917fa9f93c07b5ff2966bf60b3917b853926a3dad"},
    {"name": "bfcl_simple_python", "family": "BFCL", "format": "bfcl", "url":
     "https://raw.githubusercontent.com/ShishirPatil/gorilla/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_simple_python.json"},
    {"name": "bfcl_multiple", "family": "BFCL", "format": "bfcl", "url":
     "https://raw.githubusercontent.com/ShishirPatil/gorilla/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_multiple.json"},
    {"name": "bfcl_irrelevance", "family": "BFCL", "format": "bfcl", "url":
     "https://raw.githubusercontent.com/ShishirPatil/gorilla/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_irrelevance.json"},
    {"name": "ifeval", "family": "IFEval", "format": "ifeval", "url":
     "https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/instruction_following_eval/data/input_data.jsonl"},
)
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_DECODED_BYTES = 128 * 1024 * 1024


def fetch_source(source, opener=None):
    """Fetch pinned source in memory, verify known reference hashes, no disk writes."""
    open_url = opener or urllib.request.urlopen
    with open_url(source["url"], timeout=120) as response:
        parts, total = [], 0
        while True:
            part = response.read(1024 * 1024)
            if not part:
                break
            total += len(part)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"{source['name']}: download size limit exceeded")
            parts.append(part)
    payload = b"".join(parts)
    if not payload:
        raise ValueError(f"{source['name']}: empty download")
    if source["url"].endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
            payload = stream.read(MAX_DECODED_BYTES + 1)
        if len(payload) > MAX_DECODED_BYTES:
            raise ValueError(f"{source['name']}: decompression size limit exceeded")
    digest = hashlib.sha256(payload).hexdigest()
    if source.get("expected_sha256") is not None and digest != source["expected_sha256"]:
        raise ValueError(f"{source['name']}: SHA-256 mismatch")
    return payload, digest


def parse_jsonl(raw, source_name):
    try:
        text = raw.decode("utf-8-sig")
        values = [json.loads(line) for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{source_name}: invalid JSONL") from exc
    if not values:
        raise ValueError(f"{source_name}: empty JSONL")
    return values


def extract_prompts(source, payload):
    """Strictly extract official user-facing question text, not gold answers."""
    name, fmt = source["name"], source["format"]
    if fmt == "svamp":
        try:
            entries = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{name}: invalid SVAMP JSON") from exc
        if not isinstance(entries, list):
            raise ValueError(f"{name}: expected SVAMP list")
    else:
        entries = parse_jsonl(payload, name)
    prompts = []
    for n, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"{name} item {n}: expected object")
        try:
            if fmt == "svamp":
                parts = (entry["Body"], entry["Question"])
                if any(not isinstance(v, str) or not v.strip() for v in parts):
                    raise ValueError("invalid SVAMP question")
                prompt = " ".join(v.strip() for v in parts)
            elif fmt == "mbpp":
                prompt = entry["prompt"]
            elif fmt == "ifeval":
                prompt = entry["prompt"]
            elif fmt == "bfcl":
                turns = entry["question"]
                if not isinstance(turns, list) or len(turns) != 1 or not isinstance(turns[0], list):
                    raise ValueError("expected one BFCL conversation turn")
                messages = turns[0]
                if any(not isinstance(message, dict) for message in messages):
                    raise ValueError("malformed BFCL message")
                user_parts = [message["content"] for message in messages if message.get("role") == "user"]
                if not user_parts or any(not isinstance(x, str) or not x.strip() for x in user_parts):
                    raise ValueError("BFCL user prompt missing/unusable")
                prompt = " ".join(user_parts)
            else:
                raise ValueError("unsupported source format")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{name} item {n}: invalid prompt schema") from exc
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{name} item {n}: blank prompt")
        normalized = normalize_question(prompt)
        if not normalized:
            raise ValueError(f"{name} item {n}: unusable normalized prompt")
        prompts.append(normalized)
    if not prompts:
        raise ValueError(f"{name}: no prompts found")
    return prompts


def verify_selection(questions_path, report_path):
    """Bind audit to original 12 question IDs and hashes; do not reselect."""
    selected = read_questions(questions_path)
    validate_questions(selected)
    if any(row["source_revision"] != DATASET_REVISION for row in selected):
        raise ValueError("selected questions use a different GSM8K revision")
    with Path(report_path).open(encoding="utf-8") as stream:
        report = json.load(stream)
    expected_ids = [q["question_id"] for q in selected]
    hashes = [hashlib.sha256(q["question"].encode("utf-8")).hexdigest() for q in selected]
    if (report.get("status") != "review_only" or report.get("training_approved") is not False
            or report.get("dataset_revision") != DATASET_REVISION
            or report.get("train_parquet_sha256") !=
            "ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d"
            or report.get("selected_question_ids") != expected_ids
            or report.get("selected_question_sha256") != hashes):
        raise ValueError("selected questions do not match the verified review manifest")
    return selected, hashes


def screen_questions(selected, source_prompts):
    """Always check all 12 fixed candidates against all 6 required sources."""
    expected = {source["name"] for source in SOURCES}
    if set(source_prompts) != expected:
        raise ValueError("missing or unexpected official source; refusing partial screen")
    for name, prompts in source_prompts.items():
        if not isinstance(prompts, list) or not prompts or any(
                not isinstance(q, str) or not q for q in prompts):
            raise ValueError(f"{name}: missing prompts")
    matches = []
    for row in selected:
        norm = normalize_question(row["question"])
        for source in SOURCES:
            for index, eval_prompt in enumerate(source_prompts[source["name"]]):
                if norm == eval_prompt or close_match(norm, eval_prompt):
                    matches.append({"question_id": row["question_id"], "source": source["name"],
                                    "source_index": index, "match_kind":
                                    "exact" if norm == eval_prompt else "near_duplicate"})
    return matches


def audit(questions_path, selection_report_path, report_path, fetcher=fetch_source):
    """Fetch only eval source data, fail closed, write report once if all six pass."""
    target = Path(report_path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite {target}")
    selected, question_hashes = verify_selection(questions_path, selection_report_path)
    texts, source_meta = {}, []
    for source in SOURCES:
        payload, digest = fetcher(source)
        prompts = extract_prompts(source, payload)
        texts[source["name"]] = prompts
        source_meta.append({"name": source["name"], "family": source["family"],
                            "url": source["url"], "sha256_of_decoded_bytes": digest,
                            "known_sha256_pin_checked": "expected_sha256" in source,
                            "prompt_count": len(prompts)})
    hits = screen_questions(selected, texts)
    report = {
        "status": "review_only", "audit_type": "heuristic_text_overlap_screen",
        "audit_result": "potential_overlap_found" if hits else "no_matches_in_screened_sources",
        "screened_all_declared_sources": True, "screened_source_count": len(source_meta),
        "screened_families": sorted(set(s["family"] for s in SOURCES)),
        "screened_prompt_count": sum(s["prompt_count"] for s in source_meta),
        "question_count": len(selected), "question_ids": [q["question_id"] for q in selected],
        "question_sha256": question_hashes, "dataset_revision": DATASET_REVISION,
        "potential_match_count": len(hits), "potential_matches": hits,
        "sources": source_meta,
        "semantic_paraphrases_ruled_out": False, "overlap_audit_exhaustive": False,
        "training_approved": False, "gpu_used": False,
        "model_generations_performed": 0, "training_performed": False,
        "official_benchmark_run": False, "original_candidate_files_modified": False,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true",
                        help="Explicit opt-in to downloading six pinned official data sources")
    parser.add_argument("--questions", type=Path, default=Path("data/safe-start/questions.jsonl"))
    parser.add_argument("--selection-report", type=Path,
                        default=Path("data/safe-start/selection-report.json"))
    parser.add_argument("--out", type=Path, default=Path("data/safe-start/overlap-audit.json"))
    args = parser.parse_args(argv)
    if not args.download:
        parser.error("explicit --download is required; no source downloads by default")
    report = audit(args.questions, args.selection_report, args.out)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
