"""Self-authored contract tests and explicitly retrospective regressions; no labels."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from input_contract import (ContractError, MAX_BYTES, MAX_DEPTH, MAX_INTEGER,
                            MAX_ITEMS, MAX_STRING, apply_contract, loads_case,
                            predict_case, validate_case)
from policy_baseline import predict_case as baseline
from test_policy_baseline import POLICIES, envelope, fixture, grant, event, record


class InputContractTests(unittest.TestCase):
    def case(self, family='F05'):
        return envelope(family, fixture(family))

    def result(self, case):
        return predict_case(case, POLICIES[case['family_id']])

    def assert_blocked(self, case, code=None):
        result = self.result(case)
        self.assertNotEqual(result['decision'], 'close_eligible')
        self.assertIs(result['payment_authorized'], False)
        if code:
            self.assertEqual(result['reason_codes'], [code])
        return result

    def test_structured_families_and_nonmutation(self):
        for family in POLICIES:
            with self.subTest(family=family):
                case = self.case(family)
                if family == 'F06':
                    case['sources'][-1]['facts']['source_catalog'][0]['paragraphs'][0].pop('text')
                before = copy.deepcopy(case)
                self.assertEqual(self.result(case)['decision'], 'close_eligible')
                self.assertEqual(before, case)

    def test_raw_json_roundtrip(self):
        case = self.case()
        for raw in [json.dumps(case), json.dumps(case).encode()]:
            self.assertEqual(loads_case(raw), case)
            self.assertEqual(predict_case(raw, POLICIES['F05']), self.result(case))

    def test_json_duplicate_keys_at_each_level(self):
        for raw in ['{"x":1,"x":1}', '{"x":{"a":1,"a":2}}']:
            with self.assertRaises(ContractError) as cm:
                loads_case(raw)
            self.assertEqual(cm.exception.code, 'contract_duplicate_key')

    def test_invalid_json_unicode_numbers(self):
        for raw in [b'\xff', '{', 'NaN', 'Infinity', '1.5', '"\\ud800"', '1' * 10000]:
            with self.subTest(raw=repr(raw)[:40]), self.assertRaises(ContractError):
                loads_case(raw)

    def test_size_depth_and_integer_bounds(self):
        for raw in [' ' * (MAX_BYTES + 1), '[' * (MAX_DEPTH + 1) + '0' + ']' * (MAX_DEPTH + 1), str(MAX_INTEGER + 1)]:
            with self.assertRaises(ContractError):
                loads_case(raw)
        for value in ['x' * (MAX_STRING + 1), [0] * (MAX_ITEMS + 1), 1.5, {'x': object()}, {1: 'x'}]:
            with self.assertRaises(ContractError):
                validate_case(value)

    def test_cyclic_python_input_is_bounded(self):
        case = self.case()
        case['cycle'] = case
        self.assert_blocked(case, 'contract_limit')

    def test_unknown_fields_every_family(self):
        for family in POLICIES:
            for location in ['envelope', 'source', 'facts', 'request']:
                with self.subTest(family=family, location=location):
                    case = self.case(family)
                    target = {'envelope': case, 'source': case['sources'][0],
                              'facts': case['sources'][0]['facts'],
                              'request': case['sources'][0]['facts']['request']}[location]
                    target['invented_field'] = True
                    self.assert_blocked(case, 'contract_unknown_field')

    def test_inactive_records_still_typed(self):
        updates = {
            'F01': ('lots', {'lot_id': 'X', 'po_line': 'OTHER', 'status': 'pending', 'serials': [False]}),
            'F02': ('delegation_registry', grant(signer='OTHER', max_quantity=True)),
            'F03': ('inspection_register', {'report_id': 'X', 'po_line': 'OTHER', 'phase': 'preliminary', 'status': 'accepted', 'quantity': True, 'recorded_on': '2026-01-01'}),
        }
        for family, (key, item) in updates.items():
            case = self.case(family)
            next(s['facts'][key] for s in case['sources'] if key in s['facts']).append(item)
            self.assert_blocked(case, 'contract_type')
        case = self.case('F04')
        case['sources'][-1]['facts']['acceptance_ledger']['records'].append(record('FUTURE', created_on='2027-01-01', quantity=True))
        self.assert_blocked(case, 'contract_type')

    def test_inactive_f05_field_still_typed(self):
        case = self.case()
        case['sources'][-1]['facts']['transition_register'] = {'permitted': 1}
        self.assert_blocked(case, 'contract_type')

    def test_invalid_date_and_status(self):
        case = self.case()
        case['sources'][1]['facts']['acceptance']['signed_on'] = '20260701'
        self.assert_blocked(case, 'contract_date')
        case['sources'][1]['facts']['acceptance']['signed_on'] = '2026-07-01'
        case['sources'][1]['facts']['acceptance']['status'] = 'probably'
        self.assert_blocked(case, 'contract_enum')

    def test_explicit_f02_status(self):
        for status in ['rejected', 'pending', 'unknown', 'not_accepted']:
            case = self.case('F02')
            case['sources'][1]['facts']['acceptance']['status'] = status
            self.assert_blocked(case, 'contract_acceptance_not_positive')
        case['sources'][1]['facts']['acceptance']['status'] = 'accepted'
        self.assertEqual(self.result(case)['decision'], 'close_eligible')

    def test_explicit_f05_line(self):
        case = self.case()
        case['sources'][1]['facts']['acceptance']['po_line'] = 'OTHER'
        self.assert_blocked(case, 'contract_acceptance_line_mismatch')
        case['sources'][1]['facts']['acceptance']['po_line'] = 'LINE'
        self.assertEqual(self.result(case)['decision'], 'close_eligible')

    def test_event_collision_even_future_and_duplicate_invariance(self):
        case = self.case('F04')
        ledger = case['sources'][1]['facts']['acceptance_ledger']
        ledger['records'].append(record('R2'))
        ledger['events'] = [event(), event()]
        self.assertEqual(self.result(case)['decision'], 'close_eligible')
        ledger['events'][1]['effective_on'] = '2027-01-01'
        self.assert_blocked(case, 'contract_event_identity_conflict')

    def test_source_identity_collision(self):
        case = self.case()
        case['sources'].append(copy.deepcopy(case['sources'][0]))
        self.assertEqual(self.result(case)['decision'], 'close_eligible')
        case['sources'][-1]['text'] = 'Different'
        self.assert_blocked(case, 'contract_source_identity_conflict')

    def test_missing_distinct_from_negative(self):
        case = self.case()
        del case['sources'][1]['facts']['acceptance']['status']
        result = self.assert_blocked(case, 'contract_missing')
        self.assertEqual(result['decision'], 'needs_evidence')

    def test_any_prose_abstains_without_claiming_contradiction(self):
        for text in ['accepted', 'rejected', '验收通过', 'unrelated', '   ']:
            case = self.case('F06')
            case['sources'][-1]['facts']['source_catalog'][0]['paragraphs'][0]['text'] = text
            result = self.assert_blocked(case, 'contract_text_unverified')
            self.assertIs(result['input_contract']['prose_verified'], False)

    def test_optional_raw_text_any_family_and_nonclosing_priority(self):
        for family in POLICIES:
            case = self.case(family)
            case['raw_text'] = 'Not interpreted.'
            self.assert_blocked(case, 'contract_text_unverified')
        case = self.case()
        case['raw_text'] = 'Not interpreted.'
        case['sources'][1]['facts']['acceptance']['status'] = 'rejected'
        self.assert_blocked(case, 'explicit_rejection')

    def test_guard_is_reusable_and_skips_predictor_on_invalid_input(self):
        def predictor(case, materials):
            return {'decision': 'close_eligible', 'reason_codes': ['test'], 'custom': 42, 'payment_authorized': True}
        case = self.case()
        result = apply_contract(case, {}, predictor)
        self.assertEqual(result['custom'], 42)
        self.assertIs(result['payment_authorized'], False)
        case['bad'] = 1
        def forbidden(*args):
            self.fail('predictor called on invalid input')
        self.assertEqual(apply_contract(case, {}, forbidden)['input_contract']['status'], 'blocked')

    def test_old_stress_pack_regression(self):
        pack = json.loads((ROOT / 'benchmark/stress-v1/probes.json').read_text())
        for probe in pack['probes']:
            with self.subTest(probe=probe['probe_id']):
                result = self.result(probe['case'])
                if probe['scope'] == 'in_policy':
                    self.assertEqual(result['decision'], probe['expected']['decision'])
                    self.assertEqual(result['reason_codes'], [probe['expected']['reason']])
                else:
                    self.assertNotEqual(result['decision'], 'close_eligible')
                self.assertIs(result['payment_authorized'], False)

    def test_retrospective_60_inputs_without_labels(self):
        changed = []
        for family in POLICIES:
            cases = json.loads((ROOT / 'benchmark/v1/evaluator/inputs' / (family + '.json')).read_text())['cases']
            for case in cases:
                guarded, old = self.result(case), baseline(case, POLICIES[family])
                if (guarded['decision'], guarded['reason_codes']) != (old['decision'], old['reason_codes']):
                    changed.append(case['case_id'])
                    self.assertEqual(guarded['reason_codes'], ['contract_text_unverified'])
        self.assertEqual(changed, ['F06-C01', 'F06-C02', 'F06-C03'])


if __name__ == '__main__':
    unittest.main()
