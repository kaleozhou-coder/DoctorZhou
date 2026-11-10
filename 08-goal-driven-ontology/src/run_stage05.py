"""Retrospective entry-contract and common-IR engineering audit, not an LLM run."""
import argparse
import hashlib
import json
from pathlib import Path

import policy_baseline
import input_contract
import rule_ir_v2
from benchmark_eval import verify_freeze

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n')


def verify_manifest(root, path):
    manifest = json.loads(path.read_text())
    files = manifest.get('sha256', manifest.get('files', manifest.get('hashes')))
    if not isinstance(files, dict) or not files:
        raise ValueError('Freeze must contain nonempty sha256/files map')
    for name, expected in files.items():
        target = root / name
        if not target.resolve().is_relative_to(root.resolve()) or sha(target) != expected:
            raise ValueError('Frozen file changed: ' + name)
    return files


def guarded_call(predictor, case, materials):
    try:
        return predictor(case, materials)
    except Exception as exc:
        # Exceptions are retained in the full denominator, not converted to success.
        return {'case_id': case.get('case_id'), 'decision': None,
                'reason_codes': [], 'payment_authorized': False,
                'execution_exception': type(exc).__name__}


def summarize_labels(predictions, labels):
    by_id = {r['case_id']: r for r in labels}
    if len(by_id) != len(labels) or len({p['case_id'] for p in predictions}) != len(predictions):
        raise ValueError('Duplicate case ID')
    rows = []
    for p in predictions:
        label = by_id[p['case_id']]
        expected = label['expected_decision']
        rows.append({'case_id': p['case_id'], 'family_id': label['family_id'],
                     'expected': expected, 'predicted': p['decision'],
                     'decision_correct': p['decision'] == expected,
                     'reason_correct': p['reason_codes'] == label['required_reason_codes'],
                     'unsafe_close': p['decision'] == 'close_eligible' and expected != 'close_eligible',
                     'positive': expected == 'close_eligible',
                     'close_recalled': p['decision'] == expected == 'close_eligible',
                     'exception': 'execution_exception' in p,
                     'payment_unauthorized': p.get('payment_authorized') is False})
    def total(selected):
        return {'n': len(selected), 'decision_correct': sum(x['decision_correct'] for x in selected),
                'reason_correct': sum(x['reason_correct'] for x in selected),
                'unsafe_close': sum(x['unsafe_close'] for x in selected),
                'negative_n': sum(not x['positive'] for x in selected),
                'positive_n': sum(x['positive'] for x in selected),
                'close_recalled': sum(x['close_recalled'] for x in selected),
                'exceptions': sum(x['exception'] for x in selected),
                'payment_unauthorized': sum(x['payment_unauthorized'] for x in selected)}
    return {'summary': total(rows), 'by_family': {f: total([x for x in rows if x['family_id'] == f])
             for f in sorted({x['family_id'] for x in rows})}, 'rows': rows}


def summarize_probes(predictions, pack):
    if len(predictions) != len(pack['probes']):
        raise ValueError('Probe count mismatch')
    rows = []
    for p, probe in zip(predictions, pack['probes']):
        scope, expected = probe['scope'], probe['expected']
        if p['case_id'] != probe['case']['case_id']:
            raise ValueError('Probe ID mismatch')
        exception = 'execution_exception' in p
        no_close = p['decision'] in ('needs_review', 'needs_evidence') and not exception
        exact = (p['decision'] == expected.get('decision') and p['reason_codes'] == [expected.get('reason')])
        # Benign unsupported inputs have no business-correctness label.
        passed = exact if scope == 'in_policy' else (no_close if scope == 'ood_safety' else None)
        if passed is not None:
            passed = passed and p.get('payment_authorized') is False and not exception
        rows.append({'probe_id': probe['probe_id'], 'scope': scope, 'passed': passed,
                     'decision': p['decision'], 'reason_codes': p['reason_codes'],
                     'conservative_nonclose': no_close, 'exception': exception,
                     'payment_unauthorized': p.get('payment_authorized') is False})
    groups = {}
    for scope in sorted({x['scope'] for x in rows}):
        selected = [x for x in rows if x['scope'] == scope]
        groups[scope] = {'n': len(selected),
                         'passed': None if scope == 'unsupported_benign' else sum(x['passed'] for x in selected),
                         'conservative_nonclose': sum(x['conservative_nonclose'] for x in selected),
                         'exceptions': sum(x['exception'] for x in selected),
                         'close_n': sum(x['decision'] == 'close_eligible' for x in selected),
                         'unexpected_n': sum(x['decision'] not in ('close_eligible', 'needs_review', 'needs_evidence') for x in selected),
                         'payment_unauthorized': sum(x['payment_unauthorized'] for x in selected),
                         'failed_ids': [x['probe_id'] for x in selected if x['passed'] is False]}
    return {'summary': groups, 'rows': rows}


