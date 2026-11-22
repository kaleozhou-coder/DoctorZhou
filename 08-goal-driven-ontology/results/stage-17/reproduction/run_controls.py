"""Deliberately constructed controls seeded from reference labels; never model runs."""
import argparse
import copy
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import audit as judge


def row(report, key):
    return next(q for q in report["questions"] if q["id"] == key)


def run(frozen):
    manifest = judge.read_json(frozen / "manifest.json")
    gold = judge.read_json(frozen / "gold.json")
    docs = judge.load_snapshots(frozen, manifest)
    answers = {"answers": []}
    for q in gold["questions"]:
        evidence = [{"doc": c["doc"], "quote": c["contains"]} for c in q["alternatives"][0]]
        answers["answers"].append({k: q[k] for k in ("id", "status", "value")} | {"evidence": evidence})
    n = len(answers["answers"])
    base = judge.audit(docs, gold, answers)
    assert base["totals"]["JOINT"] == n
    cases = [
        ("same_words_unsigned_draft", "Q6", [{"doc": "D6", "quote": "夜间自助通道开放至22:30"}],
         True, "MATCH"),
        ("missing_second_half_of_gap_proof", "Q5", [{"doc": "D1", "quote": "现场照片数量见该附件§7"}],
         True, "MATCH"),
        ("ambiguous_short_string", "Q7", [{"doc": "D5", "quote": "标包"}],
         False, "QUOTE_NOT_UNIQUE"),
        ("fabricated_span", "Q6", [{"doc": "D7", "quote": "夜间自助通道开放至22:31"}],
         False, "QUOTE_NOT_IN_DOCUMENT"),
        ("unknown_document", "Q6", [{"doc": "D900", "quote": "夜间自助通道开放至22:30"}],
         False, "UNKNOWN_OR_UNAUTHORIZED_DOCUMENT"),
    ]
    results = [{"case": "label_seeded_exact_control", "n_questions": n, "totals": base["totals"]}]
    for name, key, evidence, anchor, state in cases:
        probe = copy.deepcopy(answers)
        next(a for a in probe["answers"] if a["id"] == key)["evidence"] = evidence
        q = row(judge.audit(docs, gold, probe), key)
        assert q["VALUE_MATCH"] and q["ANCHOR_OK"] is anchor and not q["SUPPORT_OK"] and not q["JOINT"]
        assert q["anchors"][0]["status"] == state
        results.append({"case": name, "id": key, "value_matches": True, "anchor_ok": anchor,
                        "support_ok": False, "joint": False, "anchor_status": state})
    with TemporaryDirectory() as dirname:
        temp = Path(dirname)
        shutil.copytree(frozen / "documents", temp / "documents")
        target = temp / "documents" / "D2.txt"
        original = target.read_bytes()
        assert b"\n" in original
        target.write_bytes(original.replace(b"\n", b"\r\n"))
        try:
            judge.load_snapshots(temp, manifest)
        except judge.InvalidInput as e:
            assert "snapshot hash mismatch" in str(e)
        else:
            raise AssertionError("raw rendition change was accepted")
    results.append({"case": "raw_changed_same_normalized_rendition", "error": "document snapshot hash mismatch"})
    return results


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("frozen", type=Path)
    args = cli.parse_args()
    print(json.dumps(run(args.frozen), ensure_ascii=False, indent=2))
