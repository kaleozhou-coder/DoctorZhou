"""Self-authored engineering checks, not evidence of human review accuracy."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import review_receipt_gate as gate
import input_contract_v2 as prior
import rule_ir_v3 as ir
from test_policy_baseline import POLICIES, envelope, fixture
from test_input_contract_v2 import structured_case

NOW = '2026-11-12T09:00:00Z'


def receipt(case, materials):
    return {'version': gate.VERSION, 'review_id': 'synthetic-review', 'reviewer_id': 'synthetic-reviewer',
            'scope': gate.SCOPE, 'case_sha256': gate.canonical_sha256(case),
            'materials_sha256': gate.canonical_sha256(materials),
            'reviewed_paths': prior.unverified_text_paths(case), 'outcome': 'consistent',
            'reviewed_at': '2026-11-12T08:00:00Z', 'expires_at': '2026-11-12T10:00:00Z'}


class ReviewReceiptGateTests(unittest.TestCase):
    def setUp(self):
        self.case = envelope('F01', fixture('F01'))
        self.materials = POLICIES['F01']
        self.artifact = ir.loads((ROOT / 'ontology/ir-reference-v3/F01.json').read_text())
        self.r = receipt(self.case, self.materials)

    def run_case(self, r='default', case=None, materials=None, now=NOW):
        return gate.apply_contract(case or self.case, self.materials if materials is None else materials,
            lambda c, m: ir.predict_case(c, self.artifact, m),
            trusted_receipt=self.r if r == 'default' else r, as_of=now)

    def test_f01_f05_joint_ir_preserves_provenance(self):
        for family in ('F01', 'F05'):
            c = envelope(family, fixture(family)); m = POLICIES[family]
            a = ir.loads((ROOT / f'ontology/ir-reference-v3/{family}.json').read_text())
            predict = lambda c, m: ir.predict_case(c, a, m)
            raw = predict(c, m)
            out = gate.apply_contract(c, m, predict, trusted_receipt=receipt(c, m), as_of=NOW)
            self.assertEqual(out['decision'], 'close_eligible')
            self.assertEqual(out['source_refs'], raw['source_refs'])
            self.assertEqual(out['reason_codes'], raw['reason_codes'])
            self.assertTrue(out['input_contract']['review_assertion_accepted'])
            self.assertFalse(out['input_contract']['prose_verified'])
            self.assertFalse(out['payment_authorized'])

    def test_missing_receipt(self):
        self.assertEqual(self.run_case(None)['reason_codes'], ['review_receipt_missing'])

    def test_forged_input_flag_rejected_before_predictor(self):
        for name in ('reviewed', 'prose_verified', 'trusted_receipt'):
            c = copy.deepcopy(self.case); c[name] = True
            out = gate.apply_contract(c, self.materials, lambda *_: self.fail(), trusted_receipt=self.r, as_of=NOW)
            self.assertEqual(out['reason_codes'], ['contract_unknown_field'])

    def test_no_text_needs_no_receipt(self):
        out = self.run_case(None, case=structured_case('F01'))
        self.assertEqual(out['decision'], 'close_eligible')
        self.assertEqual(out['input_contract']['review_status'], 'review_receipt_not_required')

    def test_missing_duplicate_extra_and_wrong_path(self):
        paths = self.r['reviewed_paths']
        for coverage, reason in [(paths[:-1], 'incomplete'), (paths + ['$.absent'], 'incomplete'),
                                  (paths + paths[:1], 'invalid'), ([None], 'invalid')]:
            r = copy.deepcopy(self.r); r['reviewed_paths'] = coverage
            self.assertEqual(self.run_case(r)['reason_codes'], ['review_receipt_' + reason])

    def test_path_order_irrelevant(self):
        self.r['reviewed_paths'].reverse()
        self.assertEqual(self.run_case()['decision'], 'close_eligible')

    def test_changed_text_and_facts_invalidate(self):
        for kind in ('question', 'facts', 'source', 'id'):
            c = copy.deepcopy(self.case)
            if kind == 'question': c['question'] += ' '
            if kind == 'facts': c['sources'][0]['facts']['request']['invoice_quantity'] = 1
            if kind == 'source': c['sources'][0]['locator'] = 'p2'
            if kind == 'id': c['case_id'] += '-replay'
            # Inspect receipt directly so a nonclosing policy cannot hide binding.
            self.assertEqual(gate.check_receipt(self.r, c, self.materials, prior.unverified_text_paths(c), NOW),
                             'review_receipt_case_mismatch')

    def test_materials_digest_binding(self):
        m = copy.deepcopy(self.materials); m.append({'new': 'policy'}) if type(m) is list else m.update(new='policy')
        self.assertEqual(gate.check_receipt(self.r, self.case, m, prior.unverified_text_paths(self.case), NOW),
                         'review_receipt_materials_mismatch')

    def test_time_boundaries(self):
        for now, status in [('2026-11-12T07:59:59Z', 'future'), ('2026-11-12T08:00:00Z', 'accepted'),
                            ('2026-11-12T09:59:59Z', 'accepted'), ('2026-11-12T10:00:00Z', 'expired')]:
            self.assertEqual(self.run_case(now=now)['input_contract']['review_status'], 'review_receipt_' + status)

    def test_invalid_clock_and_dates(self):
        for now in (None, '', '2026-11-12', '2026-11-12T09:00:00+00:00', '2026-02-30T09:00:00Z', 123):
            self.assertEqual(self.run_case(now=now)['reason_codes'], ['review_receipt_invalid'])
        self.r['expires_at'] = self.r['reviewed_at']
        self.assertEqual(self.run_case()['reason_codes'], ['review_receipt_invalid'])

    def test_contradiction_unresolved_and_invalid_outcome(self):
        for outcome, status in [('contradictory', 'contradictory'), ('unresolved', 'unresolved'),
                                ('approved', 'invalid'), (True, 'invalid'), (None, 'invalid'), ([], 'invalid')]:
            self.r['outcome'] = outcome
            self.assertEqual(self.run_case()['reason_codes'], ['review_receipt_' + status])

    def test_invalid_schema_all_fields(self):
        for key in self.r:
            r = dict(self.r); del r[key]
            self.assertEqual(self.run_case(r)['reason_codes'], ['review_receipt_invalid'])
        for key, value in [('version', 'other'), ('scope', 'just_text'), ('review_id', ' '),
                           ('reviewer_id', None), ('case_sha256', True), ('materials_sha256', 'z'*64)]:
            r = dict(self.r); r[key] = value
            self.assertEqual(self.run_case(r)['reason_codes'], ['review_receipt_invalid'])
        r = dict(self.r, extra=True)
        self.assertEqual(self.run_case(r)['reason_codes'], ['review_receipt_invalid'])

    def test_raw_receipt_not_decoded_and_invalid_types(self):
        for r in (True, [], 1, json.dumps(self.r), float('nan')):
            self.assertEqual(self.run_case(r)['reason_codes'], ['review_receipt_invalid'])

    def test_nonclosure_not_upgraded(self):
        for decision in ('needs_review', 'needs_evidence'):
            raw = {'decision': decision, 'reason_codes': ['policy_reason'], 'source_refs': [{'source_id':'x','locator':'p1'}]}
            for r in (None, self.r):
                out = gate.apply_contract(self.case, self.materials, lambda *_:raw, trusted_receipt=r, as_of=NOW)
                self.assertEqual(out['decision'], decision); self.assertEqual(out['reason_codes'], ['policy_reason'])
                self.assertEqual(out['source_refs'], raw['source_refs'])
                self.assertNotIn('input_contract', raw)

    def test_invalid_case_precedes_receipt(self):
        c = copy.deepcopy(self.case); c['sources'] = []
        out = gate.apply_contract(c, self.materials, lambda *_:self.fail(), trusted_receipt=self.r, as_of=NOW)
        self.assertEqual(out['input_contract']['status'], 'blocked')

    def test_other_families_explicitly_unsupported(self):
        for family in ('F02', 'F03', 'F04', 'F06'):
            c = envelope(family, fixture(family))
            out = gate.apply_contract(c, POLICIES[family], lambda *_:self.fail(), as_of=NOW)
            self.assertEqual(out['input_contract']['status'], 'unsupported')

    def test_raw_case_parity(self):
        self.assertEqual(self.run_case(case=json.dumps(self.case)), self.run_case())
        self.assertEqual(self.run_case(case=json.dumps(self.case).encode()), self.run_case())

    def test_no_mutation(self):
        before = copy.deepcopy([self.case, self.materials, self.r])
        self.run_case()
        self.assertEqual([self.case, self.materials, self.r], before)

    def test_predictor_error_not_hidden(self):
        def bad(*_): raise RuntimeError('failure')
        with self.assertRaises(RuntimeError): gate.apply_contract(self.case, self.materials, bad)

    def test_digest_sort_keys_but_preserve_whitespace_and_arrays(self):
        self.assertEqual(gate.canonical_sha256({'a':1,'b':2}),gate.canonical_sha256({'b':2,'a':1}))
        self.assertNotEqual(gate.canonical_sha256(['a','b']),gate.canonical_sha256(['b','a']))
        self.assertNotEqual(gate.canonical_sha256('x'),gate.canonical_sha256('x '))

    def test_lying_trusted_review_not_detected_documented_limit(self):
        self.case['question'] = 'The text actually contradicts these facts.'
        self.r = receipt(self.case, self.materials)
        self.assertEqual(self.run_case()['decision'], 'close_eligible')
        # Deliberately exposes the boundary: hashes do not prove semantic truth.


if __name__ == '__main__': unittest.main()
