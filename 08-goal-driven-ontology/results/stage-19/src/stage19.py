"""Deterministic paired review-slot simulation. Run without gold; score separately."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .evidence_gate import GateError, run_gate
except ImportError:  # direct CLI invocation
    from evidence_gate import GateError, run_gate

STAGE18_SHA256 = "b65c4c8b14c0709ea49c0c3558eadd2a5bcd2f7325b3fff5b451d037a3dac02b"
ARMS = ("A", "B")
STATES = {"KNOWN", "UNKNOWN"}
GATES = {"ELIGIBLE", "PENDING", "BLOCKED", "SYSTEM_FAILURE"}
TRANSITIONS = ("recover_unknown", "stay_unknown", "update_known", "stable_known", "reopen_known")
BUDGET = 4
RESERVE = 2
SCHEMA = "stage19-simulation-v1"


class Invalid(ValueError):
    pass


def _obj(value, req, optional=()):
    req, optional = set(req), set(optional)
    if not isinstance(value, dict) or not req <= value.keys() or value.keys() - req - optional:
        raise Invalid("unexpected object shape")
    return value


def _list(value, *, minimum=0, maximum=256):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise Invalid("unexpected list shape")
    return value


def _label(value):
    if not isinstance(value, str) or not 0 < len(value) <= 256 or value != value.strip():
        raise Invalid("invalid label")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise Invalid("invalid label")
    return value


def _claim(value):
    data = _obj(value, {"state", "value"})
    if data["state"] == "KNOWN":
        _label(data["value"])
    elif data["state"] != "UNKNOWN" or data["value"] is not None:
        raise Invalid("invalid decision")
    return dict(data)


def _gate_result(value, *, allow_failure=True):
    data = _obj(value, {"status", "reason"})
    if (not isinstance(data["status"], str) or data["status"] not in GATES
            or (not allow_failure and data["status"] == "SYSTEM_FAILURE")):
        raise Invalid("invalid gate status")
    _label(data["reason"])
    return dict(data)


def _index(records, name):
    result = {}
    for record in records:
        if not isinstance(record, dict):
            raise Invalid("expected record")
        key = _label(record.get(name))
        if key in result:
            raise Invalid("duplicate identity")
        result[key] = record
    return result


def _fields(records):
    return _index(_list(records, minimum=BUDGET), "id")


def _families(data):
    if isinstance(data, dict):
        data = _obj(data, {"families"})["families"]
    return _index(_list(data, minimum=1, maximum=128), "family")


def select(queue: list[dict], arm: str) -> list[str]:
    """Selection can only see id, declared priority and historical state."""
    if arm not in ARMS:
        raise Invalid("arm must be A or B")
    indexed = _fields(queue)
    for row in indexed.values():
        _obj(row, {"id", "priority", "old_state"})
        if type(row["priority"]) is not int or not 0 <= row["priority"] <= 1_000_000:
            raise Invalid("invalid priority; lower non-negative integer wins")
        if not isinstance(row["old_state"], str) or row["old_state"] not in STATES:
            raise Invalid("invalid old state")
    ranking = sorted(indexed, key=lambda slot: (indexed[slot]["priority"], slot))
    if arm == "A":
        return ranking[:BUDGET]
    reserved = [slot for slot in ranking if indexed[slot]["old_state"] == "UNKNOWN"][:RESERVE]
    fill = [slot for slot in ranking if slot not in reserved]
    return (reserved + fill)[:BUDGET]


def _replay(registry, candidate):
    try:
        return _gate_result(run_gate(registry, candidate))
    except GateError:
        return {"status": "SYSTEM_FAILURE", "reason": "GATE_INPUT_INVALID"}


def simulate(family: dict, arm: str) -> dict:
    family = _obj(family, {"family", "slots"}, {"title"})
    if "title" in family:
        _label(family["title"])
    name = _label(family["family"])
    slots = _fields(family["slots"])
    queue, old_claims = [], {}
    for key, slot in slots.items():
        _obj(slot, {"id", "priority", "old", "reviewed", "gate_registry"}, {"intake_signal"})
        if "intake_signal" in slot:
            _label(slot["intake_signal"])
        old = _obj(slot["old"], {"decision", "evidence", "gap"})
        old_claims[key] = _claim(old["decision"])
        queue.append({"id": key, "priority": slot["priority"], "old_state": old_claims[key]["state"]})
    selected = select(queue, arm)
    chosen = set(selected)
    rows = []
    for key, slot in sorted(slots.items()):
        old = slot["old"]
        old_gate = _replay(slot["gate_registry"], old)
        if key in chosen:
            reviewed = _obj(slot["reviewed"], {"decision", "evidence", "gap"})
            final_claim = _claim(reviewed["decision"])
            final_gate = _replay(slot["gate_registry"], reviewed)
        else:
            final_claim = dict(old_claims[key])
            final_gate = dict(old_gate)
        rows.append({"id": key, "selected": key in chosen,
                     "old": {"decision": old_claims[key], "gate": old_gate},
                     "final": {"decision": final_claim, "gate": final_gate}})
    by_id = {x["id"]: x for x in queue}
    return {"family": name, "arm": arm, "budget": BUDGET,
            "ranked": [x["id"] for x in sorted(queue, key=lambda x: (x["priority"], x["id"]))],
            "selected": selected,
            "selected_old_unknown": sum(by_id[key]["old_state"] == "UNKNOWN" for key in chosen),
            "slots": rows}


def run_all(data, arm: str) -> dict:
    families = _families(data)
    return {"schema": SCHEMA, "arm": arm,
            "families": [simulate(families[name], arm) for name in sorted(families)]}


def _match(observed: dict, expected_decision: dict, expected_gate: dict) -> tuple[bool, bool, bool]:
    return (observed["decision"] == expected_decision,
            observed["gate"] == expected_gate,
            observed["decision"] == expected_decision and observed["gate"] == expected_gate)


def _load_output(data, arm: str):
    data = _obj(data, {"schema", "arm", "families"})
    if data["schema"] != SCHEMA or data["arm"] != arm:
        raise Invalid("output schema or arm mismatch")
    return _families(data["families"])


def _gold_rows(gold: dict) -> dict:
    data = _obj(gold, {"families"}) if isinstance(gold, dict) else gold
    families = _families(data)
    out = {}
    for key, family in families.items():
        _obj(family, {"family", "slots"})
        labeled = _fields(family["slots"])
        bucket = {}
        for slot_id, raw in labeled.items():
            record = _obj(raw, {"id", "transition", "expected", "final"})
            if record["transition"] not in TRANSITIONS:
                raise Invalid("unsupported transition")
            decision, gate = _claim(record["final"]), _gate_result(record["expected"], allow_failure=False)
            if gate["status"] == "ELIGIBLE" and decision["state"] != "KNOWN":
                raise Invalid("gold cannot expect eligible UNKNOWN")
            if gate["status"] == "PENDING" and decision["state"] != "UNKNOWN":
                raise Invalid("gold cannot expect pending KNOWN")
            expected_state = "UNKNOWN" if record["transition"] in {"stay_unknown", "reopen_known"} else "KNOWN"
            if decision["state"] != expected_state:
                raise Invalid("gold transition contradicts final state")
            bucket[slot_id] = (record["transition"], decision, gate)
        out[key] = bucket
    return out


def _observed_rows(family: dict, arm: str, expected: dict) -> dict:
    family = _obj(family, {"family", "arm", "budget", "ranked", "selected",
                           "selected_old_unknown", "slots"})
    if family["arm"] != arm or family["budget"] != BUDGET:
        raise Invalid("wrong arm or review budget")
    ranked = [_label(x) for x in _list(family["ranked"], minimum=BUDGET)]
    selected = [_label(x) for x in _list(family["selected"], minimum=BUDGET, maximum=BUDGET)]
    rows = _fields(family["slots"])
    if (set(rows) != set(expected) or set(ranked) != set(rows) or len(ranked) != len(rows)
            or len(set(selected)) != BUDGET or not set(selected) <= set(rows)):
        raise Invalid("result rows/rank/selection differ from frozen identities")
    rebuilt = {}
    unknown_selected = 0
    for k, row in rows.items():
        _obj(row, {"id", "selected", "old", "final"})
        if type(row["selected"]) is not bool or row["selected"] != (k in selected):
            raise Invalid("selection indicator mismatch")
        phases = []
        for phase in ("old", "final"):
            data = _obj(row[phase], {"decision", "gate"})
            phases.append({"decision": _claim(data["decision"]), "gate": _gate_result(data["gate"])})
        if not row["selected"] and phases[0] != phases[1]:
            raise Invalid("unreviewed field changed")
        unknown_selected += int(row["selected"] and phases[0]["decision"]["state"] == "UNKNOWN")
        rebuilt[k] = phases
    if family["selected_old_unknown"] != unknown_selected:
        raise Invalid("selected old UNKNOWN count mismatch")
    if arm == "A":
        policy_expected = ranked[:BUDGET]
    else:
        reserved = [k for k in ranked if rebuilt[k][0]["decision"]["state"] == "UNKNOWN"][:RESERVE]
        policy_expected = (reserved + [k for k in ranked if k not in reserved])[:BUDGET]
    if selected != policy_expected:
        raise Invalid("recorded selection contradicts advertised policy")
    return rebuilt


COUNT_KEYS = (
    "slots", "reviewed", "reviewed_old_unknown", "value_correct", "gate_exact", "joint",
    "eligible_correct", "false_eligible", "candidate_blocked_on_ideal_target", "missed_review_eligibility",
    "value_correct_without_joint", "role_mismatch_block",
    "system_failure", "old_system_failure",
    "recover_unknown_total", "recovered_unknown", "newly_recovered_unknown",
    "stay_unknown_total", "retained_unknown", "retained_unknown_state",
    "stable_known_total", "previously_joint_stable_known", "stable_known_regression",
    "update_known_total", "updated_known", "missed_update_known",
    "reopen_known_total", "reopened_known",
)


def score(output_a: dict, output_b: dict, gold: dict) -> dict:
    """Join external gold only after simulation; no tuning or selecting here."""
    indexed = {"A": _load_output(output_a, "A"), "B": _load_output(output_b, "B")}
    expected_families = _gold_rows(gold)
    if any(side.keys() != expected_families.keys() for side in indexed.values()):
        raise Invalid("run and gold family IDs differ")
    family_scores = []
    aggregates = {arm: collections.Counter({key: 0 for key in COUNT_KEYS}) for arm in ARMS}
    directions = collections.Counter({"B_higher": 0, "tie": 0, "A_higher": 0, "N/A": 0})
    for name, expected in sorted(expected_families.items()):
        by_arm = {arm: _observed_rows(indexed[arm][name], arm, expected) for arm in ARMS}
        if indexed["A"][name]["ranked"] != indexed["B"][name]["ranked"]:
            raise Invalid("arms do not share the same declared priority order")
        if any(by_arm["A"][k][0] != by_arm["B"][k][0] for k in expected):
            raise Invalid("arms do not share the same historical state rechecked on new snapshot")
        selected_both = set(indexed["A"][name]["selected"]) & set(indexed["B"][name]["selected"])
        if any(by_arm["A"][k][1] != by_arm["B"][k][1] for k in selected_both):
            raise Invalid("same reviewed slot does not share reviewer outcome")
        by_fields, arm_counts = {}, {}
        for arm in ARMS:
            counts = collections.Counter({key: 0 for key in COUNT_KEYS})
            counts["reviewed"] = BUDGET
            counts["reviewed_old_unknown"] = indexed[arm][name]["selected_old_unknown"]
            selected = set(indexed[arm][name]["selected"])
            for k, (transition, want, want_gate) in sorted(expected.items()):
                old, final = by_arm[arm][k]
                value, gate, joint = _match(final, want, want_gate)
                _, _, old_joint = _match(old, want, want_gate)
                actual_gate = final["gate"]["status"]
                old_status = old["gate"]["status"]
                old_expected = "UNKNOWN" if transition in {"recover_unknown", "stay_unknown"} else "KNOWN"
                if old["decision"]["state"] != old_expected:
                    raise Invalid("gold transition contradicts frozen old state")
                counts["slots"] += 1
                counts["value_correct"] += value
                counts["gate_exact"] += gate
                counts["joint"] += joint
                counts["eligible_correct"] += actual_gate == "ELIGIBLE" and joint
                counts["false_eligible"] += actual_gate == "ELIGIBLE" and not joint
                counts["candidate_blocked_on_ideal_target"] += (
                    actual_gate == "BLOCKED" and want_gate["status"] != "BLOCKED")
                counts["value_correct_without_joint"] += value and not joint
                counts["role_mismatch_block"] += final["gate"]["reason"] == "EVIDENCE_ROLE_MISMATCH"
                counts["missed_review_eligibility"] += want_gate["status"] == "ELIGIBLE" and actual_gate != "ELIGIBLE"
                counts["system_failure"] += actual_gate == "SYSTEM_FAILURE"
                counts["old_system_failure"] += old_status == "SYSTEM_FAILURE"
                counts[transition + "_total"] += 1
                if transition == "recover_unknown":
                    counts["recovered_unknown"] += joint
                    counts["newly_recovered_unknown"] += not old_joint and joint
                elif transition == "stay_unknown":
                    counts["retained_unknown"] += joint
                    counts["retained_unknown_state"] += final["decision"]["state"] == "UNKNOWN"
                elif transition == "stable_known":
                    counts["previously_joint_stable_known"] += old_joint
                    counts["stable_known_regression"] += old_joint and not joint
                elif transition == "update_known":
                    counts["updated_known"] += joint
                    counts["missed_update_known"] += not joint
                elif transition == "reopen_known":
                    counts["reopened_known"] += joint
                by_fields.setdefault(k, {"id": k, "transition": transition, "expected": want,
                                         "expected_gate": want_gate, "old_joint": old_joint,
                                         "old": old})
                by_fields[k][arm] = {"selected": k in selected, "final": final,
                                     "value_correct": value, "gate_exact": gate, "joint": joint}
            arm_counts[arm] = dict(counts)
            aggregates[arm].update(counts)
        delta = {k: arm_counts["B"][k] - arm_counts["A"][k] for k in COUNT_KEYS}
        paired = collections.Counter({"A_only": 0, "B_only": 0, "both": 0, "neither": 0})
        for item in by_fields.values():
            if item["transition"] == "recover_unknown":
                got_a, got_b = item["A"]["joint"], item["B"]["joint"]
                paired["both" if got_a and got_b else "A_only" if got_a else "B_only" if got_b else "neither"] += 1
        rec_total = arm_counts["A"]["recover_unknown_total"]
        d_recovery = delta["recovered_unknown"]
        direction = ("N/A" if rec_total == 0 else "B_higher" if d_recovery > 0
                     else "A_higher" if d_recovery < 0 else "tie")
        directions[direction] += 1
        selected_a = set(indexed["A"][name]["selected"])
        selected_b = set(indexed["B"][name]["selected"])
        family_scores.append({"family": name, "A": arm_counts["A"], "B": arm_counts["B"],
                              "delta_B_minus_A": delta, "recovery_direction": direction,
                              "paired_recovery": {"denominator": rec_total, **dict(paired)},
                              "selection": {"both": sorted(selected_a & selected_b),
                                            "A_only": sorted(selected_a - selected_b),
                                            "B_only": sorted(selected_b - selected_a)},
                              "fields": list(by_fields.values())})
    return {"schema": "stage19-scored-v1", "n_families": len(family_scores),
            "recovery_direction_by_family": dict(directions),
            "gate_false_block_technical": {"status": "N/A", "reason": "NO_INDEPENDENT_ACTUAL_CANDIDATE_LABELS"},
            "total_fields_descriptive_only": {arm: dict(aggregates[arm]) for arm in ARMS},
            "families": family_scores}


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise Invalid("duplicate JSON member")
        out[key] = value
    return out


def _constant(value):
    raise Invalid("invalid non-JSON constant")


def _read(path: Path):
    with path.open("rb") as handle:
        data = handle.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise Invalid("input exceeds limit")
    return json.loads(data.decode("utf-8", errors="strict"),
                      object_pairs_hook=_pairs, parse_constant=_constant)


def assert_vendored_gate():
    actual = hashlib.sha256(Path(__file__).with_name("evidence_gate.py").read_bytes()).hexdigest()
    if actual != STAGE18_SHA256:
        raise Invalid("vendored gate differs from frozen Stage18 source")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--arm", required=True, choices=ARMS)
    scoring = sub.add_parser("score")
    scoring.add_argument("--observed-a", required=True, type=Path)
    scoring.add_argument("--observed-b", required=True, type=Path)
    scoring.add_argument("--gold", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            assert_vendored_gate()
            result = run_all(_read(args.input), args.arm)
        else:
            result = score(_read(args.observed_a), _read(args.observed_b), _read(args.gold))
    except (Invalid, OSError, ValueError, RecursionError):
        print("stage19: invalid or inconsistent frozen inputs", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, sort_keys=True,
                                        indent=2, allow_nan=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
