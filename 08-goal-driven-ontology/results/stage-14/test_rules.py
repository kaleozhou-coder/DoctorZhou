import unittest
from rules import compare,check,judgement,run,grade_all
from pathlib import Path

class TestRules(unittest.TestCase):
    def test_complete_and(self): self.assertIs(run(['and','a','b'],{'a':True,'b':False}), False)
    def test_false_and_unknown(self): self.assertIs(run(['and','a','b'],{'a':None,'b':False}), False)
    def test_true_and_unknown(self): self.assertIsNone(run(['and','a','b'],{'a':True}))
    def test_true_or_unknown(self): self.assertIs(run(['or','a','b'],{'a':True}), True)
    def test_false_or_unknown(self): self.assertIsNone(run(['or','a','b'],{'a':False}))
    def test_not_unknown(self): self.assertIsNone(run(['not','a'],{}))
    def test_no_rule_means_unknown(self): self.assertEqual(judgement(run(None,{})), 'UNKNOWN')
    def test_invalid_leaf(self):
        with self.assertRaises(ValueError): check('new',{'a'})
    def test_invalid_operator(self):
        with self.assertRaises(ValueError): check(['xor','a','b'],{'a','b'})
    def test_invalid_binary(self):
        with self.assertRaises(ValueError): check(['and','a'],{'a'})
    def test_invalid_not(self):
        with self.assertRaises(ValueError): check(['not','a','b'],{'a','b'})
    def test_invalid_fact(self):
        with self.assertRaises(ValueError): run('a',{'a':1})
    def test_exhaustive_equivalence(self):
        self.assertEqual(compare(['and','a','b'],['and','b','a'],['a','b'])['different'],0)
    def test_exhaustive_false_allow(self):
        r=compare(['and','a','b'],'a',['a','b'])
        self.assertEqual((r['evaluated'],r['different'],r['false_allow']),(9,3,2))
    def test_grade_corpus(self):
        g=grade_all(Path(__file__).resolve().parent)
        for fam in ('a','b'):
            for meth,r in g[fam].items():
                self.assertEqual(r['heldout_total'],8)
                self.assertEqual(r['citation_required_total'],3)
                self.assertEqual(r['exhaustive']['evaluated'],3**6)
