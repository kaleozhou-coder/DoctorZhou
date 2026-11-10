"""Bounded, eager input gate around the unchanged synthetic policy baseline.

This validates structured data, not natural-language entailment. See the v1
contract for legacy assumptions, provenance-only text and closure abstention.
"""
from datetime import date
import json

from policy_baseline import predict_case as baseline_predict

MAX_BYTES = 262144
MAX_DEPTH = 24
MAX_NODES = 20000
MAX_ITEMS = 1000
MAX_STRING = 8192
MAX_INTEGER = 10**12


class ContractError(ValueError):
    def __init__(self, code, path='$'):
        self.code, self.path = code, path
        super().__init__(code + ' at ' + path)


def fail(code, path):
    raise ContractError(code, path)


def bounded(value):
    """Check Python input too, before serialization or recursive schema checks."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            fail('contract_limit', '$')
        if type(item) is dict:
            if len(item) > MAX_ITEMS or any(type(k) is not str for k in item):
                fail('contract_type', '$')
            pending.extend((v, depth + 1) for v in item.values())
            pending.extend((k, depth + 1) for k in item)
        elif type(item) is list:
            if len(item) > MAX_ITEMS:
                fail('contract_limit', '$')
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            if len(item) > MAX_STRING:
                fail('contract_limit', '$')
            try:
                item.encode('utf-8', errors='strict')
            except UnicodeError:
                fail('contract_encoding', '$')
        elif type(item) is int:
            if abs(item) > MAX_INTEGER:
                fail('contract_limit', '$')
        elif item is not None and type(item) is not bool:
            fail('contract_type', '$')
    if len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > MAX_BYTES:
        fail('contract_limit', '$')


def loads_case(raw):
    """Strict JSON decoder; raises ContractError, never evaluates input code."""
    if type(raw) not in (str, bytes):
        fail('contract_type', '$')
    try:
        data = raw.encode('utf-8') if type(raw) is str else raw
        if len(data) > MAX_BYTES:
            fail('contract_limit', '$')
        text = data.decode('utf-8', errors='strict')
        # Bound nesting before the stdlib decoder allocates a recursive tree.
        depth, quoted, escape = 0, False, False
        for ch in text:
            if quoted:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    quoted = False
            elif ch == '"':
                quoted = True
            elif ch in '[{':
                depth += 1
                if depth > MAX_DEPTH:
                    fail('contract_limit', '$')
            elif ch in ']}':
                depth -= 1
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out:
                    fail('contract_duplicate_key', '$')
                out[key] = value
            return out
        def no_constant(_):
            fail('contract_type', '$')
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=no_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, ContractError):
            raise
        fail('contract_json', '$')
    bounded(result)
    return result


# Schema constructors: dictionaries are closed; ? fields may be absent;
# nullable is explicit, and integer/bool types never coerce one another.
def nullable(spec):
    return ('nullable', spec)


def enum(*values):
    return ('enum', values)


def array(spec):
    return ('array', spec)


def check(value, spec, path):
    if isinstance(spec, dict):
        if type(value) is not dict:
            fail('contract_type', path)
        keys = {k.rstrip('?'): k for k in spec}
        if set(value) - set(keys):
            fail('contract_unknown_field', path + '.' + sorted(set(value) - set(keys))[0])
        for key, rule in spec.items():
            name = key.rstrip('?')
            if name not in value:
                if not key.endswith('?'):
                    fail('contract_missing', path + '.' + name)
            else:
                check(value[name], rule, path + '.' + name)
    elif isinstance(spec, tuple):
        kind, argument = spec
        if kind == 'nullable':
            if value is not None:
                check(value, argument, path)
        elif kind == 'array':
            if type(value) is not list:
                fail('contract_type', path)
            for index, item in enumerate(value):
                check(item, argument, path + '[' + str(index) + ']')
        elif type(value) is not str or value not in argument:
            fail('contract_enum', path)
    elif spec == 'str' or spec == 'text':
        if type(value) is not str or (spec == 'str' and not value.strip()):
            fail('contract_type', path)
    elif spec == 'date':
        try:
            if type(value) is not str or date.fromisoformat(value).isoformat() != value:
                fail('contract_date', path)
        except ValueError:
            fail('contract_date', path)
    elif spec == 'bool':
        if type(value) is not bool:
            fail('contract_type', path)
    elif spec in ('nat', 'positive'):
        if type(value) is not int or value < (1 if spec == 'positive' else 0):
            fail('contract_type', path)


STATUS = enum('accepted', 'rejected', 'not_accepted', 'pending', 'unknown')
PARAGRAPH = {'locator?': 'str', 'paragraph_mode?': enum('asserted', 'quoted', 'example'),
             'invoice_id?': nullable('str'), 'po_line?': nullable('str'),
             'status?': nullable(STATUS), 'accepted_quantity?': nullable('nat'),
             'unit?': nullable('str'), 'signer_role?': nullable('str'), 'text?': 'text'}
REQUEST = {'po_line': 'str', 'invoice_quantity': 'positive'}
SCHEMAS = {
    'F01': {'request': dict(REQUEST, invoice_id='str', target_serials=array('str')),
            'lots': array({'lot_id': 'str', 'po_line': 'str', 'status': enum('accepted', 'pending'), 'serials': array('str')})},
    'F02': {'request': REQUEST,
            'acceptance': {'po_line': 'str', 'signer': 'str', 'signed_on': 'date', 'accepted_quantity': 'positive', 'status?': STATUS},
            'delegation_registry': array({'type': enum('grant', 'deny'), 'signer': 'str', 'po_line': 'str', 'valid_from': 'date', 'valid_to': 'date', 'max_quantity?': 'nat'})},
    'F03': {'request': REQUEST,
            'inspection_register': array({'report_id': 'str', 'po_line': 'str', 'phase': enum('final', 'preliminary'), 'status': enum('accepted', 'rejected', 'pending', 'unknown'), 'quantity': 'nat', 'recorded_on': 'date'})},
    'F04': {'request': dict(REQUEST, as_of='date'),
            'acceptance_ledger': {'records': array({'record_id': 'str', 'po_line': 'str', 'status': enum('accepted', 'rejected'), 'quantity': 'nat', 'created_on': 'date'}),
                                  'events': array({'event_id': 'str', 'type': enum('revoke', 'supersede'), 'old_id': 'str', 'new_id?': nullable('str'), 'effective_on': 'date'})}},
    'F05': {'request': dict(REQUEST, **{'receipt_on?': nullable('date'), 'invoice_on?': 'date', 'reviewed_on?': 'date'}),
            'acceptance': {'signed_on': 'date', 'declared_regime': enum('OLD', 'NEW'), 'quantity': 'nat', 'status': enum('accepted', 'rejected'), 'po_line?': 'str'},
            'quality_release?': nullable({'released?': 'bool', 'released_on?': nullable('date')}),
            'transition_register?': nullable({'po_line?': 'str', 'permitted?': 'bool', 'grandfather_until?': nullable('date')})},
    'F06': {'request': dict(REQUEST, invoice_id='str'), 'closure_claim': {'source_id': 'str', 'locator': 'str'},
            'source_catalog': array({'source_id': 'str', 'kind': 'str', 'invoice_id?': nullable('str'), 'paragraphs': array(PARAGRAPH)})},
}
# Legacy F06 attachment facts are repeated at top level. They remain typed and
# are checked against their own catalog locator, never used to fill a gap.
SCHEMAS['F06'].update({k: v for k, v in PARAGRAPH.items() if k not in ('locator?', 'text?')})


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def validate_case(case):
    """Return merged facts after eager checks, or raise ContractError.

    Does not mutate the case and does not read labels, files or network.
    """
    bounded(case)
    # facts have family-specific keys; envelope checking is separated so all
    # partial source objects can be merged without pretending nested merges.
    envelope = {'case_id': 'str', 'family_id': enum(*SCHEMAS), 'policy_source_id': 'str',
                'split?': 'str', 'question?': 'text', 'synthetic?': 'bool', 'raw_text?': 'text'}
    if type(case) is not dict:
        fail('contract_type', '$')
    check({k: v for k, v in case.items() if k != 'sources'}, envelope, '$')
    if 'sources' not in case or type(case['sources']) is not list:
        fail('contract_missing', '$.sources')
    family = case['family_id']
    facts, seen_sources = {}, {}
    schema = SCHEMAS[family]
    partial_schema = {k.rstrip('?') + '?': v for k, v in schema.items()}
    for index, source in enumerate(case['sources']):
        path = '$.sources[' + str(index) + ']'
        check(source, {'source_id': 'str', 'locator': 'str', 'text?': 'text', 'source_kind?': 'str',
                       'raw_text?': 'text', 'facts': partial_schema}, path)
        identity = (source['source_id'], source['locator'])
        payload = canonical(source)
        if identity in seen_sources and seen_sources[identity] != payload:
            fail('contract_source_identity_conflict', path)
        seen_sources[identity] = payload
        for key, value in source['facts'].items():
            if key in facts and canonical(facts[key]) != canonical(value):
                fail('contract_conflicting_facts', path + '.facts.' + key)
            facts[key] = value
    check(facts, schema, '$.facts')
    if family == 'F01':
        for path, serials in [('target_serials', facts['request']['target_serials'])] + [
                ('lots.serials', lot['serials']) for lot in facts['lots']]:
            if len(set(serials)) != len(serials):
                fail('contract_duplicate_serial', '$.facts.' + path)
    elif family == 'F02':
        status = facts['acceptance'].get('status', 'accepted')
        if status != 'accepted':
            fail('contract_acceptance_not_positive', '$.facts.acceptance.status')
        for grant in facts['delegation_registry']:
            if grant['type'] == 'grant' and 'max_quantity' not in grant:
                fail('contract_missing', '$.facts.delegation_registry.max_quantity')
            if grant['valid_from'] > grant['valid_to']:
                fail('contract_date_interval', '$.facts.delegation_registry')
    elif family == 'F04':
        identities = {}
        for event in facts['acceptance_ledger']['events']:
            if event['type'] == 'supersede' and not event.get('new_id'):
                fail('contract_missing', '$.facts.acceptance_ledger.events.new_id')
            identity, payload = event['event_id'], canonical(event)
            if identity in identities and identities[identity] != payload:
                fail('contract_event_identity_conflict', '$.facts.acceptance_ledger.events')
            identities[identity] = payload
    elif family == 'F05':
        a = facts['acceptance']
        if 'po_line' in a and a['po_line'] != facts['request']['po_line']:
            fail('contract_acceptance_line_mismatch', '$.facts.acceptance.po_line')
    elif family == 'F06':
        for source in case['sources']:
            flat = {k: v for k, v in source['facts'].items() if k in {x.rstrip('?') for x in PARAGRAPH}}
            if not flat:
                continue
            matches = [p for s in facts['source_catalog'] if s['source_id'] == source['source_id']
                       for p in s['paragraphs'] if p.get('locator') == source['locator']]
            if not matches or any(any(k not in p or p[k] != v for k, v in flat.items()) for p in matches):
                fail('contract_attachment_mismatch', '$.sources')
    return facts


def apply_contract(case, materials, predictor):
    """Gate a trusted predictor(case, materials); preserve its output fields.

    Policies and the callable are trusted, not executable untrusted input.
    Exceptions in a supplied predictor are not hidden by this input validator.
    """
    try:
        if type(case) in (bytes, str):
            case = loads_case(case)
        facts = validate_case(case)
    except ContractError as error:
        return {'case_id': case.get('case_id') if type(case) is dict and type(case.get('case_id')) is str else None,
                'decision': 'needs_evidence' if error.code == 'contract_missing' else 'needs_review',
                'evidence_ids': [], 'reason_codes': [error.code], 'source_refs': [],
                'payment_authorized': False, 'input_contract': {
                    'version': '1', 'status': 'blocked', 'code': error.code, 'path': error.path}}
    result = dict(predictor(case, materials))
    unverified = bool(case.get('raw_text')) or any(s.get('raw_text') for s in case['sources'])
    if case['family_id'] == 'F06':
        unverified = unverified or any(p.get('text') for s in facts['source_catalog'] for p in s['paragraphs'])
    result['input_contract'] = {'version': '1', 'status': 'validated',
                                'prose_verified': False, 'unverified_text_present': bool(unverified)}
    if unverified and result['decision'] == 'close_eligible':
        result['decision'] = 'needs_review'
        result['reason_codes'] = ['contract_text_unverified']
        result['input_contract']['status'] = 'abstained'
    result['payment_authorized'] = False
    return result


def predict_case(case, materials):
    """Convenience entry point using the unchanged deterministic baseline."""
    return apply_contract(case, materials, baseline_predict)
