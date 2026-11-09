"""Pack/runner regressions, not a claim that OOD safety goals all pass."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from run_stress_probes import verify,evaluate,unsafe_control


class StressTests(unittest.TestCase):
    def test_frozen_inputs_and_stratification(self):
        pack=verify()
        self.assertEqual(len(pack['probes']),30)
        self.assertEqual(len({p['probe_id'] for p in pack['probes']}),30)
        self.assertEqual(sum(p['scope']=='in_policy' for p in pack['probes']),22)
        for p in pack['probes']:
            self.assertTrue(p['oracle_rationale'])
            self.assertTrue(p['policy_refs'])

    def test_reproduce_frozen_baseline_without_mutating_inputs(self):
        pack=verify();before=copy.deepcopy(pack)
        actual=evaluate(pack)
        saved=json.loads((ROOT/'results/stage-04/stress/frozen-baseline.json').read_text())
        self.assertEqual(actual,saved)
        self.assertEqual(pack,before)

    def test_control_cannot_hide_nonclosure_and_ood_failures(self):
        result=evaluate(verify(),unsafe_control)
        self.assertEqual(result['summary']['ood_safety']['passed'],0)
        self.assertLess(result['summary']['in_policy']['passed'],22)
        self.assertLess(result['summary']['metamorphic']['passed'],8)

    def test_predictor_exceptions_are_failure_not_dropped_rows(self):
        def broken(case,policy):raise TypeError('synthetic failure')
        result=evaluate(verify(),broken)
        self.assertEqual(len(result['results']),30)
        self.assertEqual(result['summary']['in_policy']['exceptions'],22)
        self.assertEqual(result['summary']['ood_safety']['exceptions'],8)
        self.assertEqual(result['summary']['metamorphic']['passed'],0)

    def test_payment_authorization_never_passes(self):
        def unsafe(case,policy):
            r=unsafe_control(case,policy);r['payment_authorized']=True;return r
        result=evaluate(verify(),unsafe)
        self.assertEqual(sum(r['passed'] for r in result['results']),0)


if __name__=='__main__':unittest.main()
