#!/usr/bin/env python3
"""Stage 17 reproducible strict quote anchoring and separately frozen reference-label scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORPUS_SCHEMA = "stage17-corpus-v1"
GOLD_SCHEMA = "stage17-gold-v1"
SCORE_SCHEMA = "stage17-audit-v1"
PROFILE = "utf8-no-bom-lf-nfc-codepoint-v1"
DOC_MAX = 64
RAW_DOC_MAX = 256 * 1024
RAW_CORPUS_MAX = 4 * 1024 * 1024
QUESTION_MAX = 128
CITE_MAX = 8
QUOTE_MAX = 320
JSON_MAX = 1024 * 1024
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
SHA = re.compile(r"[a-f0-9]{64}")


class InvalidInput(ValueError):
    """Fail closed before returning any score."""


@dataclass(frozen=True)
class Snapshot:
    doc_id: str
    path: str
    text: str
    raw_sha256: str
    normalized_sha256: str
    nbytes: int


def _read_limited(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError as exc:
        raise InvalidInput(f"cannot read {path.name}: {exc.strerror}") from exc
    if len(data) > limit:
        raise InvalidInput(f"input exceeds byte limit: {path.name}")
    return data


def _utf8(raw: bytes, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise InvalidInput(f"{label}: UTF-8 BOM forbidden")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise InvalidInput(f"{label}: invalid UTF-8") from exc


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput(f"duplicate JSON member: {key!r}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise InvalidInput(f"non-JSON constant: {value}")


def read_json(path: Path) -> Any:
    try:
        return json.loads(_utf8(_read_limited(path, JSON_MAX), path.name),
                          object_pairs_hook=_strict_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        raise InvalidInput(f"{path.name}: {exc}") from exc


def _dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise InvalidInput(f"{label}: object keys must be exactly {', '.join(sorted(fields))}")
    return value


def _list(value: Any, low: int, high: int, label: str) -> list:
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise InvalidInput(f"{label}: expected array length {low}..{high}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise InvalidInput(f"{label}: malformed id")
    return value


def _chars(value: Any, limit: int, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{label}: expected a nonblank string")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise InvalidInput(f"{label}: surrogate Unicode code point not allowed")
    if len(value) > limit or len(_norm(value)) > limit:
        raise InvalidInput(f"{label}: exceeds {limit} Unicode code points")
    return value


def _relative_doc(root: Path, raw_path: Any) -> Path:
    value = _chars(raw_path, 512, "path")
    parts = value.split("/")
    if any(p in {"", ".", ".."} for p in parts) or "\\" in value or ":" in value or "\x00" in value:
        raise InvalidInput("path: expected a relative canonical POSIX file path")
    resolved = root.resolve()
    for part in parts:
        resolved = resolved / part
        if resolved.is_symlink():
            raise InvalidInput("path: symlink components are forbidden")
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise InvalidInput("path: expected an existing regular file within the manifest directory")
    return resolved


def _snapshot(root: Path, doc_id: str, relative_path: str) -> Snapshot:
    doc_id = _id(doc_id, "document id")
    raw = _read_limited(_relative_doc(root, relative_path), RAW_DOC_MAX)
    text = _norm(_utf8(raw, doc_id))
    if not text.strip():
        raise InvalidInput(f"{doc_id}: blank document")
    return Snapshot(doc_id, relative_path, text, _hash(raw), _hash(text.encode("utf-8")), len(raw))


def _snapshots(root: Path, refs: list[tuple[str, str]]) -> dict[str, Snapshot]:
    _list(refs, 1, DOC_MAX, "documents")
    docs = {}
    paths = set()
    size = 0
    for doc_id, path in refs:
        snap = _snapshot(root, doc_id, path)
        if doc_id in docs or snap.path in paths:
            raise InvalidInput("duplicate document ID or file path")
        docs[snap.doc_id] = snap
        paths.add(snap.path)
        size += snap.nbytes
        if size > RAW_CORPUS_MAX:
            raise InvalidInput("corpus exceeds aggregate byte limit")
    return docs


def build_manifest(root: Path, refs: list[tuple[str, str]]) -> dict:
    docs = _snapshots(root, refs)
    return {"schema": CORPUS_SCHEMA, "documents": [
        {"id": doc_id, "path": doc.path, "raw_sha256": doc.raw_sha256,
         "normalized_sha256": doc.normalized_sha256}
        for doc_id, doc in sorted(docs.items())
    ]}


def load_snapshots(root: Path, manifest: Any) -> dict[str, Snapshot]:
    table = _dict(manifest, {"schema", "documents"}, "manifest")
    if table["schema"] != CORPUS_SCHEMA:
        raise InvalidInput("manifest schema mismatch")
    rows = _list(table["documents"], 1, DOC_MAX, "documents")
    expected = {}
    refs = []
    for raw in rows:
        row = _dict(raw, {"id", "path", "raw_sha256", "normalized_sha256"}, "manifest record")
        doc_id = _id(row["id"], "document id")
        for key in ("raw_sha256", "normalized_sha256"):
            if not isinstance(row[key], str) or not SHA.fullmatch(row[key]):
                raise InvalidInput(f"{doc_id}: {key} must be lowercase SHA-256")
        expected[doc_id] = row
        refs.append((doc_id, row["path"]))
    docs = _snapshots(root, refs)
    for doc_id, doc in docs.items():
        row = expected[doc_id]
        if (doc.raw_sha256, doc.normalized_sha256) != (row["raw_sha256"], row["normalized_sha256"]):
            raise InvalidInput(f"{doc_id}: document snapshot hash mismatch")
    return docs


def _value(record: dict, label: str) -> None:
    status, value = record["status"], record["value"]
    if status == "KNOWN":
        _chars(value, QUOTE_MAX, f"{label}.value")
    elif status == "UNKNOWN":
        if value is not None:
            raise InvalidInput(f"{label}.value: UNKNOWN requires null")
    else:
        raise InvalidInput(f"{label}.status: expected KNOWN or UNKNOWN")


def _validate_gold(data: Any, docs: dict[str, Snapshot]) -> dict:
    raw = _dict(data, {"schema", "questions"}, "gold")
    if raw["schema"] != GOLD_SCHEMA:
        raise InvalidInput("gold schema mismatch")
    gold = {}
    for record in _list(raw["questions"], 1, QUESTION_MAX, "questions"):
        q = _dict(record, {"id", "status", "value", "alternatives", "allowed_docs"}, "gold question")
        qid = _id(q["id"], "gold question id")
        if qid in gold:
            raise InvalidInput(f"duplicate gold question ID: {qid}")
        _value(q, qid)
        raw_allowed = _list(q["allowed_docs"], 1, DOC_MAX, f"{qid}.allowed_docs")
        allowed = frozenset(_id(x, f"{qid}.allowed_docs") for x in raw_allowed)
        if len(allowed) != len(raw_allowed) or not allowed <= docs.keys():
            raise InvalidInput(f"{qid}: invalid allowed_docs")
        alternatives = []
        for raw_set in _list(q["alternatives"], 1, 32, f"{qid}.alternatives"):
            terms = []
            for entry in _list(raw_set, 1, 16, f"{qid}.proof set"):
                item = _dict(entry, {"doc", "contains"}, f"{qid}.proof term")
                doc_id = _id(item["doc"], f"{qid}.proof.doc")
                phrase = _norm(_chars(item["contains"], QUOTE_MAX, f"{qid}.proof.contains"))
                if doc_id not in allowed or phrase not in docs[doc_id].text:
                    raise InvalidInput(f"{qid}: gold phrase is absent or document is not allowed")
                terms.append((doc_id, phrase))
            if len(set(terms)) != len(terms):
                raise InvalidInput(f"{qid}: duplicate gold proof term")
            alternatives.append(tuple(terms))
        gold[qid] = (q, allowed, alternatives)
    return gold


def _validate_answers(data: Any, questions: dict) -> dict:
    top = _dict(data, {"answers"}, "candidate")
    answers = {}
    for record in _list(top["answers"], 1, QUESTION_MAX, "answers"):
        answer = _dict(record, {"id", "status", "value", "evidence"}, "answer")
        qid = _id(answer["id"], "answer id")
        if qid not in questions or qid in answers:
            raise InvalidInput(f"unexpected or duplicate answer ID: {qid}")
        _value(answer, qid)
        for entry in _list(answer["evidence"], 0, CITE_MAX, f"{qid}.evidence"):
            citation = _dict(entry, {"doc", "quote"}, f"{qid}.citation")
            _id(citation["doc"], f"{qid}.citation.doc")
            _chars(citation["quote"], QUOTE_MAX, f"{qid}.citation.quote")
        answers[qid] = answer
    if answers.keys() != questions.keys():
        raise InvalidInput("answer IDs must exactly match all expected question IDs")
    return answers


def _anchor(doc_id: str, quote: str, docs: dict[str, Snapshot]) -> dict:
    snap = docs.get(doc_id)
    quote = _norm(quote)
    if not snap:
        return {"doc": doc_id, "status": "UNKNOWN_OR_UNAUTHORIZED_DOCUMENT"}
    start = snap.text.find(quote)
    if start < 0:
        return {"doc": doc_id, "status": "QUOTE_NOT_IN_DOCUMENT"}
    if snap.text.find(quote, start + 1) >= 0:
        return {"doc": doc_id, "status": "QUOTE_NOT_UNIQUE"}
    return {"doc": doc_id, "status": "MATCH", "start": start, "end": start + len(quote),
            "quote": quote, "raw_sha256": snap.raw_sha256, "normalized_sha256": snap.normalized_sha256}


def audit(docs: dict[str, Snapshot], gold_data: Any, answers_data: Any) -> dict:
    gold = _validate_gold(gold_data, docs)
    answers = _validate_answers(answers_data, gold)
    rows = []
    for qid, (expected, allowed, alternatives) in gold.items():
        answer = answers[qid]
        keys = set()
        anchors = []
        for entry in answer["evidence"]:
            key = (entry["doc"], _norm(entry["quote"]))
            if key in keys:
                anchors.append({"doc": entry["doc"], "status": "DUPLICATE_CITATION"})
            else:
                anchors.append(_anchor(entry["doc"], entry["quote"], docs))
                keys.add(key)
        value_match = (answer["status"], answer["value"]) == (expected["status"], expected["value"])
        anchor_ok = bool(anchors) and all(a["status"] == "MATCH" for a in anchors)
        anchored = [(a["doc"], a["quote"]) for a in anchors if a["status"] == "MATCH"]
        outside = sorted({doc_id for doc_id, _ in anchored if doc_id not in allowed})
        cover = [i + 1 for i, terms in enumerate(alternatives)
                 if all(any(cdoc == gdoc and phrase in quote for cdoc, quote in anchored)
                        for gdoc, phrase in terms)]
        support_ok = bool(cover) and not outside
        rows.append({"id": qid, "VALUE_MATCH": value_match, "ANCHOR_OK": anchor_ok,
                     "SUPPORT_OK": support_ok, "JOINT": value_match and anchor_ok and support_ok,
                     "proof_alternatives_matched": cover, "out_of_scope_anchored_docs": outside,
                     "anchors": anchors})
    names = ("VALUE_MATCH", "ANCHOR_OK", "SUPPORT_OK", "JOINT")
    return {"schema": SCORE_SCHEMA, "profile": PROFILE, "n_questions": len(rows),
            "totals": {key: sum(row[key] for row in rows) for key in names}, "questions": rows}


def _out(value: dict) -> None:
    # Keep bytes deterministic regardless of shell locale or text newline translation.
    sys.stdout.buffer.write((json.dumps(value, ensure_ascii=False, sort_keys=True,
                                        indent=2, allow_nan=False) + "\n").encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    manifest = subs.add_parser("manifest", help="generate expected corpus hashes")
    manifest.add_argument("--directory", required=True, type=Path)
    manifest.add_argument("--doc", required=True, action="append", help="ID=relative/path")
    scoring = subs.add_parser("audit", help="anchor then score against independently frozen gold")
    scoring.add_argument("--manifest", required=True, type=Path)
    scoring.add_argument("--gold", required=True, type=Path)
    scoring.add_argument("--answers", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            if any("=" not in item for item in args.doc):
                raise InvalidInput("--doc expects ID=relative/path")
            refs = [tuple(item.split("=", 1)) for item in args.doc]
            _out(build_manifest(args.directory, refs))
        else:
            docs = load_snapshots(args.manifest.parent, read_json(args.manifest))
            _out(audit(docs, read_json(args.gold), read_json(args.answers)))
    except InvalidInput as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
