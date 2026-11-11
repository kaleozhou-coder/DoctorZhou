"""Bounded data-only Rule IR v3. No code loading, evaluation or family dispatch."""
from datetime import date
import json
import math

VERSION = 'rule-ir-v3'
MAX_ITEMS = 128
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


def _type(kind, depth=0):
    if depth > 4:
        raise RuleError('type depth')
    if type(kind) is str:
        if kind not in TYPES: raise RuleError('unknown type')
        return
    _keys(kind, ('kind',), ('items', 'fields'))
    if kind['kind'] in ('array', 'set'):
        _keys(kind, ('kind', 'items'))
        _type(kind['items'], depth + 1)
        if kind['kind'] == 'set' and kind['items'] not in ('string', 'integer', 'date'):
            raise RuleError('set requires ordered scalar')
    elif kind['kind'] == 'record':
        _keys(kind, ('kind', 'fields'))
        if type(kind['fields']) is not dict or not 1 <= len(kind['fields']) <= 32:
            raise RuleError('record fields')
        for k, v in kind['fields'].items():
            _text(k); _type(v, depth + 1)
    else: raise RuleError('unknown type')


def _value(value, kind):
    if value is None: return UNKNOWN
    if type(kind) is str: return _scalar(value, kind)
    if kind['kind'] in ('array', 'set'):
        if type(value) is not list or len(value) > MAX_ITEMS:
            raise RuleError('bounded array required')
        values = [_value(v, kind['items']) for v in value]
        if kind['kind'] == 'set':
            # Validate all known members before propagating missingness.
            # Otherwise [null, 1, 1] masks the malformed duplicate as UNKNOWN.
            known = [v for v in values if v is not UNKNOWN]
            if len(set(known)) != len(known): raise RuleError('duplicate set member')
        if any(v is UNKNOWN for v in values): return UNKNOWN
        return sorted(values) if kind['kind'] == 'set' else values
    if type(value) is not dict: raise RuleError('record required')
    out = dict(value)  # Extra payload retained for identity conflict comparisons.
    missing = False
    for key, subtype in kind['fields'].items():
        out[key] = _value(value.get(key), subtype)
        missing |= out[key] is UNKNOWN
    return UNKNOWN if missing else out


def _collection(kind, tag):
    if type(kind) is not dict or kind.get('kind') != tag:
        raise RuleError('wrong collection type')
    return kind['items']


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _validate(program, available_refs=None):
    """Validate structure/types. Optional supplied locator set verifies existence only."""
    _json_bound(program)
    _keys(program, ('version', 'fields', 'rules', 'default'))
    if program['version'] != VERSION or type(program['fields']) is not dict or not 1 <= len(program['fields']) <= 64:
        raise RuleError('invalid version/fields')
    fields = program['fields']
    for name, spec in fields.items():
        _text(name)
        _keys(spec, ('path', 'type'), ('minimum', 'enum'))
        _type(spec['type'])
        if type(spec['path']) is not list or not 1 <= len(spec['path']) <= 8:
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
            seen_values = set()
            for value in spec['enum']:
                value = _value(value, spec['type'])
                if value is UNKNOWN:
                    raise RuleError('enum must contain complete typed values')
                canonical = _canonical(value)
                if canonical in seen_values:
                    raise RuleError('duplicate enum member')
                seen_values.add(canonical)
    count = 0
    def expr(node, depth=0, item_type=None):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise RuleError('AST limit')
        if type(node) is not dict:
            raise RuleError('expected expression')
        op = node.get('op')
        if op == 'item':
            _keys(node, ('op', 'key'))
            if type(item_type) is not dict or item_type.get('kind') != 'record' or type(node['key']) is not str or node['key'] not in item_type['fields']:
                raise RuleError('item outside record filter or unknown key')
            return item_type['fields'][node['key']]
        if op == 'filter':
            _keys(node, ('op', 'arg', 'where'))
            kind = expr(node['arg'], depth + 1, item_type)
            subtype = _collection(kind, 'array')
            if expr(node['where'], depth + 1, subtype) != 'boolean': raise RuleError('filter predicate')
            return kind
        if op in ('count', 'identity_conflict', 'distinct_by', 'union', 'overlap'):
            _keys(node, ('op', 'arg'), ('key',))
            kind = expr(node['arg'], depth + 1, item_type)
            if op == 'count':
                if 'key' in node or type(kind) is not dict or kind.get('kind') not in ('array', 'set'): raise RuleError('count type')
                return 'integer'
            subtype = _collection(kind, 'array')
            if type(subtype) is not dict or subtype.get('kind') != 'record' or type(node.get('key')) is not str or node['key'] not in subtype['fields']: raise RuleError('record key')
            target = subtype['fields'][node['key']]
            if op in ('identity_conflict', 'distinct_by'):
                if target != 'string': raise RuleError('identity must be string')
                return 'boolean' if op == 'identity_conflict' else kind
            _collection(target, 'set')
            return 'boolean' if op == 'overlap' else target
        if op in ('intersects', 'subset'):
            _keys(node, ('op', 'left', 'right'))
            left, right = expr(node['left'], depth + 1, item_type), expr(node['right'], depth + 1, item_type)
            _collection(left, 'set')
            if left != right: raise RuleError('incompatible sets')
            return 'boolean'
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
            kind = expr(node['arg'], depth + 1, item_type)
            if op == 'not' and kind != 'boolean':
                raise RuleError('not requires boolean')
        elif op in ('all', 'any'):
            _keys(node, ('op', 'args'))
            if type(node['args']) is not list or not 1 <= len(node['args']) <= 32:
                raise RuleError('invalid operands')
            if any(expr(x, depth + 1, item_type) != 'boolean' for x in node['args']):
                raise RuleError('boolean operands required')
        elif op in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            _keys(node, ('op', 'left', 'right'))
            left, right = expr(node['left'], depth + 1, item_type), expr(node['right'], depth + 1, item_type)
            if type(left) is not str or left != right or (op not in ('eq', 'ne') and left not in ('integer', 'date')):
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


