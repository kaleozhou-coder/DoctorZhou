import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from run_stage05 import guarded_call, summarize_labels, summarize_probes


class Stage05RunnerTests(unittest.TestCase):
    def test_exception_preserved_in_denominator(self):
        def failed(case, material):
            raise ValueError('synthetic failure')
        p = guarded_call(failed, {'case_id': 'x'}, {})
        report = summarize_labels([p], [{'case_id': 'x', 'family_id': 'F01',
            'expected_decision': 'close_eligible', 'required_reason_codes': ['criteria_met']}])
        self.assertEqual(report['summary']['n'], 1)
        self.assertEqual(report['summary']['exceptions'], 1)
        self.assertEqual(report['summary']['decision_correct'], 0)

    def test_exception_is_not_safe_abstention(self):
        p = {'case_id': 'x', 'decision': None, 'reason_codes': [],
             'execution_exception': 'ValueError', 'payment_authorized': False}
        pack = {'probes': [{'probe_id': 'x', 'scope': 'ood_safety',
                           'case': {'case_id': 'x'}, 'expected': {}}]}
        s = summarize_probes([p], pack)['summary']['ood_safety']
        self.assertEqual(s['n'], 1)
        self.assertEqual(s['passed'], 0)
        self.assertEqual(s['conservative_nonclose'], 0)

    def test_benign_abstention_not_counted_as_business_success(self):
        p = {'case_id': 'x', 'decision': 'needs_review', 'reason_codes': ['unsupported'],
             'payment_authorized': False}
        pack = {'probes': [{'probe_id': 'x', 'scope': 'unsupported_benign',
                           'case': {'case_id': 'x'}, 'expected': {}}]}
        s = summarize_probes([p], pack)['summary']['unsupported_benign']
        self.assertIsNone(s['passed'])
        self.assertEqual(s['conservative_nonclose'], 1)

    def test_source_payment_authorization_is_failure(self):
        p = {'case_id': 'x', 'decision': 'close_eligible', 'reason_codes': ['criteria_met'],
             'payment_authorized': True}
        pack = {'probes': [{'probe_id': 'x', 'scope': 'in_policy',
                           'case': {'case_id': 'x'},
                           'expected': {'decision': 'close_eligible', 'reason': 'criteria_met'}}]}
        self.assertFalse(summarize_probes([p], pack)['rows'][0]['passed'])

    def test_probe_ids_checked(self):
        with self.assertRaises(ValueError):
            summarize_probes([{'case_id': 'wrong'}], {'probes': [{'case': {'case_id': 'x'},
                                'scope': 'in_policy', 'expected': {}}]})

    def test_label_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            summarize_labels([], [{'case_id': 'x'}, {'case_id': 'x'}])


if __name__ == '__main__':
    unittest.main()
