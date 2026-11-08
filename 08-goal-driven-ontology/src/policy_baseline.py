"""Manually programmed synthetic structured-fact policy baseline. No model calls."""
from datetime import date
import json


class InputFault(Exception):
    def __init__(self, reason, missing=False):
        self.reason, self.missing = reason, missing


def required(obj, key):
    if not isinstance(obj, dict):
        raise InputFault('malformed_input')
    if key not in obj:
        raise InputFault('input_missing', True)
    return obj[key]


def obj(value):
    if not isinstance(value, dict):
        raise InputFault('malformed_input')
    return value


def array(value):
    if not isinstance(value, list):
        raise InputFault('malformed_input')
    return value


def string(value):
    if not isinstance(value, str) or not value:
        raise InputFault('malformed_input')
    return value


def number(value, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise InputFault('malformed_input')
    return value


def day(value):
    if value is None:
        raise InputFault('input_missing', True)
    string(value)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise InputFault('malformed_input') from None
    if parsed.isoformat() != value:
        raise InputFault('malformed_input')
    return parsed


def choice(value, options):
    if value not in options:
        raise InputFault('malformed_input')
    return value


def strings(value):
    value = array(value)
    for item in value:
        string(item)
    if len(set(value)) != len(value):
        raise InputFault('malformed_input')
    return set(value)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise InputFault('malformed_input') from None


def base_request(facts):
    request = obj(required(facts, 'request'))
    string(required(request, 'po_line'))
    number(required(request, 'invoice_quantity'), positive=True)
    return request


def f01(facts):
    r = base_request(facts)
    string(required(r, 'invoice_id'))
    targets = strings(required(r, 'target_serials'))
    if r['invoice_quantity'] != len(targets):
        return 'needs_review', 'target_count_mismatch'
    participating = {}
    for lot in array(required(facts, 'lots')):
        obj(lot)
        line = string(required(lot, 'po_line'))
        status = choice(required(lot, 'status'), ('accepted', 'pending'))
        if line != r['po_line'] or status != 'accepted':
            continue
        serials = strings(required(lot, 'serials'))
        if not serials & targets:
            continue
        identity = string(required(lot, 'lot_id'))
        # Serial order is not a fact; all other supplied payload fields are retained.
        normalized = dict(lot, serials=sorted(serials))
        payload = canonical(normalized)
        if identity in participating and participating[identity][0] != payload:
            return 'needs_review', 'lot_identity_conflict'
        participating[identity] = (payload, serials)
    seen = set()
    for _, serials in participating.values():
        if seen & serials:
            return 'needs_review', 'overlapping_lots'
        seen.update(serials)
    if not targets <= seen:
        return 'needs_evidence', 'uncovered_serials'
    return 'close_eligible', 'criteria_met'


def f02(facts):
    r = base_request(facts)
    a = obj(required(facts, 'acceptance'))
    if string(required(a, 'po_line')) != r['po_line']:
        return 'needs_review', 'acceptance_line_mismatch'
    signer = string(required(a, 'signer'))
    signed = day(required(a, 'signed_on'))
    matches = []
    denied = False
    for grant in array(required(facts, 'delegation_registry')):
        obj(grant)
        if string(required(grant, 'signer')) != signer or string(required(grant, 'po_line')) != r['po_line']:
            continue
        start, end = day(required(grant, 'valid_from')), day(required(grant, 'valid_to'))
        if start > end:
            raise InputFault('malformed_input')
        if not start <= signed <= end:
            continue
        kind = choice(required(grant, 'type'), ('grant', 'deny'))
        if kind == 'deny':
            denied = True
        else:
            matches.append(grant)
    if denied:
        return 'needs_review', 'explicit_authority_denial'
    if not matches:
        return 'needs_evidence', 'authority_unproven'
    limit = max(number(required(g, 'max_quantity')) for g in matches)
    quantity = number(required(a, 'accepted_quantity'), positive=True)
    if quantity > limit:
        return 'needs_review', 'authority_limit_exceeded'
    if quantity < r['invoice_quantity']:
        return 'needs_evidence', 'quantity_shortfall'
    return 'close_eligible', 'criteria_met'


def f03(facts):
    r = base_request(facts)
    relevant = []
    identities = {}
    for entry in array(required(facts, 'inspection_register')):
        obj(entry)
        line = string(required(entry, 'po_line'))
        phase = choice(required(entry, 'phase'), ('final', 'preliminary'))
        if line == r['po_line'] and phase == 'final':
            rid = string(required(entry, 'report_id'))
            payload = canonical(entry)
            if rid in identities and identities[rid] != payload:
                raise InputFault('conflicting_facts')
            identities[rid] = payload
            choice(required(entry, 'status'), ('accepted', 'rejected', 'pending', 'unknown'))
            relevant.append(entry)
    accepted = [x for x in relevant if x['status'] == 'accepted']
    rejected = any(x['status'] == 'rejected' for x in relevant)
    if accepted and rejected:
        return 'needs_review', 'contradictory_final_status'
    if rejected:
        return 'needs_review', 'final_rejection'
    if not accepted:
        return 'needs_evidence', 'final_acceptance_missing'
    if max(number(required(x, 'quantity')) for x in accepted) < r['invoice_quantity']:
        return 'needs_evidence', 'quantity_shortfall'
    return 'close_eligible', 'criteria_met'


def f04(facts):
    r = base_request(facts)
    as_of = day(required(r, 'as_of'))
    ledger = obj(required(facts, 'acceptance_ledger'))
    records = {}
    for record in array(required(ledger, 'records')):
        obj(record)
        if day(required(record, 'created_on')) > as_of:
            continue
        rid = string(required(record, 'record_id'))
        if string(required(record, 'po_line')) != r['po_line']:
            raise InputFault('unsupported_case')
        choice(required(record, 'status'), ('accepted', 'rejected'))
        if rid in records and canonical(records[rid]) != canonical(record):
            raise InputFault('conflicting_facts')
        records[rid] = record
    active_events = []
    for event in array(required(ledger, 'events')):
        obj(event)
        if day(required(event, 'effective_on')) > as_of:
            continue
        string(required(event, 'event_id'))
        choice(required(event, 'type'), ('revoke', 'supersede'))
        old = string(required(event, 'old_id'))
        new = string(required(event, 'new_id')) if event['type'] == 'supersede' else None
        active_events.append((old, new))
    if any(old not in records or (new is not None and new not in records)
           for old, new in active_events):
        return 'needs_evidence', 'ledger_endpoint_missing'
    graph = {rid: set() for rid in records}
    retired = set()
    for old, new in active_events:
        retired.add(old)
        if new is not None:
            graph[old].add(new)
    # Kahn's algorithm detects cycles without a recursion-depth limit.
    indegree = dict.fromkeys(graph, 0)
    for successors in graph.values():
        for successor in successors:
            indegree[successor] += 1
    ready = [node for node, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for successor in graph[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if visited != len(graph):
        return 'needs_review', 'supersession_cycle'
    if any(len(successors) > 1 for successors in graph.values()):
        return 'needs_review', 'supersession_fork'
    live = [record for rid, record in records.items() if rid not in retired]
    if any(x['status'] == 'rejected' for x in live):
        return 'needs_review', 'active_rejection'
    if not live:
        return 'needs_evidence', 'live_acceptance_missing'
    if max(number(required(x, 'quantity')) for x in live) < r['invoice_quantity']:
        return 'needs_evidence', 'quantity_shortfall'
    return 'close_eligible', 'criteria_met'


def f05(facts):
    r = base_request(facts)
    if r.get('receipt_on') is None:
        return 'needs_evidence', 'receipt_date_missing'
    receipt = day(r['receipt_on'])
    a = obj(required(facts, 'acceptance'))
    if day(required(a, 'signed_on')) < receipt:
        return 'needs_review', 'acceptance_before_receipt'
    if choice(required(a, 'status'), ('accepted', 'rejected')) == 'rejected':
        return 'needs_review', 'explicit_rejection'
    regime = choice(required(a, 'declared_regime'), ('OLD', 'NEW'))
    if receipt < date(2026, 7, 1):
        if regime != 'OLD':
            return 'needs_review', 'regime_mismatch'
    elif regime == 'NEW':
        release = facts.get('quality_release')
        if release is None:
            return 'needs_evidence', 'quality_release_missing'
        obj(release)
        if release.get('released') is not True or release.get('released_on') is None:
            return 'needs_evidence', 'quality_release_missing'
        if day(release['released_on']) < receipt:
            return 'needs_evidence', 'quality_release_missing'
    else:
        transition = facts.get('transition_register')
        if transition is None:
            return 'needs_evidence', 'grandfathering_unproven'
        obj(transition)
        if (transition.get('po_line') != r['po_line'] or transition.get('permitted') is not True
                or transition.get('grandfather_until') is None):
            return 'needs_evidence', 'grandfathering_unproven'
        if day(transition['grandfather_until']) < receipt:
            return 'needs_evidence', 'grandfathering_unproven'
    if number(required(a, 'quantity')) < r['invoice_quantity']:
        return 'needs_evidence', 'quantity_shortfall'
    return 'close_eligible', 'criteria_met'


def f06(facts):
    r = base_request(facts)
    string(required(r, 'invoice_id'))
    claim = obj(required(facts, 'closure_claim'))
    source_id, locator = string(required(claim, 'source_id')), string(required(claim, 'locator'))
    cited = []
    for source in array(required(facts, 'source_catalog')):
        obj(source)
        if string(required(source, 'source_id')) != source_id:
            continue
        for paragraph in array(required(source, 'paragraphs')):
            obj(paragraph)
            if string(required(paragraph, 'locator')) == locator:
                cited.append((source.get('kind'), paragraph))
    if not cited:
        return 'needs_evidence', 'cited_locator_missing'
    if len({canonical(x) for x in cited}) > 1:
        raise InputFault('conflicting_facts')
    kind, p = cited[0]
    if kind != 'ACCEPTANCE_RECORD' or p.get('paragraph_mode') != 'asserted':
        return 'needs_evidence', 'source_not_acceptance'
    if p.get('invoice_id') is None or p.get('po_line') is None:
        return 'needs_evidence', 'linkage_missing'
    if p['invoice_id'] != r['invoice_id'] or p['po_line'] != r['po_line']:
        return 'needs_review', 'cited_scope_mismatch'
    if p.get('status') in ('rejected', 'not_accepted'):
        return 'needs_review', 'explicit_nonacceptance'
    if p.get('status') != 'accepted':
        return 'needs_evidence', 'acceptance_assertion_missing'
    if p.get('accepted_quantity') is None or p.get('unit') is None:
        return 'needs_evidence', 'acceptance_detail_missing'
    if p['unit'] != 'EA':
        return 'needs_review', 'unit_mismatch'
    if p.get('signer_role') != 'RECEIVING_OFFICER':
        return 'needs_evidence', 'acceptance_detail_missing'
    if number(p['accepted_quantity']) < r['invoice_quantity']:
        return 'needs_evidence', 'quantity_shortfall'
    return 'close_eligible', 'criteria_met'


RULES = {'F01': f01, 'F02': f02, 'F03': f03, 'F04': f04, 'F05': f05, 'F06': f06}


def predict_case(case, materials):
    """Return a recommendation and conservative supplied-source audit trace.

    materials is the parsed JSON policy for this family, not an interpreter or
    evaluator artifact. Text is not interpreted: rules above are hand-coded.
    """
    refs = set()
    case_id = case.get('case_id') if isinstance(case, dict) else None
    try:
        obj(case)
        string(required(case, 'case_id'))
        family = string(required(case, 'family_id'))
        if family not in RULES:
            raise InputFault('unsupported_case')
        obj(materials)
        if materials.get('family_id') != family:
            raise InputFault('unsupported_case')
        policy_id = string(required(case, 'policy_source_id'))
        policy_ids = set()
        for paragraph in array(required(materials, 'policy_paragraphs')):
            obj(paragraph)
            sid = string(required(paragraph, 'source_id'))
            loc = string(required(paragraph, 'locator'))
            string(required(paragraph, 'text'))
            refs.add((sid, loc))
            policy_ids.add(sid)
        if policy_id not in policy_ids:
            raise InputFault('unsupported_case')
        facts = {}
        # Duplicate top-level keys must have exactly equal JSON values. Arrays
        # are not concatenated and nested dictionaries are not merged.
        for source in array(required(case, 'sources')):
            obj(source)
            sid = string(required(source, 'source_id'))
            loc = string(required(source, 'locator'))
            refs.add((sid, loc))
            fields = obj(required(source, 'facts'))
            for key, value in fields.items():
                if key in facts and canonical(facts[key]) != canonical(value):
                    raise InputFault('conflicting_facts')
                facts[key] = value
        decision, reason = RULES[family](facts)
    except InputFault as error:
        decision = 'needs_evidence' if error.missing else 'needs_review'
        reason = error.reason
    return {
        'case_id': case_id,
        'decision': decision,
        'evidence_ids': [sid + '#' + loc for sid, loc in sorted(refs)],
        'reason_codes': [reason],
        'source_refs': [{'source_id': sid, 'locator': loc} for sid, loc in sorted(refs)],
        'payment_authorized': False,
    }
