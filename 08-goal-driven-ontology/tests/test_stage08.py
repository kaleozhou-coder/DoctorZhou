import copy
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import run_stage08 as m

class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((m.ROOT/m.INPUTS[0]).read_text())
        self.receipts=json.loads((m.ROOT/m.INPUTS[1]).read_text())
        self.predictions={a:json.loads((m.ROOT/f'results/stage-07/first-run/{a}.predictions.json').read_text()) for a in m.ARMS}
    def rows(self): return m.ledger(self.pack,self.receipts,self.predictions)
    def test_totals(self):
        s=m.summarize(self.rows())['scopes']
        a=s['all_28_including_failure_controls']['arms']['receipt_ir']
        self.assertEqual((a['n'],a['receipt_units'],a['declared_path_units'],a['downstream_review_units'],a['evidence_request_units'],a['known_trust_control_false_close']),(28,20,22,14,4,2))
        b=s['26_excluding_trusted_failure_controls']
        self.assertEqual(b['receipt_break_even_ratio'],'1/3');self.assertEqual(b['path_break_even_ratio'],'3/10')
        self.assertEqual(b['arms']['receipt_ir']['receipt_units'],18)
    def test_units_not_added(self):
        c=m.aggregate([r for r in self.rows() if r['arm']=='receipt_ir'])
        self.assertEqual(m.cost(c,Fraction(1)),38)
        self.assertEqual(m.cost(c,Fraction(1),'declared_path_units'),40)
    def test_equal_cost_tipping_point(self):
        s=m.summarize(self.rows())['scopes']['26_excluding_trusted_failure_controls']['arms']
        self.assertEqual(m.cost(s['receipt_ir'],Fraction(1,3)),m.cost(s['gate_v2_ir'],Fraction(1,3)))
    def test_evidence_cost_cancels(self):
        s=m.summarize(self.rows())['scopes']['26_excluding_trusted_failure_controls']['arms']
        for e in (Fraction(0),Fraction(1),Fraction(100)):
            self.assertEqual(m.cost(s['receipt_ir'],Fraction(1),evidence_ratio=e)-m.cost(s['gate_v2_ir'],Fraction(1),evidence_ratio=e),12)
    def test_not_time_measurement(self):
        s=m.summarize(self.rows());self.assertIsNone(s['actual_human_seconds']);self.assertIsNone(s['measured_cost_currency']);self.assertEqual(s['actual_human_reviews'],0)
    def test_duplicate_probe(self):
        self.pack['probes'][1]['probe_id']=self.pack['probes'][0]['probe_id']
        with self.assertRaises(ValueError):self.rows()
    def test_receipt_missing(self):
        self.receipts.pop()
        with self.assertRaises(ValueError):self.rows()
    def test_prediction_order(self):
        self.predictions['ir_only'].reverse()
        with self.assertRaises(ValueError):self.rows()
    def test_unknown_decision(self):
        self.predictions['ir_only'][0]['decision']='approved'
        with self.assertRaises(ValueError):self.rows()
    def test_payment_not_allowed(self):
        self.predictions['ir_only'][0]['payment_authorized']=True
        with self.assertRaises(ValueError):self.rows()
    def test_invalid_paths(self):
        r=next(x['receipt'] for x in self.receipts if x['receipt'])
        r['reviewed_paths']=['x','x']
        with self.assertRaises(ValueError):self.rows()
    def test_unbound_receipt(self):
        r=next(x['receipt'] for x in self.receipts if x['receipt']);r['review_id']='wrong'
        with self.assertRaises(ValueError):self.rows()
    def test_negative_cost(self):
        with self.assertRaises(ValueError):m.cost(m.aggregate(self.rows()),Fraction(-1))
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):m.cost(m.aggregate(self.rows()),Fraction(1),'both')
    def test_reproduction_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            m.run(Path(d)/'a');m.run(Path(d)/'b')
            for name in ('ledger.json','summary.json'):
                self.assertEqual((Path(d)/'a'/name).read_bytes(),(Path(d)/'b'/name).read_bytes())
            with self.assertRaises(ValueError):m.run(Path(d)/'a')
    def test_frozen_input_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for rel in m.INPUTS+['experiments/stage-08/input-freeze.json']:
                (root/rel).parent.mkdir(parents=True,exist_ok=True);(root/rel).write_bytes((m.ROOT/rel).read_bytes())
            (root/m.INPUTS[0]).write_text('{}')
            with self.assertRaises(ValueError):m.verify(root)

    def test_nonexact_cost(self):
        for x in (float('nan'),float('inf'),True,0.25,'1/3'):
            with self.assertRaises(ValueError):m.cost(m.aggregate(self.rows()),x)
    def test_nonboolean_acceptance(self):
        self.predictions['receipt_ir'][0]['input_contract']['review_assertion_accepted']='yes'
        with self.assertRaises(ValueError):self.rows()
