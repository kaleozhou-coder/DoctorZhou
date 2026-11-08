"""Deterministic semantic mutation pilot, NOT an LLM effectiveness experiment.
Only Python standard library. All cases are authored synthetic fixtures.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'ontology' / 'reference_model.json'
CASES = ROOT / 'data' / 'synthetic' / 'acceptance_cases.json'


def decide(case: dict, features: dict) -> dict:
    """Apply the synthetic P0 policy. No real approval/payment is performed."""
    line = case['invoice_line']
    records = case.get('records', [])
    if not line.get('order_line_id'):
        return {'decision': 'needs_review', 'reason': 'ambiguous_order_link', 'evidence': []}
    invoice_quantity = line.get('quantity')
    if isinstance(invoice_quantity, bool) or not isinstance(invoice_quantity, (int, float)) or not math.isfinite(invoice_quantity) or invoice_quantity <= 0:
        return {'decision': 'needs_review', 'reason': 'unsupported_invoice_quantity', 'evidence': []}
    accepted = []
    relevant = []
    seen = set()
    for record in records:
        if features['order_line_identity'] and record.get('order_line_id') != line['order_line_id']:
            continue
        if record.get('type') != 'AcceptanceRecord' and not (
            features.get('accept_delivery_as_acceptance', False) and record.get('type') == 'DeliveryRecord'
        ):
            continue
        relevant.append(record)
        if features['revocation']:
            if record.get('revoked') is True:
                continue
            if record.get('revoked') is not False:
                return {'decision': 'needs_review', 'reason': 'unverified_revocation_status', 'evidence': []}
        if features['unique_evidence_id']:
            if not record.get('id') or record['id'] in seen:
                return {'decision': 'needs_review', 'reason': 'missing_or_duplicate_evidence_id', 'evidence': []}
            seen.add(record['id'])
        if features['policy_version'] and record.get('policy_version') != case['policy_version']:
            return {'decision': 'needs_review', 'reason': 'unresolved_policy_version', 'evidence': []}
        if features['authorization'] and record.get('authorized') is not True:
            return {'decision': 'needs_review', 'reason': 'unverified_acceptor', 'evidence': []}
        if features['status']:
            if record.get('status') in ('rejected', 'conflicting'):
                return {'decision': 'needs_review', 'reason': 'adverse_or_conflicting_acceptance', 'evidence': []}
            if record.get('status') != 'accepted':
                continue
        if features['unit_identity'] and record.get('unit') != line['unit']:
            return {'decision': 'needs_review', 'reason': 'unresolved_unit_identity', 'evidence': []}
        if features['provenance'] and (not record.get('source_id') or not record.get('source_locator')):
            return {'decision': 'needs_review', 'reason': 'missing_evidence_locator', 'evidence': []}
        accepted_quantity = record.get('quantity')
        if isinstance(accepted_quantity, bool) or not isinstance(accepted_quantity, (int, float)) or not math.isfinite(accepted_quantity) or accepted_quantity <= 0:
            return {'decision': 'needs_review', 'reason': 'unsupported_acceptance_quantity', 'evidence': []}
        accepted.append(record)
    if not accepted:
        return {'decision': 'needs_evidence', 'reason': 'no_usable_acceptance_record', 'evidence': []}
    quantity = sum(r['quantity'] for r in accepted)
    if not math.isfinite(quantity):
        return {'decision': 'needs_review', 'reason': 'invalid_aggregate_quantity', 'evidence': []}
    if features['quantity_coverage'] and quantity < line['quantity']:
        return {'decision': 'needs_evidence', 'reason': 'accepted_quantity_insufficient', 'evidence': [r['id'] for r in accepted]}
    return {'decision': 'close_eligible', 'reason': 'synthetic_policy_evidence_complete', 'evidence': [r['id'] for r in accepted]}


def score(cases: list, features: dict) -> dict:
    predictions = [{'case_id': c['id'], 'expected': c['expected'], **decide(c, features)} for c in cases]
    unsafe = sum(p['decision'] == 'close_eligible' and p['expected'] != 'close_eligible' for p in predictions)
    negative_n = sum(c['expected'] != 'close_eligible' for c in cases)
    return {
        'n': len(cases),
        'exact_decision_accuracy': sum(p['decision'] == p['expected'] for p in predictions) / len(cases),
        'unsafe_close_count': unsafe,
        'unsafe_close_rate_among_negative_cases': unsafe / negative_n if negative_n else None,
        'negative_case_n': negative_n,
        'predictions': predictions,
    }


def run() -> dict:
    cases = json.loads(CASES.read_text())['cases']
    model = json.loads(MODEL.read_text())
    baseline = model['semantic_features']
    variants = {'reference': baseline}
    for key in baseline:
        if key == 'accept_delivery_as_acceptance':
            continue
        f = copy.deepcopy(baseline)
        f[key] = False
        variants[f'without_{key}'] = f
    f = copy.deepcopy(baseline)
    f['accept_delivery_as_acceptance'] = True
    variants['delivery_equals_acceptance'] = f
    results = {name: score(cases, features) for name, features in variants.items()}
    report = {
        'experiment_type': 'deterministic_semantic_mutation_test',
        'claims_not_supported': ['LLM method superiority', 'human review savings', 'real-world accuracy', 'payment readiness'],
        'data_type': 'authored_synthetic_fixtures',
        'python': platform.python_version(),
        'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [MODEL, CASES, Path(__file__)]},
        'variants': results,
        'mutation_detection': {
            'mutants': len(results) - 1,
            'killed': sum(any(p['decision'] != r['decision'] for p, r in zip(result['predictions'], results['reference']['predictions'])) for name, result in results.items() if name != 'reference'),
        },
    }
    dest = ROOT / 'results' / 'semantic_pilot.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'variants'}, ensure_ascii=False, indent=2))
    for name, result in results.items():
        print(f"{name}: accuracy={result['exact_decision_accuracy']:.3f}, unsafe_close={result['unsafe_close_count']}/{result['negative_case_n']}")
    return report

if __name__ == '__main__':
    run()
