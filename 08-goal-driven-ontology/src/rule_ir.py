"""Bounded data-only Rule IR v1. No code loading, evaluation or family dispatch."""
from datetime import date
import json
import math

VERSION = 'rule-ir-v1'
MAX_BYTES = 131072
MAX_NODES = 512
MAX_DEPTH = 24
MAX_STEPS = 4096
UNKNOWN = object()
TYPES = {'boolean', 'integer', 'string', 'date'}
DECISIONS = {'close_eligible', 'needs_evidence', 'needs_review'}


class RuleError(ValueError):
    pass


def _keys(obj, required, optional=()):
    if type(obj) is not dict or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        raise RuleError('invalid object keys')


def _text(s):
    if type(s) is not str or not s or len(s) > 256:
        raise RuleError('expected bounded nonempty string')
    return s


def _scalar(value, kind):
    if kind == 'boolean':
        ok = type(value) is bool
    elif kind == 'integer':
        ok = type(value) is int and abs(value) <= 2**53 - 1
    elif kind == 'string':
        ok = type(value) is str and 0 < len(value) <= 4096
    elif kind == 'date':
        ok = type(value) is str and len(value) == 10
        if ok:
            try:
                ok = date.fromisoformat(value).isoformat() == value
            except ValueError:
                ok = False
    else:
        ok = False
    if not ok:
        raise RuleError('invalid typed value')
    return value


def _json_bound(value):
    """Check Python API values too: reject cycles, non-JSON and unbounded input."""
    count = 0
    def visit(v, depth):
        nonlocal count
        count += 1
        if depth > 32 or count > 8192:
            raise RuleError('JSON structure limit')
        if type(v) is dict:
            if any(type(k) is not str for k in v):
                raise RuleError('non-string key')
            for x in v.values():
                visit(x, depth + 1)
        elif type(v) is list:
            for x in v:
                visit(x, depth + 1)
        elif v is not None and type(v) not in (str, int, bool, float):
            raise RuleError('non-JSON value')
        elif type(v) is float and not math.isfinite(v):
            raise RuleError('non-finite value')
    visit(value, 0)
    try:
        size = len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    except (ValueError, TypeError, RecursionError) as exc:
        raise RuleError('invalid JSON serialization') from None
    if size > MAX_BYTES:
        raise RuleError('JSON byte limit')


def loads(text):
    """Strict JSON loader: duplicate keys and non-finite numbers are rejected."""
    try:
        if type(text) is not str or len(text.encode('utf-8')) > MAX_BYTES:
            raise RuleError('JSON byte limit')
    except UnicodeError:
        raise RuleError('invalid JSON encoding') from None
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise RuleError('duplicate JSON key')
            out[k] = v
        return out
    def constant(_):
        raise RuleError('non-finite JSON number')
    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        _json_bound(result)
        return result
    except (ValueError, RecursionError) as exc:
        raise RuleError(str(exc)) from None


def validate(program, available_refs=None):
    """Validate structure/types. Optional supplied locator set verifies existence only."""
    _json_bound(program)
    _keys(program, ('version', 'fields', 'rules', 'default'))
    if program['version'] != VERSION or type(program['fields']) is not dict or not 1 <= len(program['fields']) <= 64:
        raise RuleError('invalid version/fields')
    fields = program['fields']
    for name, spec in fields.items():
        _text(name)
        _keys(spec, ('path', 'type'), ('minimum', 'enum'))
        if spec['type'] not in TYPES or type(spec['path']) is not list or not 1 <= len(spec['path']) <= 8:
            raise RuleError('invalid field')
        for key in spec['path']:
            _text(key)
        if 'minimum' in spec:
            if spec['type'] != 'integer':
                raise RuleError('minimum requires integer')
            _scalar(spec['minimum'], 'integer')
        if 'enum' in spec:
            if type(spec['enum']) is not list or not 1 <= len(spec['enum']) <= 32:
                raise RuleError('invalid enum')
            for value in spec['enum']:
                _scalar(value, spec['type'])
    count = 0
    def expr(node, depth=0):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise RuleError('AST limit')
        if type(node) is not dict:
            raise RuleError('expected expression')
        op = node.get('op')
        if op == 'field':
            _keys(node, ('op', 'name'))
            if type(node['name']) is not str or node['name'] not in fields:
                raise RuleError('unknown field')
            return fields[node['name']]['type']
        if op == 'literal':
            _keys(node, ('op', 'type', 'value'))
            _scalar(node['value'], node['type'])
            return node['type']
        if op in ('not', 'is_unknown'):
            _keys(node, ('op', 'arg'))
            kind = expr(node['arg'], depth + 1)
            if op == 'not' and kind != 'boolean':
                raise RuleError('not requires boolean')
        elif op in ('all', 'any'):
            _keys(node, ('op', 'args'))
            if type(node['args']) is not list or not 1 <= len(node['args']) <= 32:
                raise RuleError('invalid operands')
            if any(expr(x, depth + 1) != 'boolean' for x in node['args']):
                raise RuleError('boolean operands required')
        elif op in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            _keys(node, ('op', 'left', 'right'))
            left, right = expr(node['left'], depth + 1), expr(node['right'], depth + 1)
            if left != right or (op not in ('eq', 'ne') and left not in ('integer', 'date')):
                raise RuleError('incompatible comparison')
        else:
            raise RuleError('unknown operator')
        return 'boolean'
    def outcome(item, conditional):
        _keys(item, ('decision', 'reason', 'source_refs') + (('id', 'when') if conditional else ()))
        if item['decision'] not in DECISIONS:
            raise RuleError('invalid decision')
        _text(item['reason'])
        refs = item['source_refs']
        if type(refs) is not list or not 1 <= len(refs) <= 32:
            raise RuleError('source refs required')
        seen = set()
        for ref in refs:
            _keys(ref, ('source_id', 'locator'))
            pair = (_text(ref['source_id']), _text(ref['locator']))
            if pair in seen or (available_refs is not None and pair not in available_refs):
                raise RuleError('duplicate or unavailable source ref')
            seen.add(pair)
        if conditional:
            _text(item['id'])
            if expr(item['when']) != 'boolean':
                raise RuleError('condition must be boolean')
    if type(program['rules']) is not list or not 1 <= len(program['rules']) <= 64:
        raise RuleError('invalid rules')
    ids = set()
    for rule in program['rules']:
        outcome(rule, True)
        if rule['id'] in ids:
            raise RuleError('duplicate rule id')
        ids.add(rule['id'])
    outcome(program['default'], False)
    if program['default']['decision'] == 'close_eligible':
        raise RuleError('default may not close')
    return {'valid': True, 'expression_nodes': count, 'locator_existence_checked': available_refs is not None}


