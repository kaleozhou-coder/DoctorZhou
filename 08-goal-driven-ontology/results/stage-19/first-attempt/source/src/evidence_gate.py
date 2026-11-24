"""Stage 18 offline evidence-registration gate (stdlib; not a semantic reasoner)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA = "stage18-evidence-gate-v1"
PROFILE = "utf8-no-bom-lf-nfc-codepoint-v1"
ROLES = {"DIRECT", "CONTEXT", "CONFLICT"}
EVIDENCE = {"doc", "rev", "rendition", "clause", "role", "quote", "start", "end",
            "raw_sha256", "normalized_sha256"}
GAP = {"doc", "rev", "clause", "scope", "field", "locator"}
CLAUSE = {"id", "scope", "field", "role", "quote", "start", "end"}
DOC = {"doc", "rev", "rendition", "project", "text", "readable", "clauses"}
HEX = re.compile(r"[0-9a-f]{64}")
DOC_BYTES = 256 * 1024
CORPUS_BYTES = 4 * 1024 * 1024
JSON_BYTES = 8 * 1024 * 1024


class GateError(ValueError):
    """Input not in the frozen gate schema; no verdict is returned."""


def _text(value: Any, label: str, *, count: int = 512) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > count
            or any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)):
        raise GateError(f"invalid {label}")
    return value


def _key(value: Any, label: str) -> str:
    value = _text(value, label, count=128)
    if value != value.strip() or ":" in value or any(ord(c) < 32 for c in value):
        raise GateError(f"invalid {label}")
    return value


def _obj(value: Any, fields: set[str], label: str, *, optional: set[str] | None = None) -> dict:
    if (not isinstance(value, dict) or not fields <= value.keys()
            or value.keys() - fields - (optional or set())):
        raise GateError(f"invalid {label} object")
    return value


def _arr(value: Any, n: int, label: str) -> list:
    if not isinstance(value, list) or len(value) > n:
        raise GateError(f"invalid {label} list")
    return value


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.replace("\r\n", "\n").replace("\r", "\n"))


def build_snapshot(raw: bytes) -> dict:
    """Return canonical text and both SHA-256 digests; offsets are normalized code points."""
    if not isinstance(raw, bytes) or len(raw) > DOC_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("invalid raw source snapshot")
    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise GateError("invalid source UTF-8") from exc
    normalized = _norm(decoded)
    if not normalized.strip():
        raise GateError("invalid blank source")
    return {
        "text": normalized,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }


def _coordinates(record: dict, label: str, *, auto_allowed: bool) -> None:
    start, end = record["start"], record["end"]
    if auto_allowed and start is None and end is None:
        return
    if type(start) is not int or type(end) is not int:
        raise GateError(f"invalid {label} coordinates")


def _exact_span(text: str, quote: str, start: int, end: int) -> bool:
    return 0 <= start < end <= len(text) and text[start:end] == quote


def _gap(value: Any, label: str) -> None:
    if value is None:
        return
    record = _obj(value, GAP, label)
    for field in GAP - {"locator"}:
        _key(record[field], f"{label}.{field}")
    _text(record["locator"], f"{label}.locator", count=515)


def _role(value: Any) -> None:
    if not isinstance(value, str) or value not in ROLES:
        raise GateError("invalid evidence role")


def _registry(registry: Any) -> tuple[dict, dict, dict, set[str], dict | None]:
    registry = _obj(registry, {"question", "documents", "required_direct", "required_gap"}, "registry")
    question = _obj(registry["question"], {"project", "scope", "field"}, "question")
    for k, v in question.items():
        _key(v, f"question.{k}")
    docs, clauses = {}, {}
    byte_count = 0
    for document in _arr(registry["documents"], 64, "documents"):
        doc = _obj(document, DOC, "source")
        dkey = tuple(_key(doc[k], f"source.{k}") for k in ("doc", "rev", "rendition"))
        _key(doc["project"], "source.project")
        if dkey in docs or type(doc["readable"]) is not bool:
            raise GateError("invalid repeated source identity or ACL flag")
        raw = _text(doc["text"], "source.text", count=DOC_BYTES).encode("utf-8")
        byte_count += len(raw)
        if byte_count > CORPUS_BYTES:
            raise GateError("source corpus too large")
        snap = build_snapshot(raw)
        docs[dkey] = (doc, snap)
        for item in _arr(doc["clauses"], 128, "source.clauses"):
            clause = _obj(item, CLAUSE, "clause", optional={"value"})
            locator = ":".join((*dkey, _key(clause["id"], "clause.id")))
            if locator in clauses:
                raise GateError("duplicate clause identity")
            for f in ("scope", "field"):
                _key(clause[f], f"clause.{f}")
            _role(clause["role"])
            quote = _norm(_text(clause["quote"], "clause.quote", count=1024))
            _coordinates(clause, "clause", auto_allowed=False)
            if not _exact_span(snap["text"], quote, clause["start"], clause["end"]):
                raise GateError("invalid approved clause span")
            if clause.get("value") is not None:
                _text(clause["value"], "clause.value")
            clauses[locator] = (dkey, {**clause, "quote": quote})
    direct_items = _arr(registry["required_direct"], 32, "required_direct")
    direct = {_text(item, "required_direct locator", count=515) for item in direct_items}
    if len(direct) != len(direct_items):
        raise GateError("duplicate required_direct locator")
    for locator in direct:
        if locator not in clauses:
            raise GateError("required_direct locator not registered")
        dkey, clause = clauses[locator]
        if clause["role"] != "DIRECT" or not _in_question(docs[dkey][0], clause, question):
            raise GateError("required_direct locator not applicable")
    gap = registry["required_gap"]
    _gap(gap, "required_gap")
    if gap:
        if (gap["scope"], gap["field"]) != (question["scope"], question["field"]):
            raise GateError("required_gap target not applicable")
        if gap["locator"] not in clauses:
            raise GateError("required_gap locator not registered")
        dkey, clause = clauses[gap["locator"]]
        if clause["role"] != "CONTEXT" or not _in_question(docs[dkey][0], clause, question):
            raise GateError("required_gap locator not applicable")
    return question, docs, clauses, direct, gap


def _in_question(doc: dict, clause: dict, question: dict) -> bool:
    return (doc["project"], clause["scope"], clause["field"]) == (
        question["project"], question["scope"], question["field"])


def _candidate(candidate: Any) -> dict:
    data = _obj(candidate, {"decision", "evidence", "gap"}, "candidate")
    decision = _obj(data["decision"], {"state", "value"}, "decision")
    if decision["state"] == "KNOWN":
        _text(decision["value"], "known value")
    elif decision["state"] != "UNKNOWN" or decision["value"] is not None:
        raise GateError("invalid decision")
    _gap(data["gap"], "gap")
    for row in _arr(data["evidence"], 64, "evidence"):
        evidence = _obj(row, EVIDENCE, "evidence entry")
        for name in ("doc", "rev", "rendition", "clause"):
            _key(evidence[name], f"evidence.{name}")
        _role(evidence["role"])
        _text(evidence["quote"], "evidence.quote", count=1024)
        _coordinates(evidence, "evidence", auto_allowed=True)
        for key in ("raw_sha256", "normalized_sha256"):
            if not isinstance(evidence[key], str) or not HEX.fullmatch(evidence[key]):
                raise GateError("invalid evidence digest format")
    return data


def _out(status: str, reason: str) -> dict:
    # No citation contents, identifiers or source hashes are returned.
    return {"status": status, "reason": reason}


def run_gate(registry: dict, request: dict) -> dict:
    """Return only status and reason; never consult an oracle or write state."""
    question, docs, clauses, required_direct, required_gap = _registry(registry)
    data = _candidate(request)
    seen: dict[str, dict] = {}
    for evidence in data["evidence"]:
        identity = tuple(evidence[k] for k in ("doc", "rev", "rendition"))
        if identity not in docs:
            return _out("BLOCKED", "SOURCE_NOT_ADMISSIBLE")
        doc, snap = docs[identity]
        if not doc["readable"] or doc["project"] != question["project"]:
            return _out("BLOCKED", "SOURCE_NOT_ADMISSIBLE")
        if any(evidence[k] != snap[k] for k in ("raw_sha256", "normalized_sha256")):
            return _out("BLOCKED", "EVIDENCE_HASH_MISMATCH")
        locator = ":".join((*identity, evidence["clause"]))
        if locator not in clauses:
            return _out("BLOCKED", "CLAUSE_NOT_ADMISSIBLE")
        _, clause = clauses[locator]
        if not _in_question(doc, clause, question):
            return _out("BLOCKED", "DIRECT_SCOPE_MISMATCH")
        if evidence["role"] != clause["role"]:
            return _out("BLOCKED", "EVIDENCE_ROLE_MISMATCH")
        quote = _norm(evidence["quote"])
        start, end = evidence["start"], evidence["end"]
        if start is None:  # both None already asserted by schema validation
            start = snap["text"].find(quote)
            if start < 0 or snap["text"].find(quote, start + 1) >= 0:
                return _out("BLOCKED", "QUOTE_SPAN_MISMATCH")
            end = start + len(quote)
        if (quote != clause["quote"] or (start, end) != (clause["start"], clause["end"])
                or not _exact_span(snap["text"], quote, start, end)):
            return _out("BLOCKED", "QUOTE_SPAN_MISMATCH")
        if locator in seen:
            return _out("BLOCKED", "DUPLICATE_EVIDENCE")
        seen[locator] = clause

    direct = {locator for locator, clause in seen.items() if clause["role"] == "DIRECT"}
    if data["decision"]["state"] == "UNKNOWN":
        if direct:
            return _out("BLOCKED", "UNKNOWN_WITH_DIRECT")
        if (required_gap is None or data["gap"] != required_gap
                or required_gap["locator"] not in seen):
            return _out("BLOCKED", "REQUIRED_GAP_MISMATCH")
        return _out("PENDING", "REQUIRED_GAP_VERIFIED")

    if required_gap is not None or data["gap"] is not None:
        return _out("BLOCKED", "REQUIRED_GAP_MISMATCH")
    if any(clause["role"] == "CONFLICT" and docs[dkey][0]["readable"]
           and _in_question(docs[dkey][0], clause, question) for dkey, clause in clauses.values()):
        return _out("BLOCKED", "CONFLICT_PRESENT")
    if not required_direct or direct != required_direct:
        return _out("BLOCKED", "REQUIRED_DIRECT_MISSING")
    asserted = [seen[locator]["value"] for locator in required_direct
                if seen[locator].get("value") is not None]
    if not asserted or any(value != data["decision"]["value"] for value in asserted):
        return _out("BLOCKED", "DIRECT_VALUE_MISMATCH")
    return _out("ELIGIBLE", "DIRECT_VERIFIED")


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise GateError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise GateError("invalid JSON constant")


def _read(path: Path) -> Any:
    try:
        with path.open("rb") as f:
            raw = f.read(JSON_BYTES + 1)
        if len(raw) > JSON_BYTES:
            raise GateError("JSON byte limit exceeded")
        return json.loads(raw.decode("utf-8", errors="strict"),
                          object_pairs_hook=_pairs, parse_constant=_constant)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise GateError("invalid JSON input") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_gate(_read(args.registry), _read(args.request))
    except GateError:
        print(f"{SCHEMA}: invalid input", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
