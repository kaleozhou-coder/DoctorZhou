import json, tempfile, unittest
from pathlib import Path
import freeze
import score

class Test(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(14, len(score.GOLD))
        self.assertEqual(12, len(score.CHECKS))
    def test_same_multisets(self):
        self.assertCountEqual(sum(freeze.IDS['front'],[]),sum(freeze.IDS['end'],[]))
    def test_q6_crosses_batch(self):
        self.assertIn('Q6',freeze.IDS['front'][0])
        self.assertIn('Q6',freeze.IDS['end'][1])
    def test_q6_weak_hint(self):
        self.assertNotIn('替代',freeze.DOCS['Q6'])
        self.assertNotIn('更正',freeze.DOCS['Q6'])
    def test_inputs_replay(self):
        root=score.ROOT/'inputs'
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            freeze.materialize(dest)
            self.assertEqual({p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()},
                             {p.relative_to(dest):p.read_bytes() for p in dest.rglob('*') if p.is_file()})
    def test_rule_priority(self):
        a={k:[v,opts[0]] for k,(v,opts) in score.GOLD.items()}
        self.assertEqual('fail',score.apply(a,{'m_current_material_basis':'DRAWING','m_color':'BLUE'}))
        self.assertEqual('unknown',score.apply(a,{'m_current_material_basis':'DRAWING','m_color':'GRAY'}))
    def test_question_proposal_not_a_rule(self):
        a={k:[v,opts[0]] for k,(v,opts) in score.GOLD.items()}
        self.assertEqual('unknown',score.apply(a,{'y_current_ratio':'80'}))
    def test_citations_measure_both(self):
        a={k:[v,opts[0]] for k,(v,opts) in score.GOLD.items()}
        self.assertEqual(score.score(a)['joint'],14)
        a['q_opening']=['2026-07-16',['QA','Q0']]
        s=score.score(a)
        self.assertEqual((s['value'],s['joint'],s['posthoc_relaxed_joint']),(14,13,14))
        a['q_opening']=['2026-07-16',[]]
        self.assertEqual(score.score(a)['posthoc_relaxed_joint'],13)
    def test_failures_not_hidden(self):
        a=score.generate()
        self.assertEqual(a['front-strong']['final']['non_gold_evidence'],['q_opening','m_missing_locator'])
        self.assertEqual(a['end-batch']['final']['non_gold_evidence'],['q_opening','m_current_material_basis','y_current_ratio'])
    def test_predeclared_rules(self):
        for x in score.generate().values():
            self.assertEqual((x['final']['value'],x['final']['check_score']),(14,12))
            self.assertEqual(x['final']['false_positive_checks'],[])
    def test_json_duplicate(self):
        with self.assertRaises(ValueError): json.loads('{"a":1,"a":2}',object_pairs_hook=score.unique)
    def test_invalid_model_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            p.write_text('{"q_type_basis":["DRAWING",["Q4"]]}')
            with self.assertRaises(ValueError): score.load(p)

if __name__=='__main__': unittest.main()
