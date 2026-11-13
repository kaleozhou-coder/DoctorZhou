"""Deterministic retrospective workload audit. No model/human timing inference."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('ir_only', 'gate_v2_ir', 'receipt_ir')
STATES = {'close_eligible', 'needs_review', 'needs_evidence'}
INPUTS = ['benchmark/joint-review-v1/probes.json',
          'results/stage-07/first-run/simulated-receipts.json'] + [
          f'results/stage-07/first-run/{arm}.predictions.json' for arm in ARMS]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def verify(root):
    manifest = json.loads((root/'experiments/stage-08/input-freeze.json').read_text())
    if set(manifest) != set(INPUTS):
        raise ValueError('Input manifest scope changed')
    for rel, expected in manifest.items():
        if hashlib.sha256((root/rel).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input changed: ' + rel)


def ledger(pack, receipts, predictions):
    probes = pack['probes']
    ids = [p['probe_id'] for p in probes]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Empty or duplicate probe IDs')
    if [p['input']['case_id'] for p in probes] != ids:
        raise ValueError('Case identity mismatch')
    if [r['probe_id'] for r in receipts] != ids:
        raise ValueError('Receipt identity or order mismatch')
    if set(predictions) != set(ARMS):
        raise ValueError('Missing or extra arms')
    rows = []
    for arm in ARMS:
        preds = predictions[arm]
        if [r['case_id'] for r in preds] != ids:
            raise ValueError('Prediction identity or order mismatch')
        for probe, item, pred in zip(probes, receipts, preds):
            state = pred['decision']
            if state not in STATES or pred.get('payment_authorized') is not False:
                raise ValueError('Unknown decision or payment authorization')
            if arm == 'receipt_ir' and type(pred.get('input_contract', {}).get('review_assertion_accepted')) is not bool:
                raise ValueError('Receipt acceptance must be boolean')
            receipt = item['receipt']
            paths = [] if receipt is None else receipt['reviewed_paths']
            if not isinstance(paths, list) or any(not isinstance(x, str) or not x for x in paths) or len(set(paths)) != len(paths):
                raise ValueError('Invalid receipt path list')
            if receipt is not None and receipt.get('review_id') != 'SIM-' + probe['probe_id']:
                raise ValueError('Unbound simulated receipt')
            failure = probe['metric_stratum'] == 'trusted_reviewer_failure'
            rows.append(dict(arm=arm, probe_id=probe['probe_id'], stratum=probe['metric_stratum'],
                decision=state, receipt_accepted=(pred.get('input_contract', {}).get('review_assertion_accepted') if arm == 'receipt_ir' else None),
                semantic_safety_label=('known_trusted_failure_control' if failure else 'not_independently_labeled'), receipt_units=int(arm == 'receipt_ir' and receipt is not None),
                declared_path_units=len(paths) if arm == 'receipt_ir' else 0,
                downstream_review_units=int(state == 'needs_review'),
                evidence_request_units=int(state == 'needs_evidence'),
                closed=int(state == 'close_eligible'),
                trusted_failure_control=failure,
                known_trust_control_false_close=int(failure and state == 'close_eligible')))
    return rows


def aggregate(rows):
    keys = ('receipt_units', 'declared_path_units', 'downstream_review_units',
            'evidence_request_units', 'closed', 'known_trust_control_false_close')
    return dict(n=len(rows), **{key:sum(row[key] for row in rows) for key in keys})


def cost(counts, ratio, mode='receipt_units', evidence_ratio=Fraction(1)):
    if any(isinstance(v, bool) or not isinstance(v, (int, Fraction)) for v in (ratio, evidence_ratio)):
        raise ValueError('Cost ratios must be exact integers or fractions')
    if mode not in ('receipt_units', 'declared_path_units'):
        raise ValueError('Choose one upstream model, never add both')
    if ratio < 0 or evidence_ratio < 0:
        raise ValueError('Negative cost')
    return counts[mode]*ratio + counts['downstream_review_units'] + counts['evidence_request_units']*evidence_ratio


def summarize(rows):
    result = {}
    for name, selected in [('all_28_including_failure_controls', rows),
        ('26_excluding_trusted_failure_controls', [r for r in rows if not r['trusted_failure_control']])]:
        arms = {arm:aggregate([r for r in selected if r['arm'] == arm]) for arm in ARMS}
        baseline, proposed = arms['gate_v2_ir'], arms['receipt_ir']
        if baseline['evidence_request_units'] != proposed['evidence_request_units']:
            raise ValueError('Evidence cost no longer cancels')
        saving = baseline['downstream_review_units']-proposed['downstream_review_units']
        sensitivity = []
        for mode in ('receipt_units', 'declared_path_units'):
            for ratio in map(Fraction, ('0', '1/4', '1/3', '1/2', '1')):
                costs = {arm:str(cost(counts, ratio, mode)) for arm,counts in arms.items()}
                sensitivity.append(dict(upstream_mode=mode, upstream_cost_ratio=str(ratio),
                    normalized_cost=costs,
                    receipt_minus_gate=str(Fraction(costs['receipt_ir'])-Fraction(costs['gate_v2_ir']))))
        result[name] = dict(arms=arms, downstream_review_units_saved=saving,
            receipt_break_even_ratio=str(Fraction(saving,proposed['receipt_units'])),
            path_break_even_ratio=str(Fraction(saving,proposed['declared_path_units'])),
            sensitivity=sensitivity)
    return dict(study='stage08-retrospective-workload-audit-v1',
        actual_human_reviews=0, actual_human_seconds=None, actual_model_runs=0,
        measured_cost_currency=None,
        warning='Counts are synthetic workload requirements, not observed human labor. Costs are assumptions. Known trust failures remain visible.',
        scopes=result)


def run(output, root=ROOT):
    verify(root)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty')
    read = lambda rel: json.loads((root/rel).read_text())
    rows = ledger(read(INPUTS[0]), read(INPUTS[1]), {a:read(f'results/stage-07/first-run/{a}.predictions.json') for a in ARMS})
    summary = summarize(rows)
    output.mkdir(parents=True, exist_ok=True)
    write(output/'ledger.json', rows)
    write(output/'summary.json', summary)
    return summary

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output), ensure_ascii=False, sort_keys=True))