def validate(program, available_refs=None):
    """Normalize malformed Python API values to RuleError, including bad tags."""
    try:
        return _validate(program, available_refs)
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise RuleError(str(exc)) from None


def evaluate(program, facts, available_refs=None):
    """First true wins; first unknown blocks later rules. Invalid input never closes."""
    refs, trace, steps = [], [], 0
    def result(decision, reason, rule_id=None):
        return {'decision': decision, 'reason_codes': [reason], 'rule_id': rule_id,
                'source_refs': refs, 'trace': trace, 'payment_authorized': False}
    try:
        validation = validate(program, available_refs)
        if type(validation) is not dict or validation.get('valid') is not True:
            raise RuleError('artifact validation did not explicitly succeed')
    except (RuleError, TypeError, KeyError, RecursionError):
        return result('needs_review', 'invalid_artifact')
    try:
        _json_bound(facts)
        if type(facts) is not dict:
            raise RuleError('facts must be object')
        def run(node, item=None):
            nonlocal steps
            steps += 1
            if steps > MAX_STEPS:
                raise RuleError('execution budget')
            op = node['op']
            if op == 'item': return item[node['key']]
            if op == 'filter':
                values = run(node['arg'], item)
                if values is UNKNOWN: return UNKNOWN
                selected, unknown = [], False
                for row in values:
                    match = run(node['where'], row)
                    unknown |= match is UNKNOWN
                    if match is True: selected.append(row)
                return UNKNOWN if unknown else selected
            if op in ('count', 'identity_conflict', 'distinct_by', 'union', 'overlap'):
                values = run(node['arg'], item)
                if values is UNKNOWN: return UNKNOWN
                steps += len(values)
                if steps > MAX_STEPS: raise RuleError('execution budget')
                if op == 'count': return len(values)
                key = node['key']
                if op in ('identity_conflict', 'distinct_by'):
                    seen, conflict = {}, False
                    for row in values:
                        identity = row[key]
                        if identity in seen and _canonical(seen[identity]) != _canonical(row): conflict = True
                        seen[identity] = row
                    if op == 'identity_conflict': return conflict
                    if conflict: raise RuleError('conflicting identity cannot deduplicate')
                    return list(seen.values())
                seen, overlap = set(), False
                for row in values:
                    steps += len(row[key])
                    if steps > MAX_STEPS: raise RuleError('execution budget')
                    overlap |= bool(seen.intersection(row[key]))
                    seen.update(row[key])
                    if len(seen) > MAX_ITEMS: raise RuleError('derived set budget')
                return overlap if op == 'overlap' else sorted(seen)
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
                value = _value(value, spec['type'])
                if value is UNKNOWN: return UNKNOWN
                if ('minimum' in spec and value < spec['minimum']) or ('enum' in spec and _canonical(value) not in {_canonical(_value(v, spec['type'])) for v in spec['enum']}):
                    raise RuleError('field constraint')
                return value
            if op in ('not', 'is_unknown'):
                value = run(node['arg'], item)
                return value is UNKNOWN if op == 'is_unknown' else (UNKNOWN if value is UNKNOWN else not value)
            if op in ('all', 'any'):
                # Evaluate all operands: malformed facts cannot hide inside a boolean branch.
                values = [run(x, item) for x in node['args']]
                decisive = False if op == 'all' else True
                if any(v is decisive for v in values):
                    return decisive
                return UNKNOWN if any(v is UNKNOWN for v in values) else not decisive
            left, right = run(node['left'], item), run(node['right'], item)
            if left is UNKNOWN or right is UNKNOWN:
                return UNKNOWN
            if op == 'intersects': return bool(set(left).intersection(right))
            if op == 'subset': return set(left).issubset(right)
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
