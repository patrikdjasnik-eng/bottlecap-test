"""CPU-only, content-pinned GSM8K Safe Start question preparation.

Downloads ONLY the pinned GSM8K main/train Parquet file, extracts 12 candidate
questions and gold numeric answers, and marks all records REVIEW ONLY.
Never generates model outputs, trains a model, or alters evaluation files.
"""

import argparse
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

from .safe_start_plan import QUESTION_COUNT, validate_questions, plan_attempts

DATASET_REPO = "openai/gsm8k"
DATASET_REVISION = "740312add88f781978c0658806c59bc2815b9866"
TRAIN_RELATIVE_PATH = "main/train-00000-of-00001.parquet"
TRAIN_SHA256 = "ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d"
TRAIN_URL = (f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/"
             f"{DATASET_REVISION}/{TRAIN_RELATIVE_PATH}")
NORMALIZE = re.compile(r"[^a-z0-9]+")
GOLD = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?\Z")
SELECTION_SALT = "RHAR-SAFE-START-V0.1-GSM8K-TRAIN-12"


def normalize_question(value):
    """Lossy text normalizer for duplicate screening; not a semantic proof."""
    return " ".join(NORMALIZE.sub(" ", value.lower()).split())


def close_match(left, right):
    """Conservative duplicate heuristic, not exhaustive semantic similarity."""
    if left == right:
        return True
    if not left or not right:
        return False
    a, b = set(left.split()), set(right.split())
    jaccard = len(a & b) / len(a | b) if a | b else 1.0
    return jaccard >= 0.85 or SequenceMatcher(None, left, right).ratio() >= 0.92


def parse_gold(raw_answer):
    """Use only the GSM8K answer after ####, never the reference reasoning."""
    if not isinstance(raw_answer, str) or raw_answer.count("####") != 1:
        raise ValueError("expected exactly one GSM8K #### numeric answer")
    answer = raw_answer.split("####", 1)[1].strip()
    if not GOLD.fullmatch(answer):
        raise ValueError("gold answer is not a single numeric value")
    return answer.replace(",", "")


def candidate_rows(dataset_rows):
    """Deterministic ranking independent of model performance and gold answers."""
    candidates = []
    for source_index, source in enumerate(dataset_rows):
        if not isinstance(source, dict):
            raise ValueError(f"source row {source_index} is not an object")
        question = source.get("question")
        if not isinstance(question, str) or not question.strip():
            continue
        if "final answer:" in question.casefold():
            continue
        try:
            gold = parse_gold(source.get("answer"))
        except ValueError:
            continue
        normalized = normalize_question(question)
        if not normalized or len(normalized.split()) < 6:
            continue
        digest = hashlib.sha256((SELECTION_SALT + "\n" + normalized).encode()).hexdigest()
        candidates.append((digest, source_index, {
            "question_id": f"gsm8k-train-{source_index:05d}",
            "question": question.strip(), "gold_answer": gold,
            "source": "gsm8k", "source_revision": DATASET_REVISION,
            "split": "train", "task": "math",
        }, normalized))
    return sorted(candidates, key=lambda item: (item[0], item[1]))


def read_eval_prompts(path):
    """Read local evaluation prompts solely for overlap screening; never their answers."""
    if path is None:
        return None
    prompts = []
    with Path(path).open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"eval line {line_number}: invalid JSON") from exc
            if not isinstance(obj, dict) or not isinstance(obj.get("messages"), list):
                raise ValueError(f"eval line {line_number}: missing messages")
            parts = [m.get("content") for m in obj["messages"]
                     if isinstance(m, dict) and m.get("role") == "user"]
            if not parts or any(not isinstance(v, str) or not v.strip() for v in parts):
                raise ValueError(f"eval line {line_number}: unusable user prompt")
            prompts.append(normalize_question(" ".join(parts)))
    if not prompts:
        raise ValueError("empty evaluation prompt list")
    return prompts