def evaluate(program, facts, available_refs=None):
    """First true wins; first unknown blocks later rules. Invalid input never closes."""
    refs, trace, steps = [], [], 0
    def result(decision, reason, rule_id=None):
        return {'decision': decision, 'reason_codes': [reason], 'rule_id': rule_id,
                'source_refs': refs, 'trace': trace, 'payment_authorized': False}
    try:
        validate(program, available_refs)
    except (RuleError, TypeError, KeyError, RecursionError):
        return result('needs_review', 'invalid_artifact')
    try:
        _json_bound(facts)
        if type(facts) is not dict:
            raise RuleError('facts must be object')
        def run(node):
            nonlocal steps
            steps += 1
            if steps > MAX_STEPS:
                raise RuleError('execution budget')
            op = node['op']
            if op == 'literal':
                return node['value']
            if op == 'field':
                spec = program['fields'][node['name']]
                value = facts
                for key in spec['path']:
                    if value is None:
                        return UNKNOWN
                    if type(value) is not dict:
                        raise RuleError('malformed parent')
                    if key not in value:
                        return UNKNOWN
                    value = value[key]
                if value is None:
                    return UNKNOWN
                _scalar(value, spec['type'])
                if ('minimum' in spec and value < spec['minimum']) or ('enum' in spec and value not in spec['enum']):
                    raise RuleError('field constraint')
                return value
            if op in ('not', 'is_unknown'):
                value = run(node['arg'])
                return value is UNKNOWN if op == 'is_unknown' else (UNKNOWN if value is UNKNOWN else not value)
            if op in ('all', 'any'):
                # Evaluate all operands: malformed facts cannot hide inside a boolean branch.
                values = [run(x) for x in node['args']]
                decisive = False if op == 'all' else True
                if any(v is decisive for v in values):
                    return decisive
                return UNKNOWN if any(v is UNKNOWN for v in values) else not decisive
            left, right = run(node['left']), run(node['right'])
            if left is UNKNOWN or right is UNKNOWN:
                return UNKNOWN
            if op == 'eq': return left == right
            if op == 'ne': return left != right
            if op == 'lt': return left < right
            if op == 'le': return left <= right
            if op == 'gt': return left > right
            if op == 'ge': return left >= right
            raise RuleError('unknown operator')
        for rule in program['rules']:
            refs = rule['source_refs']
            value = run(rule['when'])
            trace.append({'rule_id': rule['id'], 'value': 'unknown' if value is UNKNOWN else value})
            if value is UNKNOWN:
                return result('needs_evidence', 'condition_unknown', rule['id'])
            if value is True:
                return result(rule['decision'], rule['reason'], rule['id'])
        fallback = program['default']
        refs = fallback['source_refs']
        return result(fallback['decision'], fallback['reason'])
    except (RuleError, TypeError, ValueError, RecursionError):
        return result('needs_review', 'malformed_input')


def predict_case(case, artifact, materials):
    """Transport adapter, not a family selector. Caller supplies the chosen artifact.

    Policy locators are checked against supplied materials. Fact-source refs cover
    all merged inputs (not semantic entailment); rule refs describe policy checks.
    """
    case_id = case.get('case_id') if type(case) is dict else None
    fact_refs = set()
    try:
        _json_bound(case)
        _json_bound(materials)
        _text(case_id)
        policy_refs = {(p['source_id'], p['locator']) for p in materials['policy_paragraphs']}
        if case.get('policy_source_id') not in {sid for sid, _ in policy_refs}:
            raise RuleError('policy source unavailable')
        facts = {}
        if type(case['sources']) is not list:
            raise RuleError('sources must be array')
        for source in case['sources']:
            fact_refs.add((_text(source['source_id']), _text(source['locator'])))
            if type(source['facts']) is not dict:
                raise RuleError('facts must be object')
            for key, value in source['facts'].items():
                if key in facts and json.dumps(facts[key], sort_keys=True) != json.dumps(value, sort_keys=True):
                    raise RuleError('conflicting facts')
                facts[key] = value
        output = evaluate(artifact, facts, policy_refs)
    except (RuleError, KeyError, TypeError, ValueError, RecursionError):
        output = {'decision': 'needs_review', 'reason_codes': ['invalid_transport'],
                  'source_refs': [], 'payment_authorized': False}
    refs = fact_refs | {(r['source_id'], r['locator']) for r in output['source_refs']}
    return {'case_id': case_id, 'decision': output['decision'], 'reason_codes': output['reason_codes'],
            'source_refs': [{'source_id': s, 'locator': l} for s, l in sorted(refs)],
            'evidence_ids': [s + '#' + l for s, l in sorted(refs)], 'payment_authorized': False}
