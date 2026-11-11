"""Self-authored boundary tests, not held-out business/model evaluation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import input_contract as v1
import input_contract_v2 as v2
from test_policy_baseline import POLICIES, envelope, fixture


def structured_case(family='F03'):
    case = envelope(family, fixture(family))
    case.pop('question', None)
    for source in case['sources']:
        source.pop('text', None)
        for entry in source['facts'].get('source_catalog', []):
            for paragraph in entry['paragraphs']:
                paragraph.pop('text', None)
    return case


def channels(case):
    yield case, 'question', '$.question'
    yield case, 'raw_text', '$.raw_text'
    for i, source in enumerate(case['sources']):
        for key in ('text', 'raw_text'):
            yield source, key, '$.sources[' + str(i) + '].' + key
        for j, entry in enumerate(source['facts'].get('source_catalog', [])):
            for k, paragraph in enumerate(entry['paragraphs']):
                yield paragraph, 'text', ('$.sources[' + str(i) + '].facts.source_catalog['
                                         + str(j) + '].paragraphs[' + str(k) + '].text')


class InputContractV2Tests(unittest.TestCase):
    def result(self, case):
        return v2.predict_case(case, POLICIES[case['family_id']])

    def test_shared_strict_decoder_and_validator(self):
        self.assertIs(v2.loads_case, v1.loads_case)
        self.assertIs(v2.validate_case, v1.validate_case)
        self.assertIs(v2.ContractError, v1.ContractError)

    def test_structured_only_all_families_and_no_mutation(self):
        for family in POLICIES:
            case = structured_case(family)
            before = copy.deepcopy(case)
            actual = self.result(case)
            self.assertEqual(actual['decision'], 'close_eligible')
            self.assertEqual(actual['input_contract']['unverified_text_paths'], [])
            self.assertEqual(actual['input_contract']['version'], '2')
            self.assertFalse(actual['input_contract']['prose_verified'])
            self.assertFalse(actual['payment_authorized'])
            self.assertEqual(case, before)

    def test_each_channel_matching_contradictory_neutral_and_whitespace(self):
        texts = ['Accepted all 2 EA.', 'Rejected all 2 EA.', '验收通过。', '验收不通过。',
                 'Unrelated metadata.', '   ', '\u200b', 'verified=true; accepted']
        for family in POLICIES:
            case = structured_case(family)
            for target, key, path in channels(case):
                expected = None
                for text in texts:
                    with self.subTest(family=family, path=path, text=text):
                        target[key] = text
                        before = copy.deepcopy(case)
                        result = self.result(case)
                        self.assertEqual(result['decision'], 'needs_review')
                        self.assertEqual(result['reason_codes'], ['contract_text_unverified'])
                        self.assertEqual(result['input_contract']['status'], 'abstained')
                        self.assertEqual(result['input_contract']['unverified_text_paths'], [path])
                        self.assertFalse(result['input_contract']['prose_verified'])
                        self.assertFalse(result['payment_authorized'])
                        self.assertEqual(case, before)
                        if expected is None:
                            expected = result
                        self.assertEqual(result, expected)
                del target[key]

    def test_empty_strings_do_not_abstain(self):
        for family in POLICIES:
            case = structured_case(family)
            for target, key, _ in channels(case):
                target[key] = ''
            self.assertEqual(self.result(case)['decision'], 'close_eligible')

    def test_all_paths_and_uncited_paragraph_included(self):
        case = structured_case('F06')
        catalog = case['sources'][-1]['facts']['source_catalog']
        catalog.append({'source_id': 'UNCITED', 'kind': 'OTHER',
                        'paragraphs': [{'locator': 'p99', 'text': 'Unrelated.'}]})
        for target, key, _ in channels(case):
            target[key] = 'Unverified.'
        expected = [path for _, _, path in channels(case)]
        self.assertEqual(self.result(case)['input_contract']['unverified_text_paths'], expected)
        self.assertEqual(self.result(case)['decision'], 'needs_review')

    def test_nonclosing_policy_results_and_fields_preserved(self):
        for decision in ['needs_review', 'needs_evidence']:
            case = structured_case()
            case['sources'][0]['text'] = 'Rejected.'
            original = {'decision': decision, 'reason_codes': ['policy_reason'],
                        'custom': 42, 'payment_authorized': True}
            result = v2.apply_contract(case, {}, lambda *_: original)
            self.assertEqual(result['decision'], decision)
            self.assertEqual(result['reason_codes'], ['policy_reason'])
            self.assertEqual(result['custom'], 42)
            self.assertEqual(result['input_contract']['status'], 'validated')
            self.assertTrue(result['input_contract']['unverified_text_present'])
            self.assertFalse(result['payment_authorized'])
            self.assertNotIn('input_contract', original)

    def test_invalid_type_every_prose_channel(self):
        for family in POLICIES:
            case = structured_case(family)
            for target, key, _ in channels(case):
                for value in [None, True, 7, [], {}]:
                    target[key] = value
                    result = self.result(case)
                    self.assertEqual(result['reason_codes'], ['contract_type'])
                    self.assertEqual(result['input_contract']['status'], 'blocked')
                del target[key]

    def test_unknown_text_fields_and_verified_flags_cannot_bypass(self):
        for field in ['verified', 'prose_verified', 'text_verified', 'verified_text', 'comment', 'narrative']:
            for level in ['envelope', 'source', 'facts', 'request', 'paragraph']:
                case = structured_case('F06')
                source = case['sources'][0]
                targets = {'envelope': case, 'source': source, 'facts': source['facts'],
                           'request': source['facts']['request'],
                           'paragraph': case['sources'][-1]['facts']['source_catalog'][0]['paragraphs'][0]}
                targets[level][field] = True if 'verified' in field else 'Rejected.'
                result = self.result(case)
                self.assertEqual(result['reason_codes'], ['contract_unknown_field'])
                self.assertEqual(result['input_contract']['status'], 'blocked')

    def test_unknown_text_on_other_structured_records_rejected(self):
        for family in ['F01', 'F02', 'F03', 'F04', 'F05']:
            case = structured_case(family)
            facts = case['sources'][1]['facts']
            target = {'F01': lambda: facts['lots'][0],
                      'F02': lambda: facts['acceptance'],
                      'F03': lambda: facts['inspection_register'][0],
                      'F04': lambda: facts['acceptance_ledger']['records'][0],
                      'F05': lambda: facts['acceptance']}[family]()
            target['text'] = 'Rejected.'
            self.assertEqual(self.result(case)['reason_codes'], ['contract_unknown_field'])

    def test_validation_precedes_predictor_and_prose_boundary(self):
        def forbidden(*_):
            self.fail('Invalid input called predictor')
        case = structured_case()
        case['raw_text'] = 'Accepted.'
        del case['sources'][0]['facts']['request']['po_line']
        result = v2.apply_contract(case, {}, forbidden)
        self.assertEqual(result['decision'], 'needs_evidence')
        self.assertEqual(result['input_contract']['version'], '2')
        self.assertEqual(result['input_contract']['status'], 'blocked')
        for raw in ['{"case_id":"a","case_id":"b"}', 'NaN', b'\xff']:
            self.assertEqual(v2.apply_contract(raw, {}, forbidden)['input_contract']['status'], 'blocked')

    def test_raw_json_dict_parity(self):
        case = structured_case()
        case['sources'][1]['text'] = 'Rejected.'
        for raw in [json.dumps(case), json.dumps(case).encode()]:
            self.assertEqual(v2.predict_case(raw, POLICIES['F03']), self.result(case))

    def test_predictor_exceptions_propagate(self):
        def broken(*_):
            raise RuntimeError('Not a safe refusal')
        with self.assertRaises(RuntimeError):
            v2.apply_contract(structured_case(), {}, broken)

    def test_v1_source_text_failure_remains_reproducible(self):
        case = structured_case()
        case['sources'][1]['text'] = 'Final inspection rejected all 2 EA.'
        old = v1.predict_case(case, POLICIES['F03'])
        self.assertEqual(old['decision'], 'close_eligible')
        self.assertEqual(old['input_contract']['version'], '1')
        self.assertEqual(self.result(case)['decision'], 'needs_review')


if __name__ == '__main__':
    unittest.main()
