"""Synthetic, deterministic temporal mechanism study. No learned models/API calls."""
import argparse
import hashlib
import json
from pathlib import Path

DEPENDENCIES = {
    'link': frozenset({'linked'}),
    'quantity': frozenset({'invoice_qty', 'accepted_qty'}),
    'acceptance': frozenset({'acceptance'}),
    'authority': frozenset({'authorized', 'require_authority'}),
}
FIELDS = frozenset().union(*DEPENDENCIES.values(), {'memo'})


def validate(state):
    if set(state) != FIELDS:
        raise ValueError('unexpected or missing fields')
    for key in ('linked', 'authorized'):
        if state[key] is not None and type(state[key]) is not bool:
            raise ValueError('boolean or null required')
    if type(state['require_authority']) is not bool:
        raise ValueError('policy authority flag must be boolean')
    for key in ('invoice_qty', 'accepted_qty'):
        value = state[key]
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError('nonnegative integer or null required')
    if state['invoice_qty'] == 0:
        raise ValueError('positive invoice scope only')
    if state['acceptance'] not in (None, 'accepted', 'rejected', 'revoked', 'conflict'):
        raise ValueError('unknown acceptance state')
    if type(state['memo']) is not str:
        raise ValueError('memo must be string')


def predicate(name, state):
    if name == 'link':
        return 'unknown' if state['linked'] is None else ('ok' if state['linked'] else 'adverse')
    if name == 'quantity':
        a, b = state['accepted_qty'], state['invoice_qty']
        return 'unknown' if a is None or b is None or a < b else 'ok'
    if name == 'acceptance':
        return 'unknown' if state['acceptance'] is None else ('ok' if state['acceptance'] == 'accepted' else 'adverse')
    if name == 'authority':
        if not state['require_authority']:
            return 'ok'
        return 'unknown' if state['authorized'] is None else ('ok' if state['authorized'] else 'adverse')
    raise ValueError('unknown predicate')


def aggregate(values):
    return 'review' if 'adverse' in values else ('needs_evidence' if 'unknown' in values else 'close')


class Method:
    """step receives only current evidence, never labels or future events."""
    def __init__(self, mode):
        if mode not in ('full', 'incremental', 'stale_negative_control'):
            raise ValueError('unknown mode')
        self.mode, self.previous, self.cache = mode, None, {}

    def step(self, state):
        validate(state)
        checks = 0
        if self.previous is None or self.mode == 'full':
            selected = list(DEPENDENCIES)
        elif self.mode == 'incremental':
            checks = len(DEPENDENCIES)
            selected = [name for name, fields in DEPENDENCIES.items()
                        if any(self.previous[k] != state[k] for k in fields)]
        else:
            selected = []
        for name in selected:
            self.cache[name] = predicate(name, state)
        self.previous = dict(state)
        return {'decision': aggregate(self.cache.values()),
                'predicate_evaluations': len(selected), 'dependency_group_checks': checks,
                'cache_writes': len(selected), 'aggregation_calls': 1,
                'recomputed': selected}


def replay(trajectory, mode):
    method = Method(mode)
    state = dict(trajectory['initial_state'])
    rows = []
    for event in trajectory['events']:
        if not set(event['patch']) <= FIELDS:
            raise ValueError('unknown patch fields')
        state.update(event['patch'])
        rows.append({'id': event['id'], 'visible_state': dict(state),
                     'input_field_assignments': len(event['patch']), **method.step(state)})
    return rows


def study(data):
    # Generate all predictions before consulting expectations.
    modes = ('full', 'incremental', 'stale_negative_control')
    outputs = {mode: [r for t in data['trajectories'] for r in replay(t, mode)] for mode in modes}
    expectations, withdrawals = {}, set()
    for trajectory in data['trajectories']:
        prev = None
        for event in trajectory['events']:
            if event['id'] in expectations:
                raise ValueError('duplicate id')
            expectations[event['id']] = event['expected']
            if prev == 'close' and event['expected'] != 'close':
                withdrawals.add(event['id'])
            prev = event['expected']
    predecessors = {b['id']: a['id'] for t in data['trajectories']
                    for a, b in zip(t['events'], t['events'][1:])}
    totals = {}
    for mode, rows in outputs.items():
        decisions = {r['id']: r['decision'] for r in rows}
        totals[mode] = {
            'correct': sum(r['decision'] == expectations[r['id']] for r in rows),
            'n': len(rows),
            'false_close': sum(r['decision'] == 'close' and expectations[r['id']] != 'close' for r in rows),
            'nonclose_denominator': sum(v != 'close' for v in expectations.values()),
            'same_event_withdrawals': sum(decisions[predecessors[r['id']]] == 'close' and r['decision'] != 'close'
                                          for r in rows if r['id'] in withdrawals),
            'nonclose_at_withdrawal_event': sum(r['decision'] != 'close' for r in rows if r['id'] in withdrawals),
            'withdrawal_denominator': len(withdrawals),
            **{key: sum(r[key] for r in rows) for key in ('predicate_evaluations', 'dependency_group_checks', 'cache_writes', 'aggregation_calls', 'input_field_assignments')},
        }
    return {'summary': {'kind': 'synthetic mechanism experiment; not AI A/B',
                        'trajectories': len(data['trajectories']), 'model_api_calls': 0,
                        'human_minutes': None, 'monetary_cost': None, 'methods': totals},
            'predictions': outputs, 'expectations': expectations}


def run(root, output):
    freeze = json.loads((root / 'experiments/stage-09/input-freeze.json').read_text())
    for name, sha in freeze['files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen input mismatch')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output must be empty')
    data = json.loads((root / 'data/synthetic/stage-09/trajectories.json').read_text())
    result = study(data)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in result.items():
        (output / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return result['summary']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(__file__).resolve().parents[1], args.output), indent=2))
