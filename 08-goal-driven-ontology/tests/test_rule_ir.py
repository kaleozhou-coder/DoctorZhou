"""Implementation-authored probes only; no evaluator inputs or labels imported."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rule_ir import evaluate, loads, validate, predict_case, RuleError
ROOT = Path(__file__).resolve().parents[1]


class RuleIRTests(unittest.TestCase):
    def setUp(self):
        self.p = loads((ROOT / 'ontology/ir-reference/F05.json').read_text())
        self.f = {'request': {'po_line': 'probe-line', 'invoice_quantity': 2, 'receipt_on': '2026-06-30'},
                  'acceptance': {'signed_on': '2026-07-02', 'status': 'accepted', 'declared_regime': 'OLD', 'quantity': 2}}
    def assertResult(self, decision, reason):
        out = evaluate(self.p, self.f)
        self.assertEqual((out['decision'], out['reason_codes']), (decision, [reason]))
        self.assertIs(out['payment_authorized'], False)
    def test_reference_valid(self): self.assertTrue(validate(self.p)['valid'])
    def test_old_closes(self): self.assertResult('close_eligible', 'criteria_met')
    def test_null_receipt(self):
        self.f['request']['receipt_on'] = None
        self.assertResult('needs_evidence', 'receipt_date_missing')
    def test_missing_receipt(self):
        del self.f['request']['receipt_on']
        self.assertResult('needs_evidence', 'receipt_date_missing')
    def test_order(self):
        self.f['acceptance'].update(signed_on='2026-06-29', status='rejected')
        self.assertResult('needs_review', 'acceptance_before_receipt')
    def test_rejection(self):
        self.f['acceptance']['status'] = 'rejected'
        self.assertResult('needs_review', 'explicit_rejection')
    def test_mismatch(self):
        self.f['acceptance']['declared_regime'] = 'NEW'
        self.assertResult('needs_review', 'regime_mismatch')
    def test_boundary_release(self):
        self.f['request']['receipt_on'] = '2026-07-01'
        self.f['acceptance']['declared_regime'] = 'NEW'
        self.assertResult('needs_evidence', 'quality_release_missing')
        self.f['quality_release'] = {'released': True, 'released_on': '2026-07-01'}
        self.assertResult('close_eligible', 'criteria_met')
    def test_false_release(self):
        self.f['request']['receipt_on'] = '2026-07-01'
        self.f['acceptance']['declared_regime'] = 'NEW'
        self.f['quality_release'] = {'released': False, 'released_on': '2026-07-01'}
        self.assertResult('needs_evidence', 'quality_release_missing')
    def test_grandfather(self):
        self.f['request']['receipt_on'] = '2026-07-01'
        self.assertResult('needs_evidence', 'grandfathering_unproven')
        self.f['transition_register'] = {'po_line': 'probe-line', 'permitted': True, 'grandfather_until': '2026-07-01'}
        self.assertResult('close_eligible', 'criteria_met')
    def test_transition_wrong_line(self):
        self.f['request']['receipt_on'] = '2026-07-01'
        self.f['transition_register'] = {'po_line': 'other', 'permitted': True, 'grandfather_until': '2026-07-01'}
        self.assertResult('needs_evidence', 'grandfathering_unproven')
    def test_shortfall(self):
        self.f['acceptance']['quantity'] = 1
        self.assertResult('needs_evidence', 'quantity_shortfall')
    def test_unknown_first_blocks_later(self):
        del self.f['acceptance']['signed_on']
        self.f['acceptance']['status'] = 'rejected'
        self.assertResult('needs_evidence', 'condition_unknown')
    def test_unknown_quantity_never_closes(self):
        del self.f['acceptance']['quantity']
        self.assertResult('needs_evidence', 'condition_unknown')
    def test_bool_not_integer(self):
        self.f['acceptance']['quantity'] = True
        self.assertResult('needs_review', 'malformed_input')
    def test_invalid_date(self):
        self.f['request']['receipt_on'] = '2026-02-30'
        self.assertResult('needs_review', 'malformed_input')
    def test_invalid_enum(self):
        self.f['acceptance']['status'] = 'unknown-status'
        self.assertResult('needs_review', 'malformed_input')
    def test_wrong_parent(self):
        self.f['request'] = []
        self.assertResult('needs_review', 'malformed_input')
    def test_no_default_close(self):
        self.p['default']['decision'] = 'close_eligible'
        self.assertResult('needs_review', 'invalid_artifact')
    def test_no_arbitrary_operator(self):
        self.p['rules'][0]['when'] = {'op': 'eval', 'code': '__import__("os")'}
        self.assertResult('needs_review', 'invalid_artifact')
    def test_no_extra_keys(self):
        self.p['family_id'] = 'F05'
        self.assertResult('needs_review', 'invalid_artifact')
    def test_incompatible_types(self):
        self.p['rules'][1]['when']['right'] = {'op': 'literal', 'type': 'integer', 'value': 2}
        self.assertResult('needs_review', 'invalid_artifact')
    def test_duplicate_rule_id(self):
        self.p['rules'][1]['id'] = self.p['rules'][0]['id']
        self.assertResult('needs_review', 'invalid_artifact')
    def test_bad_source_ref(self):
        with self.assertRaises(RuleError): validate(self.p, set())
    def test_locator_validation(self):
        refs = {('F05-POL', 'p%02d' % n) for n in range(1, 8)}
        self.assertTrue(validate(self.p, refs)['locator_existence_checked'])
    def test_duplicate_json(self):
        with self.assertRaises(RuleError): loads('{"a":1,"a":2}')
    def test_truncated_json(self):
        with self.assertRaises(RuleError): loads('{"a":')
    def test_nonfinite_json(self):
        for s in ('NaN', 'Infinity', '1e999'):
            with self.subTest(s=s), self.assertRaises(RuleError): loads(s)
    def test_deep_ast(self):
        n = {'op': 'literal', 'type': 'boolean', 'value': True}
        for _ in range(25): n = {'op': 'not', 'arg': n}
        self.p['rules'][0]['when'] = n
        self.assertResult('needs_review', 'invalid_artifact')
    def test_large_input(self):
        self.f['extra'] = 'x' * 140000
        self.assertResult('needs_review', 'malformed_input')
    def test_deep_input(self):
        node = self.f
        for _ in range(40): node['x'] = {}; node = node['x']
        self.assertResult('needs_review', 'malformed_input')
    def test_cyclic_python_input(self):
        self.f['cycle'] = self.f
        self.assertResult('needs_review', 'malformed_input')
    def test_kleene_truth_tables(self):
        self.p['fields']['probe'] = {'path': ['absent'], 'type': 'boolean'}
        unknown = {'op': 'field', 'name': 'probe'}
        for op, known, expected in [('all', False, False), ('all', True, 'unknown'), ('any', True, True), ('any', False, 'unknown')]:
            self.p['rules'][0]['when'] = {'op': op, 'args': [unknown, {'op':'literal','type':'boolean','value':known}]}
            out = evaluate(self.p, self.f)
            self.assertEqual(out['trace'][0]['value'], expected)
    def test_adapter(self):
        materials = json.loads((ROOT / 'benchmark/v1/model-facing/F05/materials.json').read_text())
        case = {'case_id':'probe-only','policy_source_id':'F05-POL','sources':[{'source_id':'probe', 'locator':'body','facts':self.f}]}
        out = predict_case(case, self.p, materials)
        self.assertEqual(out['decision'], 'close_eligible')
        self.assertIn('probe#body', out['evidence_ids'])
        case['sources'].append({'source_id':'conflict','locator':'body','facts':{'request':{}}})
        self.assertEqual(predict_case(case, self.p, materials)['reason_codes'], ['invalid_transport'])
    def test_surrogate_program(self):
        self.p['extra'] = '\ud800'
        self.assertResult('needs_review', 'invalid_artifact')
    def test_huge_integer_program(self):
        self.p['extra'] = 10**5000
        self.assertResult('needs_review', 'invalid_artifact')
    def test_surrogate_json(self):
        with self.assertRaises(RuleError): loads('\ud800')
        with self.assertRaises(RuleError): loads('"\\ud800"')
    def test_surrogate_facts(self):
        self.f['extra'] = '\ud800'
        self.assertResult('needs_review', 'malformed_input')
    def test_determinism(self): self.assertEqual(evaluate(self.p,self.f), evaluate(copy.deepcopy(self.p),copy.deepcopy(self.f)))

if __name__ == '__main__': unittest.main()
