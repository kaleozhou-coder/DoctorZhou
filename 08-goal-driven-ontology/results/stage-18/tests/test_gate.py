"""Unit tests for Stage18 contracts. All input strings and roles are synthetic."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.evidence_gate import GateError, build_snapshot, run_gate


def fixture(doc="D1", role="DIRECT", quote="正式范围的阈值是70%。",
            raw=None, index=0, scope="LOT1", field="LIMIT", readable=True,
            rev="R1", rendition="T1", project="P1"):
    raw = raw if raw is not None else f"项😀目e\u0301\r\n{quote}\r\n末句"
    snap = build_snapshot(raw.encode("utf-8"))
    start = snap["text"].find(quote, index)
    assert start >= 0
    end = start + len(quote)
    clause = {"id": "C1", "scope": scope, "field": field, "role": role, "quote": quote,
              "start": start, "end": end}
    if role == "DIRECT":
        clause["value"] = "70%"
    record = {"doc": doc, "rev": rev, "rendition": rendition, "project": project, "text": raw,
              "readable": readable, "clauses": [clause]}
    citation = {"doc": doc, "rev": rev, "rendition": rendition, "clause": clause["id"],
                "role": role, "quote": quote, "start": start, "end": end,
                "raw_sha256": snap["raw_sha256"], "normalized_sha256": snap["normalized_sha256"]}
    return record, citation, f"{doc}:{rev}:{rendition}:C1"


class GateTests(unittest.TestCase):
    def setUp(self):
        self.source, self.cite, self.locator = fixture()
        self.registry = {"question": {"project": "P1", "scope": "LOT1", "field": "LIMIT"},
                         "documents": [self.source], "required_direct": [self.locator], "required_gap": None}
        self.candidate = {"decision": {"state": "KNOWN", "value": "70%"}, "evidence": [self.cite], "gap": None}

    def verdict(self, status, reason):
        self.assertEqual(run_gate(self.registry, self.candidate), {"status": status, "reason": reason})

    def test_verified_normalized_cp_with_raw_identity(self):
        self.assertEqual(self.cite["start"], 5)
        self.assertNotEqual(self.cite["raw_sha256"], self.cite["normalized_sha256"])
        reg, req = copy.deepcopy(self.registry), copy.deepcopy(self.candidate)
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")
        self.assertEqual(self.registry, reg)
        self.assertEqual(self.candidate, req)
        self.cite.update(start=None, end=None)
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")

    def test_hash_mismatch_even_if_normalized_text_equal(self):
        self.source["text"] = build_snapshot(self.source["text"].encode())["text"]
        self.verdict("BLOCKED", "EVIDENCE_HASH_MISMATCH")

    def test_normalized_hash_mismatch(self):
        self.cite["normalized_sha256"] = "0" * 64
        self.verdict("BLOCKED", "EVIDENCE_HASH_MISMATCH")

    def test_unapproved_versions_and_renditions(self):
        for key in ("rev", "rendition", "doc"):
            original = self.cite[key]
            self.cite[key] = "OTHER"
            self.verdict("BLOCKED", "SOURCE_NOT_ADMISSIBLE")
            self.cite[key] = original

    def test_unreadable_without_disclosure_even_if_hash_is_wrong(self):
        self.source["readable"] = False
        self.cite["raw_sha256"] = "0" * 64
        self.verdict("BLOCKED", "SOURCE_NOT_ADMISSIBLE")

    def test_unapproved_clause(self):
        self.cite["clause"] = "ABSENT"
        self.verdict("BLOCKED", "CLAUSE_NOT_ADMISSIBLE")

    def test_ambiguous_overlap_rejected_only_in_unpositioned_tier(self):
        first, citation, locator = fixture(quote="aaa", raw="aaaa")
        self.registry.update(documents=[first], required_direct=[locator])
        self.candidate["evidence"] = [citation]
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")
        citation.update(start=None, end=None)
        self.verdict("BLOCKED", "QUOTE_SPAN_MISMATCH")
        citation.update(start=1, end=4)
        self.verdict("BLOCKED", "QUOTE_SPAN_MISMATCH")

    def test_wrong_quote_or_bad_span(self):
        original = self.cite.copy()
        for diff in ({"quote": "非原文"}, {"start": -1}, {"end": 999}, {"end": self.cite["start"]}):
            self.candidate["evidence"] = [original | diff]
            self.verdict("BLOCKED", "QUOTE_SPAN_MISMATCH")

    def test_matching_quote_cannot_cross_scope_field_or_project(self):
        for kw, code in (({"scope": "LOT2"}, "DIRECT_SCOPE_MISMATCH"),
                         ({"field": "DEADLINE"}, "DIRECT_SCOPE_MISMATCH"),
                         ({"project": "P2"}, "SOURCE_NOT_ADMISSIBLE")):
            foreign, cited, _ = fixture(doc="D2", **kw)
            self.registry["documents"] = [self.source, foreign]
            self.candidate["evidence"] = [self.cite, cited]
            self.verdict("BLOCKED", code)

    def test_role_promotion_rejected_and_context_alone_not_enough(self):
        d2, c2, _ = fixture(doc="D2", role="CONTEXT")
        self.registry["documents"].append(d2)
        self.candidate["evidence"] = [c2 | {"role": "DIRECT"}]
        self.verdict("BLOCKED", "EVIDENCE_ROLE_MISMATCH")
        self.candidate["evidence"] = [c2]
        self.verdict("BLOCKED", "REQUIRED_DIRECT_MISSING")

    def test_exact_direct_set_no_vacuous_or_extra(self):
        d2, c2, l2 = fixture(doc="D2", rev="R2")
        self.registry["documents"].append(d2)
        self.registry["required_direct"].append(l2)
        self.verdict("BLOCKED", "REQUIRED_DIRECT_MISSING")
        self.candidate["evidence"].append(c2)
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")
        self.registry["required_direct"].pop()
        self.verdict("BLOCKED", "REQUIRED_DIRECT_MISSING")
        self.registry["required_direct"] = []
        self.candidate["evidence"] = []
        self.verdict("BLOCKED", "REQUIRED_DIRECT_MISSING")

    def test_direct_complement_requires_some_asserted_value_and_all_agree(self):
        d2, c2, l2 = fixture(doc="D2", quote="签署生效已登记。")
        d2["clauses"][0].pop("value")
        self.registry["documents"].append(d2)
        self.registry["required_direct"].append(l2)
        self.candidate["evidence"].append(c2)
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")
        d2["clauses"][0]["value"] = "65%"
        self.verdict("BLOCKED", "DIRECT_VALUE_MISMATCH")
        d2["clauses"][0]["value"] = None
        self.source["clauses"][0].pop("value")
        self.verdict("BLOCKED", "DIRECT_VALUE_MISMATCH")

    def test_wrong_value_despite_valid_proof_position(self):
        self.candidate["decision"]["value"] = "70％"
        self.verdict("BLOCKED", "DIRECT_VALUE_MISMATCH")

    def test_active_conflict_cannot_be_omitted(self):
        d2, _, _ = fixture(doc="D2", role="CONFLICT", quote="同范围另一份文件仍写60%。")
        self.registry["documents"].append(d2)
        self.verdict("BLOCKED", "CONFLICT_PRESENT")
        d2["clauses"][0]["scope"] = "LOT2"
        self.verdict("ELIGIBLE", "DIRECT_VERIFIED")

    def test_duplicate_citation_cannot_hide_failure(self):
        self.candidate["evidence"].append(self.cite.copy())
        self.verdict("BLOCKED", "DUPLICATE_EVIDENCE")

    def prepare_gap(self):
        gap_doc, gap_cite, locator = fixture(doc="INDEX", role="CONTEXT", quote="当前附件第三条缺失。")
        target = {"doc": "ANNEX", "rev": "A2", "clause": "SEC3", "scope": "LOT1",
                  "field": "LIMIT", "locator": locator}
        self.registry["documents"].append(gap_doc)
        self.registry["required_gap"] = target.copy()
        self.candidate.update(decision={"state": "UNKNOWN", "value": None},
                              evidence=[gap_cite], gap=target.copy())
        return target, gap_cite

    def test_exact_gap_is_pending_and_wrong_version_or_locator_is_blocked(self):
        target, _ = self.prepare_gap()
        self.verdict("PENDING", "REQUIRED_GAP_VERIFIED")
        for diff in ({"rev": "A1"}, {"clause": "SEC4"}, {"scope": "LOT2"}, {"locator": self.locator}):
            self.candidate["gap"] = target | diff
            self.verdict("BLOCKED", "REQUIRED_GAP_MISMATCH")
        self.candidate.update(gap=target, evidence=[])
        self.verdict("BLOCKED", "REQUIRED_GAP_MISMATCH")

    def test_gap_cannot_be_solved_with_direct_or_known_assertion(self):
        _, gap_cite = self.prepare_gap()
        self.candidate["evidence"] = [self.cite, gap_cite]
        self.verdict("BLOCKED", "UNKNOWN_WITH_DIRECT")
        self.candidate.update(decision={"state": "KNOWN", "value": "70%"}, gap=None, evidence=[self.cite])
        self.verdict("BLOCKED", "REQUIRED_GAP_MISMATCH")

    def test_invalid_model_shape_no_verdict(self):
        for bad in (self.candidate | {"oracle": "ELIGIBLE"},
                    self.candidate | {"decision": {"state": "UNKNOWN", "value": "70%"}},
                    self.candidate | {"evidence": [self.cite | {"start": True}]},
                    self.candidate | {"evidence": [self.cite | {"start": None}]},
                    self.candidate | {"evidence": [self.cite | {"quote": "\ud800"}]}):
            with self.assertRaises(GateError):
                run_gate(self.registry, bad)

    def test_invalid_registry_cannot_establish_authority(self):
        self.source["clauses"][0]["end"] += 1
        with self.assertRaises(GateError):
            run_gate(self.registry, self.candidate)

    def test_bom_and_invalid_utf8(self):
        for raw in (b"\xef\xbb\xbfabc", b"\xffabc", b"\n\t"):
            with self.assertRaises(GateError):
                build_snapshot(raw)

    def test_cli_shapes_and_leak_free_invalid_output(self):
        cli = Path(__file__).resolve().parents[1] / "src" / "evidence_gate.py"
        with tempfile.TemporaryDirectory() as d:
            reg, req = Path(d) / "registry.json", Path(d) / "request.json"
            reg.write_text(json.dumps(self.registry), encoding="utf-8")
            req.write_text(json.dumps(self.candidate), encoding="utf-8")
            command = [sys.executable, "-B", str(cli), "--registry", str(reg), "--request", str(req)]
            good = subprocess.run(command, capture_output=True, check=False)
            self.assertEqual(good.returncode, 0)
            self.assertEqual(json.loads(good.stdout), {"status": "ELIGIBLE", "reason": "DIRECT_VERIFIED"})
            req.write_text('{"extra":"never_echo_case_data","extra":2}', encoding="utf-8")
            bad = subprocess.run(command, capture_output=True, check=False)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(bad.stdout, b"")
            self.assertNotIn(b"never_echo_case_data", bad.stderr)


if __name__ == "__main__":
    unittest.main()
