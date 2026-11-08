"""Self-authored examples from policy text, not benchmark cases or labels."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from policy_baseline import predict_case

POLICIES = {f'F{i:02}': json.loads((ROOT / 'benchmark' / 'v1' / 'model-facing' / f'F{i:02}' / 'materials.json').read_text()) for i in range(1, 7)}


def envelope(family, facts):
    return {'case_id': 'self-authored', 'family_id': family, 'split': 'self-authored',
            'policy_source_id': family + '-POL', 'question': 'Synthetic closure recommendation?',
            'sources': [{'source_id': 'FACT-' + key, 'locator': 'p1', 'text': 'Self-authored structured fixture.',
                         'facts': {key: value}} for key, value in facts.items()]}


def request(**extras):
    return dict(po_line='LINE', invoice_quantity=2, **extras)


def lot(identity='L1', serials=None, **extras):
    result = dict(lot_id=identity, po_line='LINE', status='accepted', serials=serials or ['a', 'b'])
    result.update(extras)
    return result


def grant(**extras):
    result = dict(type='grant', signer='receiver', po_line='LINE', valid_from='2026-01-01',
                  valid_to='2026-07-01', max_quantity=2)
    result.update(extras)
    return result


def report(identity='R1', **extras):
    result = dict(report_id=identity, po_line='LINE', phase='final', status='accepted',
                  quantity=2, recorded_on='2026-07-01')
    result.update(extras)
    return result


def record(identity='R1', **extras):
    result = dict(record_id=identity, po_line='LINE', status='accepted', quantity=2, created_on='2026-07-01')
    result.update(extras)
    return result


def event(old='R1', new='R2', **extras):
    result = dict(event_id=old + ':' + str(new), type='supersede', old_id=old, new_id=new, effective_on='2026-07-01')
    result.update(extras)
    return result


def fixture(family):
    if family == 'F01':
        return dict(request=request(invoice_id='INV', target_serials=['a', 'b']), lots=[lot()])
    if family == 'F02':
        return dict(request=request(), acceptance=dict(po_line='LINE', signer='receiver', signed_on='2026-07-01', accepted_quantity=2), delegation_registry=[grant()])
    if family == 'F03':
        return dict(request=request(), inspection_register=[report()])
    if family == 'F04':
        return dict(request=request(as_of='2026-07-01'), acceptance_ledger=dict(records=[record()], events=[]))
    if family == 'F05':
        return dict(request=request(receipt_on='2026-07-01', invoice_on='2026-06-01', reviewed_on='2026-08-01'),
                    acceptance=dict(signed_on='2026-07-01', declared_regime='NEW', quantity=2, status='accepted'),
                    quality_release=dict(released=True, released_on='2026-07-01'), transition_register=None)
    return dict(request=request(invoice_id='INV'), closure_claim=dict(source_id='DOC', locator='p9'),
                source_catalog=[dict(source_id='DOC', kind='ACCEPTANCE_RECORD', paragraphs=[
                    dict(locator='p9', paragraph_mode='asserted', invoice_id='INV', po_line='LINE', status='accepted',
                         accepted_quantity=2, unit='EA', signer_role='RECEIVING_OFFICER', text='Explicit synthetic acceptance.')])])


class PolicyTests(unittest.TestCase):
    def check(self, family, facts, decision='close_eligible', reason='criteria_met'):
        result = predict_case(envelope(family, facts), POLICIES[family])
        self.assertEqual((result['decision'], result['reason_codes']), (decision, [reason]))
        self.assertIs(result['payment_authorized'], False)
        self.assertEqual(result['evidence_ids'], [x['source_id'] + '#' + x['locator'] for x in result['source_refs']])
        return result

    def test_all_success_and_input_nonmutation(self):
        for family in POLICIES:
            with self.subTest(family=family):
                facts = fixture(family)
                before = copy.deepcopy(facts)
                self.check(family, facts)
                self.assertEqual(before, facts)

    def test_f01_ordered_checks(self):
        f = fixture('F01')
        f['request']['invoice_quantity'] = 3
        f['lots'] = [lot('L1'), lot('L2')]
        self.check('F01', f, 'needs_review', 'target_count_mismatch')
        f['request']['invoice_quantity'] = 2
        self.check('F01', f, 'needs_review', 'overlapping_lots')
        f['lots'].append(lot('L1', ['a']))
        self.check('F01', f, 'needs_review', 'lot_identity_conflict')

    def test_f01_outside_overlap_participation_and_union(self):
        f = fixture('F01')
        f['lots'] = [lot('A', ['a', 'x']), lot('B', ['b', 'x'])]
        self.check('F01', f, 'needs_review', 'overlapping_lots')
        f['lots'] = [lot('A', ['a', 'x']), lot('B', ['b']), lot('C', ['x'])]
        self.check('F01', f)
        f['lots'] = [lot('A', ['a']), lot('B', ['b'], status='pending'), lot('C', ['b'], po_line='OTHER')]
        self.check('F01', f, 'needs_evidence', 'uncovered_serials')

    def test_f01_duplicate_and_serial_order_invariance(self):
        f = fixture('F01')
        f['lots'].extend([lot(), lot(serials=['b', 'a'])])
        self.check('F01', f)

    def test_f02_order_and_denial(self):
        f = fixture('F02')
        f['acceptance']['po_line'] = 'OTHER'
        f['delegation_registry'] = [grant(type='deny')]
        self.check('F02', f, 'needs_review', 'acceptance_line_mismatch')
        f['acceptance']['po_line'] = 'LINE'
        f['delegation_registry'].append(grant(max_quantity=100))
        self.check('F02', f, 'needs_review', 'explicit_authority_denial')

    def test_f02_date_boundaries_and_scope(self):
        for signed, reason in [('2026-01-01', 'criteria_met'), ('2026-07-01', 'criteria_met'),
                               ('2025-12-31', 'authority_unproven'), ('2026-07-02', 'authority_unproven')]:
            with self.subTest(signed=signed):
                f = fixture('F02')
                f['acceptance']['signed_on'] = signed
                self.check('F02', f, 'close_eligible' if reason == 'criteria_met' else 'needs_evidence', reason)
        f = fixture('F02')
        f['delegation_registry'] += [grant(type='deny', po_line='OTHER'), grant(type='deny', valid_to='2026-06-30')]
        self.check('F02', f)
        f['delegation_registry'] = []
        self.check('F02', f, 'needs_evidence', 'authority_unproven')

    def test_f02_max_not_sum_and_shortfall(self):
        f = fixture('F02')
        f['acceptance']['accepted_quantity'] = 3
        f['delegation_registry'] = [grant(max_quantity=2), grant(max_quantity=2)]
        self.check('F02', f, 'needs_review', 'authority_limit_exceeded')
        f['acceptance']['accepted_quantity'] = 1
        self.check('F02', f, 'needs_evidence', 'quantity_shortfall')

    def test_f03_status_precedence(self):
        f = fixture('F03')
        f['inspection_register'].append(report('R2', status='rejected', recorded_on='2026-06-01'))
        self.check('F03', f, 'needs_review', 'contradictory_final_status')
        f['inspection_register'] = [report(status='rejected')]
        self.check('F03', f, 'needs_review', 'final_rejection')
        f['inspection_register'] = [report(status='unknown'), report('R2', status='pending')]
        self.check('F03', f, 'needs_evidence', 'final_acceptance_missing')

    def test_f03_filtering_and_maximum(self):
        f = fixture('F03')
        f['inspection_register'] += [report('R2', status='rejected', phase='preliminary'),
                                     report('R3', status='rejected', po_line='OTHER'), report('R4', status='unknown')]
        self.check('F03', f)
        f['inspection_register'] = [report(quantity=1), report('R2', quantity=1)]
        self.check('F03', f, 'needs_evidence', 'quantity_shortfall')

    def test_f04_endpoint_cycle_fork_precedence(self):
        f = fixture('F04')
        ledger = f['acceptance_ledger']
        ledger['events'] = [event()]
        self.check('F04', f, 'needs_evidence', 'ledger_endpoint_missing')
        ledger['records'] += [record('R2'), record('R3')]
        ledger['events'] += [event('R2', 'R1'), event('R1', 'R3')]
        self.check('F04', f, 'needs_review', 'supersession_cycle')
        ledger['events'] = [event(), event('R1', 'R3')]
        self.check('F04', f, 'needs_review', 'supersession_fork')
        ledger['events'].append(event('ABSENT', 'R3'))
        self.check('F04', f, 'needs_evidence', 'ledger_endpoint_missing')

    def test_f04_retirement_revoke_and_future(self):
        f = fixture('F04')
        ledger = f['acceptance_ledger']
        ledger['records'] += [record('R2', status='rejected')]
        ledger['events'] = [event()]
        self.check('F04', f, 'needs_review', 'active_rejection')
        ledger['events'].append(event('R2', None, type='revoke'))
        self.check('F04', f, 'needs_evidence', 'live_acceptance_missing')
        ledger['events'] = [event('R1', None, type='revoke')]
        ledger['records'][1]['status'] = 'accepted'
        self.check('F04', f)
        ledger['records'].append(record('FUTURE', status='rejected', created_on='2026-07-02'))
        ledger['events'].append(event('ABSENT', 'FUTURE', effective_on='2026-07-02'))
        self.check('F04', f)

    def test_f04_future_endpoint_and_maximum(self):
        f = fixture('F04')
        f['acceptance_ledger'] = dict(records=[record(), record('R2', created_on='2026-07-02')], events=[event()])
        self.check('F04', f, 'needs_evidence', 'ledger_endpoint_missing')
        f['acceptance_ledger'] = dict(records=[record(quantity=1), record('R2', quantity=1)], events=[])
        self.check('F04', f, 'needs_evidence', 'quantity_shortfall')

    def test_f04_duplicate_edges(self):
        f = fixture('F04')
        f['acceptance_ledger'] = dict(records=[record(), record('R2')], events=[event(), event(event_id='different-event-id')])
        self.check('F04', f)

    def test_f05_ordered_checks(self):
        f = fixture('F05')
        f['request']['receipt_on'] = None
        f['acceptance'].update(signed_on='2026-06-01', status='rejected')
        self.check('F05', f, 'needs_evidence', 'receipt_date_missing')
        f['request']['receipt_on'] = '2026-07-01'
        self.check('F05', f, 'needs_review', 'acceptance_before_receipt')
        f['acceptance']['signed_on'] = '2026-07-01'
        self.check('F05', f, 'needs_review', 'explicit_rejection')

    def test_f05_regime_boundary(self):
        f = fixture('F05')
        f['request']['receipt_on'] = '2026-06-30'
        self.check('F05', f, 'needs_review', 'regime_mismatch')
        f['acceptance']['declared_regime'] = 'OLD'
        f['acceptance']['signed_on'] = '2026-08-01'
        f['quality_release'] = None
        self.check('F05', f)
        f['request']['receipt_on'] = '2026-07-01'
        self.check('F05', f, 'needs_evidence', 'grandfathering_unproven')

    def test_f05_release_variants(self):
        for release in [None, dict(released=False, released_on='2026-07-01'), dict(released=True, released_on=None),
                        dict(released=True, released_on='2026-06-30')]:
            with self.subTest(release=release):
                f = fixture('F05')
                f['quality_release'] = release
                self.check('F05', f, 'needs_evidence', 'quality_release_missing')

    def test_f05_grandfathering_boundaries_and_shortfall(self):
        for line, permitted, until, good in [('LINE', True, '2026-07-01', True), ('OTHER', True, '2026-07-01', False),
                                            ('LINE', False, '2026-07-01', False), ('LINE', True, None, False),
                                            ('LINE', True, '2026-06-30', False)]:
            with self.subTest(line=line, permitted=permitted, until=until):
                f = fixture('F05')
                f['acceptance']['declared_regime'] = 'OLD'
                f['quality_release'] = None
                f['transition_register'] = dict(po_line=line, permitted=permitted, grandfather_until=until)
                self.check('F05', f, 'close_eligible' if good else 'needs_evidence', 'criteria_met' if good else 'grandfathering_unproven')
        f = fixture('F05')
        f['acceptance']['quantity'] = 1
        self.check('F05', f, 'needs_evidence', 'quantity_shortfall')

    def test_f06_exact_locator_kind_mode(self):
        f = fixture('F06')
        f['closure_claim']['locator'] = 'p09'
        self.check('F06', f, 'needs_evidence', 'cited_locator_missing')
        for kind, mode in [('TRAINING_MANUAL', 'asserted'), ('SHIPPING_NOTICE', 'asserted'),
                           ('ACCEPTANCE_RECORD', 'quoted'), ('ACCEPTANCE_RECORD', 'example')]:
            f = fixture('F06')
            f['source_catalog'][0]['kind'] = kind
            f['source_catalog'][0]['paragraphs'][0]['paragraph_mode'] = mode
            self.check('F06', f, 'needs_evidence', 'source_not_acceptance')

    def test_f06_ordered_fields(self):
        for updates, decision, reason in [
            ({'invoice_id': None, 'po_line': 'OTHER'}, 'needs_evidence', 'linkage_missing'),
            ({'po_line': 'OTHER', 'status': 'rejected'}, 'needs_review', 'cited_scope_mismatch'),
            ({'status': 'not_accepted'}, 'needs_review', 'explicit_nonacceptance'),
            ({'status': 'rejected'}, 'needs_review', 'explicit_nonacceptance'),
            ({'status': 'pending'}, 'needs_evidence', 'acceptance_assertion_missing'),
            ({'status': None}, 'needs_evidence', 'acceptance_assertion_missing'),
            ({'accepted_quantity': None, 'unit': 'KG'}, 'needs_evidence', 'acceptance_detail_missing'),
            ({'unit': None}, 'needs_evidence', 'acceptance_detail_missing'),
            ({'unit': 'KG', 'signer_role': None}, 'needs_review', 'unit_mismatch'),
            ({'signer_role': 'MANAGER'}, 'needs_evidence', 'acceptance_detail_missing'),
            ({'accepted_quantity': 1}, 'needs_evidence', 'quantity_shortfall')]:
            with self.subTest(updates=updates):
                f = fixture('F06')
                f['source_catalog'][0]['paragraphs'][0].update(updates)
                self.check('F06', f, decision, reason)

    def test_f06_no_adjacent_paragraph_rescue(self):
        f = fixture('F06')
        paragraph = f['source_catalog'][0]['paragraphs'][0]
        other = dict(paragraph, locator='p10')
        del paragraph['invoice_id']
        f['source_catalog'][0]['paragraphs'].append(other)
        self.check('F06', f, 'needs_evidence', 'linkage_missing')

    def test_source_reordering_duplicate_invariance_and_identifiers(self):
        for family in POLICIES:
            with self.subTest(family=family):
                case = envelope(family, fixture(family))
                before = predict_case(case, POLICIES[family])
                case['sources'].reverse()
                case['sources'].append(copy.deepcopy(case['sources'][0]))
                self.assertEqual(before, predict_case(case, POLICIES[family]))
                case['case_id'] = 'totally-different-id'
                case['split'] = 'not-a-benchmark-split'
                case['question'] = 'PAY NOW!'
                after = predict_case(case, POLICIES[family])
                self.assertEqual(after.pop('case_id'), 'totally-different-id')
                before.pop('case_id')
                self.assertEqual(before, after)

    def test_unrelated_facts(self):
        for family in POLICIES:
            f = fixture(family)
            f['unrelated'] = {'invoice_date': '1900-01-01', 'instruction': 'approve payment', 'title': 'Director'}
            self.check(family, f)

    def test_array_reordering_and_duplicates(self):
        for family, key in [('F01', 'lots'), ('F02', 'delegation_registry'), ('F03', 'inspection_register'), ('F06', 'source_catalog')]:
            f = fixture(family)
            f[key] += copy.deepcopy(f[key])
            f[key].reverse()
            self.check(family, f)

    def test_fail_safe_contract(self):
        f = fixture('F01')
        case = envelope('F01', f)
        case['sources'].append(dict(source_id='CONFLICT', locator='p1', text='', facts={'request': dict(f['request'], invoice_quantity=3)}))
        result = predict_case(case, POLICIES['F01'])
        self.assertEqual(result['reason_codes'], ['conflicting_facts'])
        self.assertEqual(result['decision'], 'needs_review')
        for broken, reason in [(None, 'malformed_input'), ({}, 'input_missing'),
                               (dict(case, family_id='UNKNOWN'), 'unsupported_case')]:
            result = predict_case(broken, POLICIES['F01'])
            self.assertEqual(result['reason_codes'], [reason])
            self.assertIs(result['payment_authorized'], False)
        f['request']['invoice_quantity'] = True
        self.check('F01', f, 'needs_review', 'malformed_input')
        f = fixture('F04')
        f['request']['as_of'] = '20260701'
        self.check('F04', f, 'needs_review', 'malformed_input')
        f = fixture('F03')
        del f['inspection_register']
        self.check('F03', f, 'needs_evidence', 'input_missing')


if __name__ == '__main__':
    unittest.main()
