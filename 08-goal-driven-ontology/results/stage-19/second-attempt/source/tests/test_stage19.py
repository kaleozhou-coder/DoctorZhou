"""Unit tests of the paired review simulator; not derived from experiment corpus/gold."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from src.evidence_gate import build_snapshot
from src.stage19 import Invalid, assert_vendored_gate, run_all, score, select, simulate


def job(slot_id, priority, old_state):
    text = "正式条款：上限为 70%。\r\n"
    snap = build_snapshot(text.encode())
    quote = "上限为 70%"
    start = snap["text"].index(quote)
    end = start + len(quote)
    clause = {"id": "c", "scope": "S", "field": slot_id, "role": "DIRECT",
              "quote": quote, "start": start, "end": end, "value": "70%"}
    document = {"doc": "D", "rev": "R2", "rendition": "N", "project": "P", "text": text,
                "readable": True, "clauses": [clause]}
    cert = {"doc": "D", "rev": "R2", "rendition": "N", "clause": "c",
            "role": "DIRECT", "quote": quote, "start": start, "end": end,
            "raw_sha256": snap["raw_sha256"], "normalized_sha256": snap["normalized_sha256"]}
    review = {"decision": {"state": "KNOWN", "value": "70%"}, "evidence": [cert], "gap": None}
    if old_state == "UNKNOWN":
        old = {"decision": {"state": "UNKNOWN", "value": None}, "evidence": [], "gap": None}
    else:
        old = copy.deepcopy(review)
    return {"id": slot_id, "priority": priority, "intake_signal": "共同优先级信号",
            "old": old, "reviewed": review, "gate_registry": {
                "question": {"project": "P", "scope": "S", "field": slot_id},
                "documents": [document], "required_direct": ["D:R2:N:c"], "required_gap": None,
            }}


def experiment():
    family = {"family": "Z", "title": "内部构造样例", "slots": [
        job("s7", 7, "UNKNOWN"), job("s5", 5, "KNOWN"), job("s6", 6, "UNKNOWN"),
        job("s3", 3, "KNOWN"), job("s2", 2, "KNOWN"), job("s4", 4, "KNOWN"),
        job("s1", 1, "KNOWN"),
    ]}
    gold = {"families": [{"family": "Z", "slots": [
        {"id": row["id"], "transition": "recover_unknown" if row["old"]["decision"]["state"] == "UNKNOWN"
         else "stable_known", "final": {"state": "KNOWN", "value": "70%"},
         "expected": {"status": "ELIGIBLE", "reason": "DIRECT_VERIFIED"}}
        for row in family["slots"]
    ]}]}
    return family, gold


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.family, self.gold = experiment()
        self.cases = {s["id"]: s for s in self.family["slots"]}
        self.data = {"families": [self.family]}

    def run_both(self):
        return run_all(self.data, "A"), run_all(self.data, "B")

    def test_exact_gate_and_independent_cli_commands(self):
        assert_vendored_gate()
        script = pathlib.Path(__file__).resolve().parents[1] / "src" / "stage19.py"
        with tempfile.TemporaryDirectory() as directory:
            p = pathlib.Path(directory)
            corpus = p / "input.json"
            corpus.write_text(json.dumps(self.data), encoding="utf-8")
            outs = []
            gold = p / "oracle.json"
            self.assertFalse(gold.exists())
            for arm in ("A", "B"):
                result = subprocess.run([sys.executable, "-B", str(script), "run",
                                         "--input", str(corpus), "--arm", arm],
                                        check=True, capture_output=True)
                out = p / f"{arm}.json"
                out.write_bytes(result.stdout)
                outs.append(str(out))
            gold.write_text(json.dumps(self.gold), encoding="utf-8")
            scored = subprocess.run([sys.executable, "-B", str(script), "score", "--observed-a", outs[0],
                                     "--observed-b", outs[1], "--gold", str(gold)],
                                    check=True, capture_output=True)
            self.assertEqual(json.loads(scored.stdout)["recovery_direction_by_family"]["B_higher"], 1)

    def test_common_rank_b_forces_two_but_does_not_cap_all_unknowns(self):
        a, b = self.run_both()
        self.assertEqual(a["families"][0]["selected"], ["s1", "s2", "s3", "s4"])
        self.assertEqual(b["families"][0]["selected"], ["s6", "s7", "s1", "s2"])
        all_u = [{"id": f"s{i}", "old_state": "UNKNOWN", "priority": i} for i in range(5)]
        self.assertEqual(select(all_u, "A"), select(all_u, "B"))

    def test_ties_and_permuting_input_changes_neither_arm(self):
        for item in self.family["slots"]:
            item["priority"] = 3
        before = self.run_both()
        self.family["slots"].reverse()
        self.family["title"] = "不影响任何排序"
        self.assertEqual(self.run_both(), before)
        self.assertEqual(before[0]["families"][0]["selected"], ["s1", "s2", "s3", "s4"])

    def test_no_or_one_unknown_fill_uses_no_duplicates_and_still_four(self):
        for n_unknown in (0, 1):
            ordinary = [{"id": f"s{i}", "old_state": "UNKNOWN" if i < n_unknown else "KNOWN",
                          "priority": 4 - i} for i in range(5)]
            selected = select(ordinary, "B")
            self.assertEqual(len(set(selected)), 4)
            self.assertEqual(("s0" in selected), bool(n_unknown))

    def test_only_selected_review_payload_is_applied(self):
        self.cases["s6"]["reviewed"] = None  # invalid if submitted; A does not submit it
        simulated = simulate(self.family, "A")
        s6 = next(row for row in simulated["slots"] if row["id"] == "s6")
        self.assertEqual(s6["old"], s6["final"])
        self.assertEqual(s6["final"]["gate"]["status"], "BLOCKED")
        with self.assertRaises(Invalid):
            simulate(self.family, "B")

    def test_unreviewed_old_claim_is_rechecked_on_new_registry(self):
        original = copy.deepcopy(self.cases["s5"]["old"])
        self.cases["s5"]["gate_registry"]["documents"][0]["readable"] = False
        for result in self.run_both():
            item = next(row for row in result["families"][0]["slots"] if row["id"] == "s5")
            self.assertFalse(item["selected"])
            self.assertEqual(item["final"]["decision"], original["decision"])
            self.assertEqual(item["final"]["gate"], {"status": "BLOCKED", "reason": "SOURCE_NOT_ADMISSIBLE"})

    def test_paired_recovery_and_stable_regression_have_distinct_denominators(self):
        self.cases["s1"]["reviewed"]["evidence"][0]["role"] = "CONTEXT"
        a, b = self.run_both()
        scored = score(a, b, self.gold)
        fam = scored["families"][0]
        self.assertEqual(fam["paired_recovery"], {"denominator": 2, "A_only": 0, "B_only": 2, "both": 0, "neither": 0})
        self.assertEqual(fam["A"]["stable_known_regression"], 1)
        self.assertEqual(fam["B"]["stable_known_regression"], 1)
        self.assertEqual(fam["A"]["previously_joint_stable_known"], 5)
        self.assertEqual(fam["B"]["role_mismatch_block"], 1)
        self.assertEqual(fam["B"]["value_correct_without_joint"], 1)
        self.assertEqual(scored["gate_false_block_technical"]["status"], "N/A")
        self.assertEqual(fam["selection"]["B_only"], ["s6", "s7"])

    def test_shared_reviewer_disagreement_rejected_by_score(self):
        a, b = self.run_both()
        item = next(row for row in b["families"][0]["slots"] if row["id"] == "s1")
        item["final"]["gate"] = {"status": "BLOCKED", "reason": "MUTATION"}
        with self.assertRaisesRegex(Invalid, "reviewer outcome"):
            score(a, b, self.gold)

    def test_malformed_gate_input_is_system_failure_not_unknown(self):
        self.cases["s2"]["reviewed"]["evidence"][0]["start"] = False
        a, b = self.run_both()
        scores = score(a, b, self.gold)["families"][0]
        self.assertEqual(scores["A"]["system_failure"], 1)
        self.assertEqual(scores["A"]["candidate_blocked_on_ideal_target"], 2)
        # Blocked on an ideal target includes two old unresolved s6/s7 in A,
        # not the additional system failure s2.
        self.assertEqual(scores["A"]["missed_review_eligibility"], 3)

    def test_correct_value_with_wrong_evidence_not_false_block(self):
        self.cases["s1"]["reviewed"]["evidence"][0]["rev"] = "OLD"
        observed = self.run_both()
        summary = score(*observed, self.gold)
        self.assertEqual(summary["families"][0]["B"]["value_correct_without_joint"], 1)
        self.assertEqual(summary["families"][0]["B"]["candidate_blocked_on_ideal_target"], 1)
        self.assertEqual(summary["gate_false_block_technical"]["status"], "N/A")

    def test_duplicate_ids_and_invalid_budget_refused(self):
        queue = [{"id": f"x{i}", "priority": i, "old_state": "KNOWN"} for i in range(4)]
        for shape in (queue[:-1], queue + [queue[0]], [queue[0] | {"priority": True}] + queue[1:]):
            with self.assertRaises(Invalid):
                select(shape, "A")


if __name__ == "__main__":
    unittest.main()
