"""Deterministic tests with fully synthetic locally constructed cases."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from audit import (CORPUS_SCHEMA, GOLD_SCHEMA, InvalidInput, PROFILE, audit,
                   build_manifest, load_snapshots, read_json)


class AuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        (self.base / "primary.txt").write_bytes("古😀cafe\u0301\r\n甲：有效结论70%。\r甲：附件未提交。\r\n".encode())
        (self.base / "proposal.txt").write_bytes("乙：提议80%。\n".encode())
        (self.base / "repeat.txt").write_bytes("aaaa\n单独可核验。\n".encode())
        self.refs = [("D2", "proposal.txt"), ("D1", "primary.txt"), ("D3", "repeat.txt")]
        self.manifest = build_manifest(self.base, self.refs)
        self.docs = load_snapshots(self.base, self.manifest)
        self.gold = {"schema": GOLD_SCHEMA, "questions": [
            {"id": "Q1", "status": "KNOWN", "value": "70%",
             "alternatives": [
                 [{"doc": "D1", "contains": "有效结论70%"}],
                 [{"doc": "D1", "contains": "café"}, {"doc": "D3", "contains": "单独可核验"}],
             ], "allowed_docs": ["D1", "D3"]},
            {"id": "Q2", "status": "UNKNOWN", "value": None,
             "alternatives": [[{"doc": "D1", "contains": "附件未提交"}]], "allowed_docs": ["D1"]},
        ]}
        self.answers = {"answers": [
            {"id": "Q1", "status": "KNOWN", "value": "70%",
             "evidence": [{"doc": "D1", "quote": "甲：有效结论70%。"}]},
            {"id": "Q2", "status": "UNKNOWN", "value": None,
             "evidence": [{"doc": "D1", "quote": "甲：附件未提交。"}]},
        ]}

    def scored(self, index=0):
        return audit(self.docs, self.gold, self.answers)["questions"][index]

    def test_normalization_codepoint_offsets_and_sha(self):
        self.assertEqual(self.manifest["schema"], CORPUS_SCHEMA)
        self.assertNotEqual(self.docs["D1"].raw_sha256, self.docs["D1"].normalized_sha256)
        self.answers["answers"][0]["evidence"][0]["quote"] = "cafe\u0301\r\n甲：有效结论70%。"
        output = audit(self.docs, self.gold, self.answers)
        self.assertEqual(output["profile"], PROFILE)
        q = output["questions"][0]
        span = q["anchors"][0]
        self.assertTrue(q["JOINT"])
        self.assertEqual(span["start"], 2)
        self.assertEqual(self.docs["D1"].text[span["start"]:span["end"]], span["quote"])
        self.assertEqual(span["normalized_sha256"], self.docs["D1"].normalized_sha256)
        self.assertEqual(output["totals"], {name: 2 for name in ("VALUE_MATCH", "ANCHOR_OK", "SUPPORT_OK", "JOINT")})

    def test_alternatives_require_complete_group(self):
        self.answers["answers"][0]["evidence"] = [{"doc": "D1", "quote": "café"}]
        self.assertFalse(self.scored()["SUPPORT_OK"])
        self.answers["answers"][0]["evidence"].append({"doc": "D3", "quote": "单独可核验。"})
        self.assertEqual(self.scored()["proof_alternatives_matched"], [2])
        self.assertTrue(self.scored()["JOINT"])

    def test_anchored_wrong_scope_is_not_support(self):
        self.answers["answers"][0]["evidence"] = [{"doc": "D2", "quote": "乙：提议80%。"}]
        row = self.scored()
        self.assertTrue(row["VALUE_MATCH"])
        self.assertTrue(row["ANCHOR_OK"])
        self.assertFalse(row["SUPPORT_OK"])
        self.assertEqual(row["out_of_scope_anchored_docs"], ["D2"])
        self.assertFalse(row["JOINT"])

    def test_gold_disallowed_extra_ref_blocks_joint(self):
        self.answers["answers"][0]["evidence"].append({"doc": "D2", "quote": "乙：提议80%。"})
        row = self.scored()
        self.assertTrue(row["ANCHOR_OK"])
        self.assertEqual(row["proof_alternatives_matched"], [1])
        self.assertFalse(row["SUPPORT_OK"])
        self.assertFalse(row["JOINT"])

    def test_allowed_background_is_not_required_but_is_permitted(self):
        self.answers["answers"][0]["evidence"].append({"doc": "D3", "quote": "单独可核验。"})
        self.assertTrue(self.scored()["JOINT"])

    def test_overlap_repetition_is_ambiguous(self):
        self.answers["answers"][0]["evidence"] = [{"doc": "D3", "quote": "aaa"}]
        row = self.scored()
        self.assertEqual(row["anchors"][0]["status"], "QUOTE_NOT_UNIQUE")
        self.assertFalse(row["ANCHOR_OK"])
        self.assertFalse(row["JOINT"])

    def test_duplicate_citation_is_rejected_even_if_proof_already_covered(self):
        refs = self.answers["answers"][0]["evidence"]
        refs.append(refs[0].copy())
        row = self.scored()
        self.assertEqual(row["anchors"][1]["status"], "DUPLICATE_CITATION")
        self.assertFalse(row["ANCHOR_OK"])
        self.assertFalse(row["JOINT"])

    def test_no_quote_and_wrong_quote_are_not_credited(self):
        for citation, error in (
            ([], None),
            ([{"doc": "D9", "quote": "甲：附件未提交。"}], "UNKNOWN_OR_UNAUTHORIZED_DOCUMENT"),
            ([{"doc": "D1", "quote": "甲：附件已提交。"}], "QUOTE_NOT_IN_DOCUMENT"),
            ([{"doc": "D1", "quote": "甲:附件未提交。"}], "QUOTE_NOT_IN_DOCUMENT"),
        ):
            with self.subTest(error=error):
                self.answers["answers"][1]["evidence"] = citation
                row = self.scored(1)
                self.assertTrue(row["VALUE_MATCH"])
                self.assertFalse(row["ANCHOR_OK"])
                self.assertFalse(row["JOINT"])
                if error:
                    self.assertEqual(row["anchors"][0]["status"], error)

    def test_exact_value_mismatch_independent_from_support(self):
        self.answers["answers"][0]["value"] = "70％"
        row = self.scored()
        self.assertFalse(row["VALUE_MATCH"])
        self.assertTrue(row["ANCHOR_OK"])
        self.assertTrue(row["SUPPORT_OK"])
        self.assertFalse(row["JOINT"])

    def test_snapshot_rejects_raw_change_even_if_normalization_equal(self):
        (self.base / "primary.txt").write_text(self.docs["D1"].text, encoding="utf-8")
        with self.assertRaisesRegex(InvalidInput, "snapshot hash mismatch"):
            load_snapshots(self.base, self.manifest)

    def test_strict_utf8_and_bom_even_ascii_tail(self):
        broken = self.base / "error.txt"
        for content, diagnostic in ((b"\xef\xbb\xbftext", "BOM"), (b"\xfftext", "UTF-8")):
            broken.write_bytes(content)
            with self.assertRaisesRegex(InvalidInput, diagnostic):
                build_manifest(self.base, [("D1", broken.name)])

    def test_invalid_paths_or_duplicate_manifest_labels(self):
        for refs in (
            [("D1", "primary.txt"), ("D1", "repeat.txt")],
            [("D1", "primary.txt"), ("D2", "primary.txt")],
            [("D1", "../primary.txt")],
            [("D1", str(self.base / "primary.txt"))],
        ):
            with self.subTest(refs=refs):
                with self.assertRaises(InvalidInput):
                    build_manifest(self.base, refs)
        (self.base / "alias.txt").symlink_to(self.base / "primary.txt")
        with self.assertRaisesRegex(InvalidInput, "symlink"):
            build_manifest(self.base, [("D1", "alias.txt")])

    def test_invalid_answer_shape_and_type(self):
        mutations = [
            lambda a: a["answers"][1].__setitem__("value", ""),
            lambda a: a["answers"][1].__setitem__("id", "Q1"),
            lambda a: a["answers"][1].__setitem__("id", "Q8"),
            lambda a: a["answers"].pop(),
            lambda a: a["answers"][0].__setitem__("note", 1),
            lambda a: a["answers"][0].__setitem__("value", 70),
            lambda a: a["answers"][0]["evidence"][0].__setitem__("quote", "x" * 321),
            lambda a: a["answers"][0]["evidence"][0].__setitem__("quote", "\ud800"),
            lambda a: a["answers"][0].__setitem__("evidence", [{}] * 9),
        ]
        for mutation in mutations:
            duplicate = json.loads(json.dumps(self.answers))
            mutation(duplicate)
            with self.assertRaises(InvalidInput):
                audit(self.docs, self.gold, duplicate)

    def test_json_duplicate_keys_and_non_json_constants_rejected(self):
        path = self.base / "input.json"
        for text in ('{"answers":[],"answers":[]}', '{"x":NaN}', '[] trailing'):
            path.write_text(text, encoding="utf-8")
            with self.subTest(text=text):
                with self.assertRaises(InvalidInput):
                    read_json(path)

    def test_invalid_gold_support_is_not_silently_ignored(self):
        self.gold["questions"][0]["alternatives"][0][0]["contains"] = "永远不存在"
        with self.assertRaisesRegex(InvalidInput, "gold phrase"):
            self.scored()

    def test_cli_reports_error_without_partial_score(self):
        for name, item in (("manifest", self.manifest), ("gold", self.gold), ("answers", {"answers": []})):
            (self.base / (name + ".json")).write_text(json.dumps(item), encoding="utf-8")
        script = Path(__file__).with_name("audit.py")
        args = [sys.executable, "-B", str(script), "audit"]
        for name in ("manifest", "gold", "answers"):
            args.extend(("--" + name, str(self.base / (name + ".json"))))
        bad = subprocess.run(args, capture_output=True, check=False)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, b"")
        self.assertIn(b"Invalid input", bad.stderr)
        (self.base / "answers.json").write_text(json.dumps(self.answers), encoding="utf-8")
        ok = subprocess.run(args, capture_output=True, check=False)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["totals"]["JOINT"], 2)


if __name__ == "__main__":
    unittest.main()