def run(output, root=ROOT):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty; preserve first results')
    frozen = verify_manifest(root, root / 'experiments/stage-05/implementation-freeze.json')
    required = {'src/run_stage05.py', 'src/input_contract.py', 'src/rule_ir_v2.py',
                'ontology/ir-reference-v2/F01.json', 'ontology/ir-reference-v2/F05.json',
                'benchmark/entry-challenge-v1/probes.json'}
    if not required <= frozen.keys():
        raise ValueError('Freeze does not cover evaluated implementations/data')
    verify_manifest(root, root / 'benchmark/stress-v1/FREEZE.json')
    verify_manifest(root, root / 'benchmark/entry-challenge-v1/FREEZE.json')
    verify_manifest(root, root / 'ontology/ir-reference-v2/freeze.json')
    verify_freeze(root / 'benchmark/v1')  # Integrity bytes only, before label parsing.
    materials = {f'F{i:02}': json.loads((root / f'benchmark/v1/model-facing/F{i:02}/materials.json').read_text())
                 for i in range(1, 7)}
    artifacts = {f: rule_ir_v2.loads((root / f'ontology/ir-reference-v2/{f}.json').read_text())
                 for f in ('F01', 'F05')}
    def ir(case, material):
        return rule_ir_v2.predict_case(case, artifacts[case['family_id']], material)
    def gated_ir(case, material):
        return input_contract.apply_contract(case, material, ir)
    predictors = {'baseline': policy_baseline.predict_case, 'gated_baseline': input_contract.predict_case,
                  'ir_v2': ir, 'gated_ir_v2': gated_ir}
    cases = []
    for f in materials:
        cases.extend(json.loads((root / f'benchmark/v1/evaluator/inputs/{f}.json').read_text())['cases'])
    packs = {'stress': json.loads((root / 'benchmark/stress-v1/probes.json').read_text()),
             'challenge': json.loads((root / 'benchmark/entry-challenge-v1/probes.json').read_text())}
    suites = {'legacy': cases, **{name: [p['case'] for p in pack['probes']] for name, pack in packs.items()}}
    output.mkdir(parents=True, exist_ok=True)
    all_predictions = {}
    for name, predictor in predictors.items():
        for suite, available in suites.items():
            selected = [c for c in available if name in ('baseline', 'gated_baseline') or c['family_id'] in artifacts]
            predictions = [guarded_call(predictor, c, materials[c['family_id']]) for c in selected]
            key = name + '.' + suite
            obj = {'execution_kind': 'retrospective_manual_implementation_audit', 'model_calls': 0,
                   'total_available_cases': len(available), 'executed_cases': len(selected),
                   'unsupported_not_executed': len(available) - len(selected), 'predictions': predictions}
            write(output / (key + '.predictions.json'), obj)
            all_predictions[key] = obj
    # Persist ALL predictions for ALL implementations before semantic label access.
    labels = json.loads((root / 'benchmark/v1/evaluator/labels.json').read_text())['cases']
    summary = {'model_calls': 0, 'paid_calls': 0, 'synthetic': True, 'expert_gold': False,
               'freeze_sha256': sha(root / 'experiments/stage-05/implementation-freeze.json'), 'audits': {}}
    for key, obj in all_predictions.items():
        name, suite = key.split('.')
        if suite == 'legacy':
            report = summarize_labels(obj['predictions'], labels)
        else:
            selected_ids = {p['case_id'] for p in obj['predictions']}
            pack = dict(packs[suite], probes=[p for p in packs[suite]['probes'] if p['case']['case_id'] in selected_ids])
            report = summarize_probes(obj['predictions'], pack)
        report.update({k: obj[k] for k in ('total_available_cases', 'executed_cases', 'unsupported_not_executed')})
        report['predictions_sha256'] = sha(output / (key + '.predictions.json'))
        write(output / (key + '.report.json'), report)
        summary['audits'][key] = {k: report[k] for k in ('summary', 'total_available_cases', 'executed_cases', 'unsupported_not_executed')}
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
