"""RHAR 008: integrity metadata for original generated token IDs.

Standard-library-only functions. No model loading, GPU or network access.
"""
import hashlib
import json


def build_token_trace(ids, tokenizer, expected_text, *, model_revision):
    if not isinstance(ids, list) or not ids or any(type(v) is not int or v < 0 for v in ids):
        raise ValueError("generated token IDs must be a nonempty list of nonnegative integers")
    if not isinstance(expected_text, str) or not isinstance(model_revision, str) or not model_revision:
        raise ValueError("invalid trace metadata")
    decoded = tokenizer.decode(ids, skip_special_tokens=False)
    if decoded != expected_text:
        raise ValueError("generated token IDs do not reproduce the saved text")
    encoded = json.dumps(ids, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {
        "schema": "rhar_token_trace_v1",
        "generated_token_ids": list(ids),
        "generated_token_count": len(ids),
        "token_ids_sha256": hashlib.sha256(encoded).hexdigest(),
        "decoded_text_sha256": hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
        "model_revision": model_revision,
        "decode_roundtrip_verified": True,
        "early_stop_safety_verified": False,
        "measured_token_savings": None,
    }


def verify_token_trace(trace, tokenizer, expected_text):
    if not isinstance(trace, dict) or trace.get("schema") != "rhar_token_trace_v1":
        raise ValueError("unknown token trace schema")
    ids = trace.get("generated_token_ids")
    if not isinstance(ids, list) or not ids or any(type(v) is not int or v < 0 for v in ids):
        raise ValueError("invalid token IDs")
    if trace.get("generated_token_count") != len(ids):
        raise ValueError("token count mismatch")
    encoded = json.dumps(ids, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != trace.get("token_ids_sha256"):
        raise ValueError("token ID integrity mismatch")
    decoded = tokenizer.decode(ids, skip_special_tokens=False)
    if decoded != expected_text:
        raise ValueError("decoded text mismatch")
    if hashlib.sha256(decoded.encode("utf-8")).hexdigest() != trace.get("decoded_text_sha256"):
        raise ValueError("decoded text integrity mismatch")
    return True
