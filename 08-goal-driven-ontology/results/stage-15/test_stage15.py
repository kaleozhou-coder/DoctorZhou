import unittest
import score_stage15 as s

def specimen(group):
    gold=s.read('score/gold.json')[group]
    return {**{f:{'value':gold[f]['value'],'evidence':[gold[f]['source']]} for f in s.FIELDS},
            'missing_docs':gold['missing_docs']}

class TestFrozenEvaluation(unittest.TestCase):
    def setUp(self):
        self.full=specimen('complete')
        self.gap=specimen('withheld')
    def test_frozen_bytes(self):
        s.validate_freeze()
    def test_complete_schema(self):
        result=s.grade(self.full,'complete','one')
        self.assertEqual((result['case_correct'],result['value_correct'],result['direct_citations']),(10,7,7))
    def test_withheld_schema(self):
        result=s.grade(self.gap,'withheld','one')
        self.assertEqual((result['case_correct'],result['value_correct'],result['correct_unknown']),(10,7,8))
    def test_wrong_trigger_no_substitution(self):
        self.assertEqual(s.decide(self.full,'sign',20,'buyer_install_notice'),'UNKNOWN')
        self.assertEqual(s.decide(self.full,'install',20,'award_notice_issued'),'UNKNOWN')
    def test_at_boundary(self):
        self.assertEqual(s.decide(self.full,'sign',30,'award_notice_issued'),'PASS')
        self.assertEqual(s.decide(self.full,'sign',31,'award_notice_issued'),'FAIL')
    def test_stale_rule_in_withheld_is_unsafe(self):
        self.gap['sign_days']['value']=12
        self.gap['sign_trigger']['value']='award_notice_issued'
        self.assertEqual(s.grade(self.gap,'withheld','one')['unsafe_pass'],1)
    def test_unseen_citation(self):
        self.gap['sign_days']['evidence']=['R7']
        r=s.grade(self.gap,'withheld','one')
        self.assertEqual((r['unavailable_citations'],r['direct_citations']),(1,6))
    def test_missing_doc_explicit(self):
        self.gap['missing_docs']=[]
        self.assertFalse(s.grade(self.gap,'withheld','one')['missing_docs_correct'])
    def test_unknown_missing_counted_by_field(self):
        self.full['advance_pct']['value']=None
        r=s.grade(self.full,'complete','one')
        self.assertEqual((r['value_correct'],r['case_correct']),(6,10))
    def test_type_bool_rejected(self):
        self.full['sign_days']['value']=True
        with self.assertRaisesRegex(ValueError,'invalid value type'): s.grade(self.full,'complete','one')
    def test_evidence_wide_vs_exclusive(self):
        self.full['sign_days']['evidence'].append('M')
        r=s.grade(self.full,'complete','one')
        self.assertEqual((r['direct_citations'],r['exclusive_direct_citations']),(7,6))
    def test_draft_does_not_have_future_citations(self):
        r=s.grade(self.full,'complete','batch-draft')
        self.assertEqual(r['unavailable_citations'],7)

if __name__=='__main__': unittest.main()
