"""Joint F01/F05 experiment. Simulated trusted reviews, not AI or humans."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import input_contract_v2 as gate_v2
import review_receipt_gate as receipts
import rule_ir_v3
from run_stage05 import verify_manifest, write

ROOT = Path(__file__).resolve().parents[1]
AS_OF = '2026-11-12T12:00:00Z'
REASONS = {'unverified_text':'review_receipt_missing', 'review_conflict':'review_receipt_contradictory',
           'review_coverage_missing':'review_receipt_incomplete', 'review_case_mismatch':'review_receipt_case_mismatch',
           'review_materials_mismatch':'review_receipt_materials_mismatch'}


def simulated_receipt(probe, materials):
    """Explicit fixture adapter; NOT an automatic production verifier."""
    s = probe['external_review_scenario']
    if s['kind'] == 'none':
        return None
    case_binding = copy.deepcopy(probe['input'])
    materials_binding = copy.deepcopy(materials)
    if s['kind'] == 'stale_case':
        case_binding['case_id'] += '-earlier'
    if s['kind'] == 'stale_materials':
        materials_binding['stage07_simulated_version'] = 'earlier'
    return {'version':receipts.VERSION, 'review_id':'SIM-' + probe['probe_id'],
            'reviewer_id':'SYNTHETIC-NOT-A-PERSON', 'scope':receipts.SCOPE,
            'case_sha256':receipts.canonical_sha256(case_binding),
            'materials_sha256':receipts.canonical_sha256(materials_binding),
            'reviewed_paths':s['covered_paths'],
            'outcome':'contradictory' if s['kind'] == 'conflict' else 'consistent',
            'reviewed_at':'2026-11-12T11:00:00Z', 'expires_at':'2026-11-13T11:00:00Z'}


def sorted_refs(refs):
    return sorted((r['source_id'], r['locator']) for r in refs)


def evaluate(predictions, pack, arm):
    # Predictions have all been written before this function is called.
    items, groups = [], {}
    for p, result in zip(pack['probes'], predictions):
        e = p['expected']
        reason = e['policy_reason_code'] if e['reason_semantic'] == 'policy' else REASONS[e['reason_semantic']]
        contract = result.get('input_contract', {})
        checks = {'decision':result.get('decision') == e['decision'],
                  'primary_reason':result.get('reason_codes') == [reason],
                  'source_refs':sorted_refs(result.get('source_refs', [])) == sorted_refs(e['structured_policy_source_refs']),
                  'payment_authorized':result.get('payment_authorized') is False,
                  'text_paths':contract.get('unverified_text_paths', []) == e['text_paths']}
        # For the two controls without a text channel, contract status stays validated.
        checks['contract_status'] = contract.get('status') == ('abstained' if e['reason_semantic'] != 'policy' else 'validated')
        if arm == 'ir_only':
            checks['contract_status'] = False  # No contract layer; never silently give it metadata credit.
        if 'semantic_safe_decision' in e:
            semantic_ok = result.get('decision') == e['semantic_safe_decision']
        else:
            semantic_ok = None
        row = {'probe_id':p['probe_id'], 'stratum':p['metric_stratum'], 'checks':checks,
               'all_expected_fields_match':all(checks.values()), 'decision':result.get('decision'),
               'semantic_safe_decision_match':semantic_ok}
        items.append(row)
        g = groups.setdefault(p['metric_stratum'], {'n':0,'closed':0,'needs_review':0,'needs_evidence':0,'all_expected_fields_match':0})
        g['n'] += 1; g['closed'] += result.get('decision') == 'close_eligible'
        g['needs_review'] += result.get('decision') == 'needs_review'
        g['needs_evidence'] += result.get('decision') == 'needs_evidence'
        g['all_expected_fields_match'] += all(checks.values())
    return {'arm':arm, 'scope':['F01','F05'], 'groups':groups, 'items':items,
            'warning':'Expected fields describe receipt protocol, not an equal oracle for other arms. Negative controls scored separately.'}


def run(output, root=ROOT):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty; preserve first results')
    verify_manifest(root, root/'experiments/stage-07/implementation-freeze.json')
    pack = json.loads((root/'benchmark/joint-review-v1/probes.json').read_text())
    materials = {f:json.loads((root/f'benchmark/v1/model-facing/{f}/materials.json').read_text()) for f in ('F01','F05')}
    artifacts = {f:rule_ir_v3.loads((root/f'ontology/ir-reference-v3/{f}.json').read_text()) for f in ('F01','F05')}
    def predict(case, material):
        return rule_ir_v3.predict_case(case, artifacts[case['family_id']], material)
    arms = {k:[] for k in ('ir_only', 'gate_v2_ir', 'receipt_ir')}
    review_inputs = []
    for p in pack['probes']:
        case = p['input']; material = materials[case['family_id']]
        receipt = simulated_receipt(p, material)
        review_inputs.append({'probe_id':p['probe_id'],'receipt':receipt})
        arms['ir_only'].append(predict(copy.deepcopy(case), material))
        arms['gate_v2_ir'].append(gate_v2.apply_contract(copy.deepcopy(case), material, predict))
        arms['receipt_ir'].append(receipts.apply_contract(copy.deepcopy(case), material, predict, trusted_receipt=receipt, as_of=AS_OF))
    write(output/'simulated-receipts.json',review_inputs)
    for name, predictions in arms.items():
        write(output/(name+'.predictions.json'), predictions)
    reports = {}
    for name, predictions in arms.items():
        reports[name] = evaluate(predictions, pack, name)
        write(output/(name+'.report.json'),reports[name])
    write(output/'summary.json', {'arms':{k:v['groups'] for k,v in reports.items()},
         'simulated_receipt_count':sum(x['receipt'] is not None for x in review_inputs),
         'simulated_reviewed_paths':sum(len(x['receipt']['reviewed_paths']) for x in review_inputs if x['receipt']),
         'actual_human_reviews':0, 'actual_model_runs':0,'paid_calls':0,
         'timing':'No human minutes measured; path count is workload proxy only',
         'as_of':AS_OF})
    return reports


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
