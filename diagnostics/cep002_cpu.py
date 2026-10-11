"""CEP-002 CPU prototype: narrow, independently checked arithmetic contracts.

Only fully machine-readable traces can be VERIFIED. Natural-language reasoning,
semantic task-contract correctness, and official benchmark compliance are NOT
proved by this module. No training, GPU calls, or model inference occurs here.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

VERIFIER_VERSION = "cep002-cpu-0.1"
ALLOWED_SOURCES = frozenset({"synthetic/manual", "gsm8k/main/train"})
NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
DECIMAL = re.compile(r"[+-]?\d{1,15}(?:\.\d{1,12})?\Z")
STEP_LINE = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.+?)\s*=>\s*([+-]?\d+(?:\.\d+)?)\Z")
FINAL_LINE = re.compile(r"Final answer:\s*([+-]?\d+(?:\.\d+)?)\Z")


@dataclass(frozen=True)
class StepRule:
    target: str
    expression: str


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    source: str
    facts: dict[str, str]
    rules: tuple[StepRule, ...]
    final_target: str
    gold_answer: str
    reviewed_by: str
    overlap_screen_passed: bool

    def fingerprint(self) -> str:
        payload = {
            "task_id": self.task_id,
            "source": self.source,
            "facts": self.facts,
            "rules": [{"target": rule.target, "expression": rule.expression} for rule in self.rules],
            "final_target": self.final_target,
            "gold_answer": self.gold_answer,
            "reviewed_by": self.reviewed_by,
            "overlap_screen_passed": self.overlap_screen_passed,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CandidateTrace:
    candidate_id: str
    task_id: str
    raw_text: str
    completed: bool
    measured_tokens: int | None = None


@dataclass(frozen=True)
class Verdict:
    status: str
    reason: str
    contract_hash: str
    verifier_version: str = VERIFIER_VERSION


class ContractError(ValueError):
    """Untrusted, inconsistent, or unsupported task contract."""


def parse_decimal(value: str) -> Decimal:
    if not isinstance(value, str) or not DECIMAL.fullmatch(value):
        raise ValueError("unsupported numeric literal")
    return Decimal(value)


def parse_expression(source: str) -> ast.Expression:
    if not isinstance(source, str) or len(source) > 160:
        raise ValueError("expression is too long")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError("invalid expression") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 25:
        raise ValueError("expression is too complex")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load,
               ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub)
    if any(not isinstance(node, allowed) for node in nodes):
        raise ValueError("unsafe or unsupported arithmetic")
    for node in nodes:
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, int)
            or len(str(node.value)) > 15
        ):
            raise ValueError("only short integer constants supported")
    return tree


def calculate(node: ast.AST, context: dict[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Expression):
        return calculate(node.body, context)
    if isinstance(node, ast.Constant):
        return Decimal(node.value)
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise ValueError("missing or forward-referenced input: " + node.id)
        return context[node.id]
    if isinstance(node, ast.UnaryOp):
        value = calculate(node.operand, context)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = calculate(node.left, context)
        right = calculate(node.right, context)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("division by zero")
            return left / right
    raise ValueError("unsupported expression")


def checked_contract(contract: TaskContract) -> tuple[dict[str, Decimal], list[ast.Expression]]:
    if contract.source not in ALLOWED_SOURCES:
        raise ContractError("evaluation or unknown source is not permitted")
    if not contract.task_id or not contract.reviewed_by or not contract.overlap_screen_passed:
        raise ContractError("manual review and prior overlap screening required")
    if not contract.rules or len(contract.rules) > 12 or not NAME.fullmatch(contract.final_target):
        raise ContractError("invalid contract rules")
    try:
        if len(contract.facts) > 20:
            raise ValueError("too many input facts")
        state: dict[str, Decimal] = {}
        for key, value in contract.facts.items():
            if not NAME.fullmatch(key):
                raise ValueError("invalid fact name")
            state[key] = parse_decimal(value)
        parsed = []
        with localcontext() as ctx:
            ctx.prec = 28
            for rule in contract.rules:
                if not NAME.fullmatch(rule.target) or rule.target in state:
                    raise ValueError("duplicate or invalid target")
                tree = parse_expression(rule.expression)
                state[rule.target] = calculate(tree, state)
                parsed.append(tree)
            if contract.final_target not in {rule.target for rule in contract.rules}:
                raise ValueError("final target must be derived")
            if state[contract.final_target] != parse_decimal(contract.gold_answer):
                raise ValueError("trusted contract disagrees with gold answer")
        return state, parsed
    except (ValueError, DecimalException, OverflowError) as exc:
        raise ContractError(str(exc)) from exc


def verify(contract: TaskContract, candidate: CandidateTrace) -> Verdict:
    fingerprint = contract.fingerprint()
    try:
        expected, trees = checked_contract(contract)
    except ContractError as exc:
        return Verdict("UNVERIFIED", "contract rejected: " + str(exc), fingerprint)
    if candidate.task_id != contract.task_id:
        return Verdict("UNVERIFIED", "candidate belongs to another task", fingerprint)
    if not candidate.completed or "Final answer:" not in candidate.raw_text:
        return Verdict("TRUNCATED", "candidate has no completed final answer", fingerprint)
    if len(candidate.raw_text) > 8000:
        return Verdict("UNVERIFIED", "unsupported long trace", fingerprint)
    lines = [line.strip() for line in candidate.raw_text.strip().splitlines()]
    if len(lines) != len(contract.rules) + 1:
        return Verdict("UNVERIFIED", "trace must contain only auditable steps and final", fingerprint)
    match_final = FINAL_LINE.fullmatch(lines[-1])
    if match_final is None:
        return Verdict("UNVERIFIED", "unsupported final-answer format", fingerprint)
    current = {key: parse_decimal(value) for key, value in contract.facts.items()}
    with localcontext() as ctx:
        ctx.prec = 28
        for line, rule, reference_tree in zip(lines[:-1], contract.rules, trees):
            match = STEP_LINE.fullmatch(line)
            if match is None or match.group(1) != rule.target:
                return Verdict("UNVERIFIED", "missing or reordered auditable relation", fingerprint)
            try:
                candidate_tree = parse_expression(match.group(2))
                produced = calculate(candidate_tree, current)
                claimed = parse_decimal(match.group(3))
            except (ValueError, DecimalException, OverflowError):
                return Verdict("UNVERIFIED", "unverifiable candidate expression", fingerprint)
            if produced != claimed or claimed != expected[rule.target]:
                return Verdict("INVALID", "incorrect intermediate result: " + rule.target, fingerprint)
            if ast.dump(candidate_tree, include_attributes=False) != ast.dump(reference_tree, include_attributes=False):
                return Verdict("UNVERIFIED", "relation differs from reviewed contract", fingerprint)
            current[rule.target] = claimed
        try:
            final = parse_decimal(match_final.group(1))
        except ValueError:
            return Verdict("UNVERIFIED", "unsupported final numeric value", fingerprint)
        if final != expected[contract.final_target]:
            return Verdict("INVALID", "incorrect final answer", fingerprint)
    return Verdict("VERIFIED", "all structured relations checked", fingerprint)


class ExperienceLedger:
    """Append-only-by-API JSONL audit history; not tamper-proof external storage."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def record(self, contract: TaskContract, candidate: CandidateTrace) -> Verdict:
        if not candidate.candidate_id:
            raise ValueError("nonempty candidate ID required")
        if candidate.measured_tokens is not None and candidate.measured_tokens < 1:
            raise ValueError("invalid token measurement")
        if any(event.get("type") == "attempt" and event.get("candidate_id") == candidate.candidate_id
               for event in self.events()):
            raise ValueError("candidate IDs must be globally unique")
        verdict = verify(contract, candidate)
        self.append({"type": "attempt", "task_id": candidate.task_id,
                     "candidate_id": candidate.candidate_id, "raw_text": candidate.raw_text,
                     "completed": candidate.completed, "measured_tokens": candidate.measured_tokens,
                     "status": verdict.status, "reason": verdict.reason,
                     "contract_hash": verdict.contract_hash, "verifier_version": verdict.verifier_version})
        if verdict.status == "VERIFIED":
            self.append({"type": "verified_lock", "task_id": candidate.task_id,
                         "candidate_id": candidate.candidate_id, "contract_hash": verdict.contract_hash,
                         "verifier_version": verdict.verifier_version})
        return verdict

    def xp(self, task_id: str, limit: int = 3) -> list[dict[str, Any]]:
        if not 1 <= limit <= 3:
            raise ValueError("only 1-3 independently verified candidates allowed")
        records = self.events()
        locks = {event["candidate_id"] for event in records if event["type"] == "verified_lock"}
        if any(event["type"] == "lock_disputed" and event["task_id"] == task_id
               for event in records):
            return []
        selected = [event for event in records if event["type"] == "attempt" and
                    event["task_id"] == task_id and event["candidate_id"] in locks]
        selected.sort(key=lambda row: (row["measured_tokens"] is None,
                                       row["measured_tokens"] if row["measured_tokens"] is not None else 0,
                                       row["candidate_id"]))
        distinct = []
        seen_traces = set()
        for item in selected:
            if item["raw_text"] not in seen_traces:
                distinct.append(item)
                seen_traces.add(item["raw_text"])
            if len(distinct) == limit:
                break
        return distinct

    def propose_recheck(self, old_id: str, trigger_id: str, evidence: str) -> None:
        attempts = {event["candidate_id"]: event for event in self.events() if event["type"] == "attempt"}
        if old_id not in attempts or trigger_id not in attempts:
            raise ValueError("both original and trigger must exist")
        verified_locks = {event["candidate_id"] for event in self.events()
                          if event["type"] == "verified_lock"}
        disputed = {event["candidate_id"] for event in self.events()
                    if event["type"] == "lock_disputed"}
        if (trigger_id not in verified_locks or trigger_id in disputed
                or not isinstance(evidence, str) or not evidence.strip()):
            raise ValueError("independently verified trigger and specific evidence required")
        self.append({"type": "recheck_pending", "old_id": old_id,
                     "trigger_id": trigger_id, "evidence": evidence})

    def resolve_recheck(self, contract: TaskContract, old_id: str,
                        repaired: CandidateTrace) -> str:
        events = self.events()
        originals = [item for item in events if item["type"] == "attempt" and item["candidate_id"] == old_id]
        if len(originals) != 1 or not any(item["type"] == "recheck_pending" and
                                          item["old_id"] == old_id for item in events):
            raise ValueError("original attempt and pending review required")
        pending_indices = [i for i, event in enumerate(events) if
                           event["type"] == "recheck_pending" and event["old_id"] == old_id]
        if not pending_indices:
            raise ValueError("missing pending review")
        newest = pending_indices[-1]
        closed = {"rejected_correction", "accepted_repair", "recheck_inconclusive"}
        if any((event.get("old_id") == old_id and event["type"] in closed) or
               (event.get("candidate_id") == old_id and event["type"] == "lock_disputed")
               for event in events[newest + 1:]):
            raise ValueError("review already resolved")
        old = originals[0]
        if old["task_id"] != contract.task_id:
            raise ValueError("must recheck original task, not triggering task")
        if old["contract_hash"] != contract.fingerprint() or old["verifier_version"] != VERIFIER_VERSION:
            self.append({"type": "lock_disputed", "task_id": old["task_id"],
                         "candidate_id": old_id, "reason": "contract or verifier version changed"})
            return "LOCK_DISPUTED"
        previous = verify(contract, CandidateTrace(old_id, old["task_id"], old["raw_text"], old["completed"]))
        if old["status"] == "VERIFIED" and previous.status == "VERIFIED":
            self.append({"type": "rejected_correction", "old_id": old_id,
                         "reason": "original verified trace still correct"})
            return "REJECTED_CORRECTION"
        if old["status"] == "VERIFIED" or previous.status != old["status"]:
            self.append({"type": "lock_disputed", "task_id": old["task_id"],
                         "candidate_id": old_id, "reason": "verification conflict"})
            return "LOCK_DISPUTED"
        if previous.status != "INVALID" or verify(contract, repaired).status != "VERIFIED":
            self.append({"type": "recheck_inconclusive", "old_id": old_id,
                         "reason": "old error unproven or repair not verified"})
            return "UNVERIFIED"
        if repaired.task_id != old["task_id"]:
            raise ValueError("repair must address the original task")
        self.record(contract, repaired)
        self.append({"type": "accepted_repair", "old_id": old_id,
                     "new_id": repaired.candidate_id,
                     "reason": previous.reason})
        return "ACCEPTED_VERIFIED_REPAIR"
