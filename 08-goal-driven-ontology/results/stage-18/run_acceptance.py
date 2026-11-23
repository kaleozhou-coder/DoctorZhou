#!/usr/bin/env python3
"""Use only reviewed registry + candidate in gate; compare results outside gate."""
import argparse
from collections import Counter
import json
from pathlib import Path
from src.evidence_gate import run_gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    families = json.loads(args.fixtures.read_text(encoding="utf-8"))
    assert isinstance(families, list) and len(families) >= 6
    assert len({f["family"] for f in families}) == len(families)
    seen = set()
    rows = []
    counts = Counter()
    for family in families:
        family_id = family["family"]
        registry = family["registry"]
        good_count = sum(c["expected"]["status"] in ("ELIGIBLE", "PENDING") for c in family["cases"])
        bad_count = sum(c["expected"]["status"] == "BLOCKED" for c in family["cases"])
        assert good_count and bad_count, family_id
        for case in family["cases"]:
            key = (family_id, case["id"])
            assert key not in seen, key
            seen.add(key)
            got = run_gate(registry, case["candidate"])
            expected = case["expected"]
            match = all(got.get(k) == expected[k] for k in ("status", "reason"))
            counts[f'expected_{expected["status"]}'] += 1
            counts[f'observed_{got["status"]}'] += 1
            counts["joint_exact"] += match
            counts["status_exact"] += got["status"] == expected["status"]
            counts["incorrect_eligible"] += got["status"] == "ELIGIBLE" and expected["status"] != "ELIGIBLE"
            counts["correct_eligible"] += got["status"] == expected["status"] == "ELIGIBLE"
            counts["correct_pending"] += got["status"] == expected["status"] == "PENDING"
            counts["ungated_known_unsafe"] += expected["status"] != "ELIGIBLE" and case["candidate"]["decision"]["state"] == "KNOWN"
            rows.append({"family": family_id, "id": case["id"], "expected": expected,
                         "observed": {k: got[k] for k in ("status", "reason")}, "joint_exact": match})
    report = {"families": len(families), "cases": len(rows), "counts": dict(counts), "rows": rows}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return 0 if counts["joint_exact"] == len(rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())