def pick_questions(dataset_rows, eval_prompts=None):
    """Return 12 review-only candidates plus counts; no eval prompts in output."""
    ranked = candidate_rows(dataset_rows)
    selected, selected_norms = [], []
    blocked_internal, blocked_eval = 0, 0
    for _, _, candidate, norm in ranked:
        if any(close_match(norm, chosen) for chosen in selected_norms):
            blocked_internal += 1
            continue
        if eval_prompts is not None and any(close_match(norm, p) for p in eval_prompts):
            blocked_eval += 1
            continue
        selected.append(candidate)
        selected_norms.append(norm)
        if len(selected) == QUESTION_COUNT:
            break
    if len(selected) != QUESTION_COUNT:
        raise ValueError(f"only {len(selected)} clean candidates found; need 12")
    validate_questions(selected)
    if len(plan_attempts(selected)) != 36:
        raise AssertionError("planner and selected records disagree")
    return selected, {
        "source_rows_seen": len(dataset_rows),
        "parseable_ranked_candidates": len(ranked),
        "rejected_near_or_exact_duplicate": blocked_internal,
        "rejected_overlap_with_local_eval": blocked_eval,
        "local_eval_audit_performed": eval_prompts is not None,
        "local_eval_question_count": len(eval_prompts) if eval_prompts is not None else 0,
        "overlap_audit_exhaustive": False,
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_train(raw_path, opener=None):
    """Download only pinned train file, verify content SHA-256; never overwrite."""
    path = Path(raw_path)
    if path.exists():
        if sha256_file(path) != TRAIN_SHA256:
            raise ValueError("existing cached train Parquet has incorrect SHA-256")
        return "verified_cached"
    path.parent.mkdir(parents=True, exist_ok=True)
    open_url = opener or urllib.request.urlopen
    fd, temp = tempfile.mkstemp(prefix=".train-", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as dest, open_url(TRAIN_URL, timeout=120) as src:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dest.write(chunk)
        if sha256_file(temp) != TRAIN_SHA256:
            raise ValueError("downloaded GSM8K train Parquet SHA-256 mismatch")
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        os.replace(temp, path)
        return "downloaded_and_verified"
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_parquet(path):
    """Read local Parquet only. pyarrow is a dependency of the existing datasets package."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow not installed; install project dataset dependencies") from exc
    table = pq.read_table(path, columns=["question", "answer"])
    return table.to_pylist()


def create_review_files(out_dir, selected, stats, status):
    """Write new ignored local review artifacts. Never overwrite earlier runs."""
    root = Path(out_dir)
    questions_file = root / "questions.jsonl"
    report_file = root / "selection-report.json"
    for file in (questions_file, report_file):
        if file.exists():
            raise FileExistsError(f"refusing to overwrite {file}")
    root.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in selected)
    report = {
        "status": "review_only", "question_count": len(selected),
        "planned_generations": 36, "training_approved": False,
        "model_generations_performed": 0, "gpu_used": False,
        "training_performed": False, "official_benchmark_run": False,
        "dataset": DATASET_REPO, "dataset_revision": DATASET_REVISION,
        "source_split": "main/train", "train_parquet_sha256": TRAIN_SHA256,
        "download_status": status, "selected_question_ids": [q["question_id"] for q in selected],
        "selected_question_sha256": [hashlib.sha256(q["question"].encode()).hexdigest()
                                      for q in selected],
        "overlap_audit_status": "local_partial_only" if stats["local_eval_audit_performed"]
                                else "pending_local_eval_corpus",
        **stats,
    }
    with questions_file.open("x", encoding="utf-8") as file:
        file.write(data)
    with report_file.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Explicitly download pinned GSM8K train on CPU")
    parser.add_argument("--out-dir", type=Path, default=Path("data/safe-start"))
    parser.add_argument("--eval-questions", type=Path, help="Optional existing local official evaluation questions/questions.jsonl")
    args = parser.parse_args(argv)
    if not args.download:
        parser.error("explicit --download is required (never download implicitly)")
    root = args.out_dir
    if any((root / name).exists() for name in ("questions.jsonl", "selection-report.json")):
        parser.error("output files already exist; refusing to overwrite")
    eval_path = args.eval_questions
    if eval_path is None and Path("questions/questions.jsonl").is_file():
        eval_path = Path("questions/questions.jsonl")
    # Validate local eval data before triggering an external download.
    eval_prompts = read_eval_prompts(eval_path) if eval_path is not None else None
    raw_file = root / "raw" / "gsm8k-train.parquet"
    status = download_train(raw_file)
    rows = read_parquet(raw_file)
    selected, stats = pick_questions(rows, eval_prompts)
    report = create_review_files(root, selected, stats, status)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("Review-only questions:", root / "questions.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
