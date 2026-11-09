"""Run frozen synthetic stress probes; never load v1 evaluator artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
from policy_baseline import predict_case

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    freeze = json.loads((root / 'benchmark/stress-v1/FREEZE.json').read_text())
    for name, expected in freeze['files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen file changed: ' + name)
    return json.loads((root / 'benchmark/stress-v1/probes.json').read_text())


def evaluate(pack, predictor=predict_case, root=ROOT):
    policies = {f'F{i:02}': json.loads((root / f'benchmark/v1/model-facing/F{i:02}/materials.json').read_text()) for i in range(1, 7)}
    rows = []
    for p in pack['probes']:
        try:
            result = predictor(p['case'], policies[p['case']['family_id']])
            e = p['expected']
            if p['scope'] == 'in_policy':
                passed = result['decision'] == e['decision'] and result['reason_codes'] == [e['reason']]
            else:
                passed = result['decision'] in e['allowed_decisions']
            passed = passed and result.get('payment_authorized') is False
            rows.append(dict(probe_id=p['probe_id'], scope=p['scope'], passed=passed, prediction=result))
        except Exception as exc:
            rows.append(dict(probe_id=p['probe_id'], scope=p['scope'], passed=False, exception=type(exc).__name__ + ': ' + str(exc)))
    by_id = {r['probe_id']: r for r in rows}
    relations = []
    for rel in pack['metamorphic_relations']:
        a, b = (by_id[rel[k]].get('prediction') for k in ('a', 'b'))
        passed = False
        if a is not None and b is not None:
            passed = ((a['decision'], a['reason_codes']) == (b['decision'], b['reason_codes']) if rel['relation'] == 'same_outcome' else a['decision'] != b['decision'])
        relations.append(dict(id=rel['id'], passed=passed))
    summary = {}
    for scope in ('in_policy', 'ood_safety'):
        selected = [r for r in rows if r['scope'] == scope]
        summary[scope] = dict(total=len(selected), passed=sum(r['passed'] for r in selected), failed_ids=[r['probe_id'] for r in selected if not r['passed']], exceptions=sum('exception' in r for r in selected))
    summary['metamorphic'] = dict(total=len(relations), passed=sum(r['passed'] for r in relations))
    return dict(synthetic=True,not_expert_gold=True,summary=summary,results=rows,metamorphic=relations)


def unsafe_control(case, materials):
    return dict(case_id=case['case_id'], decision='close_eligible', reason_codes=['criteria_met'], payment_authorized=False)


def run(output, root=ROOT):
    pack = verify(root)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be absent or empty')
    output.mkdir(parents=True, exist_ok=True)
    reports = {'frozen-baseline': evaluate(pack, root=root), 'always-close-control': evaluate(pack, unsafe_control, root)}
    for name, report in reports.items():
        (output / (name + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return {name: r['summary'] for name, r in reports.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
