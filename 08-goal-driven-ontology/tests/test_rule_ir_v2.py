"""Author-created engineering probes; no evaluator cases, labels or stress probes."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import rule_ir_v2 as ir
import test_rule_ir
ROOT = Path(__file__).resolve().parents[1]


class ScalarCompatibilityTests(test_rule_ir.RuleIRTests):
    """Run existing v1 probes using v2 program and interpreter, unchanged assertions."""
    def setUp(self):
        super().setUp()
        self.p['version'] = ir.VERSION
        import test_rule_ir
        for key in ('evaluate', 'loads', 'validate', 'predict_case', 'RuleError'):
            p = patch.object(test_rule_ir, key, getattr(ir, key))
            p.start(); self.addCleanup(p.stop)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.p = ir.loads((ROOT/'ontology/ir-reference-v2/F01.json').read_text())
        self.f = {'request': {'invoice_id':'invoice', 'po_line':'line', 'invoice_quantity':2, 'target_serials':['a','b']},
                  'lots':[{'lot_id':'lot1','po_line':'line','status':'accepted','serials':['a','b']}]}
    def check(self, decision, reason):
        result=ir.evaluate(self.p,self.f)
        self.assertEqual((result['decision'], result['reason_codes']), (decision,[reason]))
        self.assertIs(result['payment_authorized'],False)
    def test_valid(self):
        self.assertTrue(ir.validate(self.p)['valid']); self.check('close_eligible','criteria_met')
    def test_count(self):
        self.f['request']['invoice_quantity']=3;self.check('needs_review','target_count_mismatch')
    def test_uncovered(self):
        self.f['lots'][0]['serials']=['a'];self.check('needs_evidence','uncovered_serials')
    def test_empty_lots(self):
        self.f['lots']=[];self.check('needs_evidence','uncovered_serials')
    def test_ignore_wrong_line(self):
        self.f['lots'][0]['po_line']='other';self.check('needs_evidence','uncovered_serials')
    def test_ignore_pending(self):
        self.f['lots'][0]['status']='pending';self.check('needs_evidence','uncovered_serials')
    def test_ignore_disjoint(self):
        self.f['lots'].append(dict(self.f['lots'][0],serials=['z']));self.check('close_eligible','criteria_met')
    def test_identical_duplicate_order(self):
        self.f['lots'].append(dict(self.f['lots'][0],serials=['b','a']));self.check('close_eligible','criteria_met')
    def test_conflict(self):
        self.f['lots'].append(dict(self.f['lots'][0],serials=['a']));self.check('needs_review','lot_identity_conflict')
    def test_extra_payload_conflict(self):
        self.f['lots'].append(dict(self.f['lots'][0],extra=True));self.check('needs_review','lot_identity_conflict')
    def test_overlap(self):
        self.f['lots'].append(dict(self.f['lots'][0],lot_id='lot2'));self.check('needs_review','overlapping_lots')
    def test_outside_target_overlap(self):
        self.f['lots'][0]['serials']=['a','z']
        self.f['lots'].append(dict(self.f['lots'][0],lot_id='lot2',serials=['b','z']))
        self.check('needs_review','overlapping_lots')
    def test_nonoverlap_union(self):
        self.f['lots'][0]['serials']=['a']
        self.f['lots'].append(dict(self.f['lots'][0],lot_id='lot2',serials=['b']))
        self.check('close_eligible','criteria_met')
    def test_duplicate_target(self):
        self.f['request']['target_serials']=['a','a'];self.check('needs_review','malformed_input')
    def test_duplicate_member(self):
        self.f['lots'][0]['serials']=['a','a'];self.check('needs_review','malformed_input')
    def test_null_member(self):
        self.f['lots'][0]['serials']=['a',None];self.check('needs_evidence','condition_unknown')
    def test_missing_record_field(self):
        del self.f['lots'][0]['lot_id'];self.check('needs_evidence','condition_unknown')
    def test_missing_array(self):
        del self.f['lots'];self.check('needs_evidence','condition_unknown')
    def test_missing_request_id(self):
        del self.f['request']['invoice_id'];self.check('needs_evidence','input_missing')
    def test_bad_record(self):
        self.f['lots']=[3];self.check('needs_review','malformed_input')
    def test_bad_status(self):
        self.f['lots'][0]['status']='unknown';self.check('needs_review','malformed_input')
    def test_eager_irrelevant_record_validation(self):
        self.f['lots'].append({'po_line':'other','status':'pending','lot_id':'bad','serials':123})
        self.check('needs_review','malformed_input')
    def test_malformed_not_hidden_by_unknown(self):
        self.f['lots']=[None,dict(self.f['lots'][0],serials=123)]
        self.check('needs_review','malformed_input')
    def test_size_budget(self):
        self.f['lots']=self.f['lots']*129;self.check('needs_review','malformed_input')
    def test_execution_budget(self):
        with patch.object(ir,'MAX_STEPS',4):self.check('needs_review','malformed_input')
    def test_derived_set_budget(self):
        self.f['lots'][0]['serials']=['a']+[f'x{i}' for i in range(100)]
        self.f['lots'].append(dict(self.f['lots'][0],lot_id='lot2',serials=['b']+[f'y{i}' for i in range(100)]))
        self.check('needs_review','malformed_input')
    def test_filter_unknown_not_silently_removed(self):
        del self.f['request']['po_line']
        self.p['rules']=self.p['rules'][2:]
        self.check('needs_evidence','condition_unknown')
    def test_no_dedup_conflicts(self):
        self.f['lots'].append(dict(self.f['lots'][0],serials=['a']))
        self.p['rules']=[r for r in self.p['rules'] if r['id']!='identity']
        self.check('needs_review','malformed_input')
    def test_item_outside_filter(self):
        self.p['rules'][0]['when']={'op':'item','key':'status'};self.check('needs_review','invalid_artifact')
    def test_incompatible_set_types(self):
        self.p['fields']['targets']['type']['items']='integer';self.check('needs_review','invalid_artifact')
    def test_unknown_record_key(self):
        self.p['fields']['lots']['type']['items']['fields'].pop('status');self.check('needs_review','invalid_artifact')
    def test_unhashable_tag(self):
        self.p['rules'][0]['decision']=[];self.check('needs_review','invalid_artifact')
        with self.assertRaises(ir.RuleError):ir.validate(self.p)
    def test_bad_schema(self):
        for typ in ([], {}, {'kind':[]}, {'kind':'set','items':{'kind':'record','fields':{'x':'string'}}}):
            with self.subTest(typ=typ):
                self.p['fields']['lots']['type']=typ;self.check('needs_review','invalid_artifact')
    def test_surrogate_artifact(self):
        self.p['fields']['line']['path']=['\ud800'];self.check('needs_review','invalid_artifact')
    def test_surrogate_facts(self):
        self.f['unused']='\ud800';self.check('needs_review','malformed_input')
    def test_huge_integer(self):
        self.f['unused']=10**5000;self.check('needs_review','malformed_input')
    def test_nonstring_key(self):
        self.f[3]='bad';self.check('needs_review','malformed_input')
    def test_cyclic_program(self):
        self.p['cycle']=self.p;self.check('needs_review','invalid_artifact')
    def test_no_code(self):
        self.p['rules'][0]['when']={'op':'exec','arg':'print(1)'};self.check('needs_review','invalid_artifact')
    def test_transport(self):
        material=json.loads((ROOT/'benchmark/v1/model-facing/F01/materials.json').read_text())
        case={'case_id':'author-probe','policy_source_id':'F01-POL','sources':[{'source_id':'probe','locator':'p','facts':self.f}]}
        self.assertEqual(ir.predict_case(case,self.p,material)['decision'],'close_eligible')
    def test_generic_integer_sets(self):
        ref=[{'source_id':'generic','locator':'p'}]
        p={'version':ir.VERSION,'fields':{'left':{'path':['left'],'type':{'kind':'set','items':'integer'}},'right':{'path':['right'],'type':{'kind':'set','items':'integer'}}},'rules':[{'id':'r','when':{'op':'subset','left':{'op':'field','name':'left'},'right':{'op':'field','name':'right'}},'decision':'close_eligible','reason':'subset','source_refs':ref}],'default':{'decision':'needs_evidence','reason':'not_subset','source_refs':ref}}
        self.assertEqual(ir.evaluate(p,{'left':[1],'right':[2,1]})['decision'],'close_eligible')
        self.assertEqual(ir.evaluate(p,{'left':[True],'right':[1]})['reason_codes'],['malformed_input'])

if __name__=='__main__':unittest.main()
