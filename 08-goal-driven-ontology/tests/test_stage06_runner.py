import copy
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from run_stage06 import adapt_prose, prose_strata, run


class Stage06RunnerTests(unittest.TestCase):
    def test_author_schema_adapter_keeps_strata(self):
        entries = []
        for i, stratum in enumerate(('normal_close_control', 'policy_nonclosure_control',
                                     'safety_nonclosure', 'benign_abstention_cost')):
            entries.append({'probe_id': str(i), 'metric_stratum': stratum,
                            'input': {'case_id': str(i)},
                            'expected': {'decision': 'needs_review', 'reason_code': 'test'}})
        pack = {'probes': entries}; before = copy.deepcopy(pack)
        adapted = adapt_prose(pack)
        self.assertEqual(pack, before)
        self.assertEqual([p['scope'] for p in adapted['probes']],
                         ['in_policy', 'in_policy', 'ood_safety', 'unsupported_benign'])
        predictions = [{'case_id': str(i), 'decision': 'needs_review', 'reason_codes': ['test'],
                        'payment_authorized': False} for i in range(4)]
        strata = prose_strata(predictions, adapted)
        self.assertEqual(len(strata), 4)
        self.assertEqual(strata['safety_nonclosure']['passed'], 1)
        self.assertIsNone(strata['benign_abstention_cost']['passed'])

    def test_unknown_stratum_not_silently_scored(self):
        with self.assertRaises(KeyError):
            adapt_prose({'probes': [{'probe_id': 'x', 'metric_stratum': 'unrecognized'}]})

    def test_existing_results_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory); (p/'keep').write_text('first result')
            with self.assertRaises(ValueError):
                run(p)
            self.assertEqual((p/'keep').read_text(), 'first result')


if __name__ == '__main__':
    unittest.main()
