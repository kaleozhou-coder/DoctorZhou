import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pilot import decide, score

class SemanticPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=json.loads((ROOT/'data/synthetic/acceptance_cases.json').read_text())['cases']
        cls.features=json.loads((ROOT/'ontology/reference_model.json').read_text())['semantic_features']
    def test_all_explicit_expectations(self):
        for case in self.cases:
            with self.subTest(case=case['id']):
                self.assertEqual(case['expected'],decide(case,self.features)['decision'])
    def test_unknown_revocation_does_not_close(self):
        for value in [None, 'false', 0]:
            case=copy.deepcopy(self.cases[0]); case['records'][0]['revoked']=value
            self.assertEqual('needs_review',decide(case,self.features)['decision'])
        case=copy.deepcopy(self.cases[0]); del case['records'][0]['revoked']
        self.assertEqual('needs_review',decide(case,self.features)['decision'])
    def test_nonfinite_or_nonnumeric_quantities_do_not_close(self):
        for value in [float('nan'), float('inf'), True, None, '10']:
            for target in ['invoice_line', 'record']:
                case=copy.deepcopy(self.cases[0])
                (case['invoice_line'] if target=='invoice_line' else case['records'][0])['quantity']=value
                self.assertEqual('needs_review',decide(case,self.features)['decision'])
    def test_revoked_old_policy_does_not_block_valid_evidence(self):
        case=copy.deepcopy(self.cases[0]); extra=copy.deepcopy(case['records'][0])
        extra.update(id='E2',revoked=True,policy_version='P_OLD',authorized=False)
        case['records'].append(extra)
        self.assertEqual('close_eligible',decide(case,self.features)['decision'])
    def test_nonfinite_aggregate_does_not_close(self):
        case=copy.deepcopy(self.cases[0]); case['records'][0]['quantity']=1e308
        extra=copy.deepcopy(case['records'][0]); extra['id']='E2'; case['records'].append(extra)
        self.assertEqual('needs_review',decide(case,self.features)['decision'])
    def test_case_ids_unique(self):
        self.assertEqual(len(self.cases),len({c['id'] for c in self.cases}))
    def test_no_payment_approved_state(self):
        self.assertTrue(all(decide(c,self.features)['decision'] in ('close_eligible','needs_evidence','needs_review') for c in self.cases))
    def test_input_not_mutated(self):
        original=copy.deepcopy(self.cases)
        for case in self.cases: decide(case,self.features)
        self.assertEqual(original,self.cases)
    def test_each_mutant_is_detected(self):
        ref=[decide(c,self.features)['decision'] for c in self.cases]
        for key in self.features:
            mutated=copy.deepcopy(self.features); mutated[key]=not mutated[key]
            with self.subTest(feature=key):
                self.assertNotEqual(ref,[decide(c,mutated)['decision'] for c in self.cases])
    def test_single_record_cases_order_invariant(self):
        # Under P0 mixed defects can have different first reasons; decisions should still match.
        for case in self.cases:
            changed=copy.deepcopy(case); changed['records'].reverse()
            self.assertEqual(decide(case,self.features)['decision'],decide(changed,self.features)['decision'])

if __name__=='__main__': unittest.main()
