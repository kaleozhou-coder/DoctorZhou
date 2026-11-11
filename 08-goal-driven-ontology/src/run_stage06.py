"""Stage-06 versioned safety repair and abstention-cost audit. No model calls."""
import argparse
import json
from pathlib import Path
import policy_baseline
import input_contract
import input_contract_v2
import rule_ir_v2
import rule_ir_v3
from benchmark_eval import verify_freeze
from run_stage05 import sha, write, verify_manifest, guarded_call, summarize_labels, summarize_probes

ROOT = Path(__file__).resolve().parents[1]


def adapt_prose(pack):
    """Adapt independently frozen author format without changing any oracle."""
    scopes = {'normal_close_control': 'in_policy', 'policy_nonclosure_control': 'in_policy',
              'benign_abstention_cost': 'unsupported_benign', 'safety_nonclosure': 'ood_safety'}
    probes = []
    for p in pack['probes']:
        probes.append({'probe_id': p['probe_id'], 'metric_stratum': p['metric_stratum'],
                       'scope': scopes[p['metric_stratum']], 'case': p['input'],
                       'expected': {'decision': p['expected']['decision'],
                                    'reason': p['expected']['reason_code']}})
    return {'probes': probes}


def prose_strata(predictions, pack):
    result = {}
    for stratum in sorted({p['metric_stratum'] for p in pack['probes']}):
        probes = [p for p in pack['probes'] if p['metric_stratum'] == stratum]
        ids = {p['case']['case_id'] for p in probes}
        selected = [p for p in predictions if p['case_id'] in ids]
        result[stratum] = summarize_probes(selected, {'probes': probes})['summary'][probes[0]['scope']]
    return result


def run(output, root=ROOT):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty; preserve first results')
    frozen = verify_manifest(root, root / 'experiments/stage-06/implementation-freeze.json')
    required = {'src/run_stage06.py', 'src/input_contract.py', 'src/input_contract_v2.py',
                'src/rule_ir_v2.py', 'src/rule_ir_v3.py', 'src/run_stage05.py',
                'ontology/ir-reference-v3/F01.json', 'ontology/ir-reference-v3/F05.json',
                'benchmark/prose-channel-v1/probes.json'}
    if not required <= frozen.keys():
        raise ValueError('Freeze does not cover evaluated implementations/data')
    verify_manifest(root, root / 'benchmark/stress-v1/FREEZE.json')
    verify_manifest(root, root / 'benchmark/entry-challenge-v1/FREEZE.json')
    verify_manifest(root, root / 'ontology/ir-reference-v2/freeze.json')
    verify_manifest(root, root / 'benchmark/prose-channel-v1/FREEZE.json')
    verify_freeze(root / 'benchmark/v1')  # Integrity bytes only, before label parsing.
    materials = {f'F{i:02}': json.loads((root / f'benchmark/v1/model-facing/F{i:02}/materials.json').read_text())
                 for i in range(1, 7)}
    artifacts = {f: rule_ir_v3.loads((root / f'ontology/ir-reference-v3/{f}.json').read_text())
                 for f in ('F01', 'F05')}
    old_artifacts = {f: rule_ir_v2.loads((root / f'ontology/ir-reference-v2/{f}.json').read_text())
                     for f in artifacts}
    def ir_old(case, material):
        return rule_ir_v2.predict_case(case, old_artifacts[case['family_id']], material)
    def ir_new(case, material):
        return rule_ir_v3.predict_case(case, artifacts[case['family_id']], material)
    def gated_ir(case, material):
        return input_contract_v2.apply_contract(case, material, ir_new)
    predictors = {'baseline': policy_baseline.predict_case,
                  'gate_v1': input_contract.predict_case, 'gate_v2': input_contract_v2.predict_case,
                  'ir_v2': ir_old, 'ir_v3': ir_new, 'gated_ir_v3': gated_ir}
    cases = []
    for f in materials:
        cases.extend(json.loads((root / f'benchmark/v1/evaluator/inputs/{f}.json').read_text())['cases'])
    packs = {'stress': json.loads((root / 'benchmark/stress-v1/probes.json').read_text()),
             'challenge': json.loads((root / 'benchmark/entry-challenge-v1/probes.json').read_text())}
    prose = json.loads((root / 'benchmark/prose-channel-v1/probes.json').read_text())
    packs['prose'] = adapt_prose(prose)
    suites = {'legacy': cases, **{name: [p['case'] for p in pack['probes']] for name, pack in packs.items()}}
    output.mkdir(parents=True, exist_ok=True)
    all_predictions = {}
    for name, predictor in predictors.items():
        for suite, available in suites.items():
            selected = [c for c in available if name in ('baseline', 'gate_v1', 'gate_v2') or c['family_id'] in artifacts]
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
               'freeze_sha256': sha(root / 'experiments/stage-06/implementation-freeze.json'), 'audits': {}}
    for key, obj in all_predictions.items():
        name, suite = key.split('.')
        if suite == 'legacy':
            report = summarize_labels(obj['predictions'], labels)
        else:
            selected_ids = {p['case_id'] for p in obj['predictions']}
            pack = dict(packs[suite], probes=[p for p in packs[suite]['probes'] if p['case']['case_id'] in selected_ids])
            report = summarize_probes(obj['predictions'], pack)
            if suite == 'prose':
                report['by_stratum'] = prose_strata(obj['predictions'], pack)
        report.update({k: obj[k] for k in ('total_available_cases', 'executed_cases', 'unsupported_not_executed')})
        report['predictions_sha256'] = sha(output / (key + '.predictions.json'))
        write(output / (key + '.report.json'), report)
        summary['audits'][key] = {k: report[k] for k in ('summary', 'total_available_cases', 'executed_cases', 'unsupported_not_executed')}
        if 'by_stratum' in report:
            summary['audits'][key]['by_stratum'] = report['by_stratum']
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
