"""Score saved isolated outputs; does not call AI or the network."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT/"frozen/gold.json").read_text())
CHECKS = json.loads((ROOT/"frozen/checks.json").read_text())
ARMS = ("front","end")
METHODS = ("one","batch","strong")
GROUPS = {"public_amendment":[k for k in GOLD if k.startswith("q_")],
          "missing_body":[k for k in GOLD if k.startswith("m_")],
          "complete_other_lot":[k for k in GOLD if k.startswith("n_")],
          "speaker":[k for k in GOLD if k.startswith("y_")]}

def unique(pairs):
    result = {}
    for k,v in pairs:
        if k in result: raise ValueError(f"Duplicate {k}")
        result[k]=v
    return result

def load(path):
    a = json.loads(path.read_text(),object_pairs_hook=unique)
    if set(a)!=set(GOLD): raise ValueError(f"wrong keys for {path.name}")
    for k, v in a.items():
        if not (isinstance(v,list) and len(v)==2 and type(v[0]) is str and
                isinstance(v[1], list) and len(v[1])<=2 and all(type(x) is str for x in v[1]) and
                len(v[1])==len(set(v[1]))): raise ValueError(f"malformed {k}")
    return a

def apply(answer, offered):
    """Code checks only a supplied field bundle, not tender compliance."""
    sub=[]
    for k,v in offered.items():
        rule=answer[k][0]
        sub.append(None if rule=="UNKNOWN" or v is None else rule==v)
    return "fail" if False in sub else "unknown" if None in sub else "pass"

def score(a):
    truth={k:a[k][0]==truth for k,(truth,_e) in GOLD.items()}
    joint={k:truth[k] and any(set(a[k][1])==set(option) for option in opts)
           for k,(_v,opts) in GOLD.items()}
    # Post-hoc sensitivity, not the primary metric: permit surplus genuine segment IDs
    # when at least an entire preregistered citing set is present.
    known_sources = {"Q0","Q4","Q6","Q9","QA","M0","M5","M9","N0","N4","N6","N9","Y1"}
    relaxed={k:truth[k] and set(a[k][1]) <= known_sources and
             any(set(option) <= set(a[k][1]) for option in opts)
             for k,(_v,opts) in GOLD.items()}
    cases={c["id"]:apply(a,c["fields"]) for c in CHECKS}
    unexpected={c["id"] for c in CHECKS if cases[c["id"]]!=c["expected"]}
    return {"value":sum(truth.values()), "joint":sum(joint.values()), "posthoc_relaxed_joint":sum(relaxed.values()),
            "wrong_values":[k for k in GOLD if not truth[k]],
            "non_gold_evidence":[k for k,v in joint.items() if not v and truth[k]],
            "group_joint":{group:sum(joint[k] for k in keys) for group,keys in GROUPS.items()},
            "unresolved_as_concrete":[k for k, (v, _) in GOLD.items() if v=="UNKNOWN" and a[k][0]!="UNKNOWN"],
            "check_score":len(CHECKS)-len(unexpected),
            "false_positive_checks":[c["id"] for c in CHECKS if c["expected"]!="pass" and cases[c["id"]]=="pass"],
            "unexpected_checks":sorted(unexpected), "check_outcomes":cases,
            "missing_known_revision":a["m_missing_locator"][0]!="J8",
            "false_missing_when_complete":a["n_missing_locator"][0] in ("N6","N9")}

def generate():
    result={}
    for arm in ARMS:
        for method in METHODS:
            key=f"{arm}-{method}"
            last=load(ROOT/"observed"/f"{key}.json")
            result[key]={"final":score(last)}
            if method!="one":
                draft=load(ROOT/"observed"/f"{key}-draft.json")
                result[key].update(draft=score(draft),
                                   revised_value=[k for k in GOLD if draft[k][0]!=last[k][0]],
                                   revised_clauses=[k for k in GOLD if draft[k]!=last[k]])
    return result

if __name__=="__main__":
    print(json.dumps(generate(),ensure_ascii=False,indent=2))
