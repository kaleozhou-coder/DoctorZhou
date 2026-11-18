import itertools,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import stage13_artifacts as s
F=lambda k:{'field':k}
EXPR={'and':[F('identity_verified'),{'not':F('active_hold')},{'or':[F('routine_packet_complete'),{'and':[F('minor_repair_scope'),F('exception_reconciled'),F('exception_authorized')]}]}]}
class TestStage13(unittest.TestCase):
 def test_frozen(self):s.verify()
 def test_identical_content(self):
  sets=[{b['id']:b['text'] for b in s.read(s.ROOT/('data/stage-13/'+x+'.json'))['blocks']} for x in s.LAYOUTS]
  self.assertEqual(sets[0],sets[1]);self.assertEqual(sets[1],sets[2])
 def test_positions(self):
  for x,pos in zip(s.LAYOUTS,[0,4,8]):self.assertEqual(s.read(s.ROOT/('data/stage-13/'+x+'.json'))['blocks'][pos]['id'],'N41')
 def test_hidden_gold(self):
  for c in s.read(s.ROOT/'data/stage-13/hidden_cases.json'):self.assertEqual(s.evaluate(EXPR,c['facts']),c['expected'])
 def test_exhaustive_truth(self):
  # Independently enumerate compatible binary completions, derive consensus.
  names=['identity_verified','active_hold','routine_packet_complete','minor_repair_scope','exception_reconciled','exception_authorized']
  for values in itertools.product([False,True,None],repeat=6):
   results=[]
   for binary in itertools.product(*[([False,True] if v is None else [v]) for v in values]):
    i,h,r,m,c,a=binary;results.append(i and not h and (r or (m and c and a)))
   expected='permitted' if all(results) else 'blocked' if not any(results) else 'unknown'
   self.assertEqual(s.evaluate(EXPR,dict(zip(names,values))),expected,values)
 def test_unknown_field(self):
  with self.assertRaises(ValueError):s.validate_expr(F('evil'))
 def test_constants_rejected(self):
  for e in [True,None,1,'x',{'literal':True}]:
   with self.assertRaises(ValueError):s.validate_expr(e)
 def test_multi_op_rejected(self):
  with self.assertRaises(ValueError):s.validate_expr({'field':'active_hold','not':F('active_hold')})
 def test_empty_and(self):
  with self.assertRaises(ValueError):s.validate_expr({'and':[]})
 def test_single_or(self):
  with self.assertRaises(ValueError):s.validate_expr({'or':[F('active_hold')]})
 def test_deep(self):
  e=F('active_hold')
  for i in range(20):e={'not':e}
  with self.assertRaises(ValueError):s.validate_expr(e)
 def test_large(self):
  with self.assertRaises(ValueError):s.validate_expr({'or':[F('active_hold')]*201})
 def test_fact_missing(self):
  with self.assertRaises(ValueError):s.evaluate(EXPR,{})
 def test_fact_integer(self):
  with self.assertRaises(ValueError):s.evaluate(EXPR,{k:1 for k in s.FIELDS})
 def test_fact_extra(self):
  with self.assertRaises(ValueError):s.evaluate(EXPR,{**{k:True for k in s.FIELDS},'x':True})
 def test_sources(self):
  self.assertTrue(s.source_errors(['bad'],{'N41'}));self.assertTrue(s.source_errors(['N41','N41'],{'N41'}));self.assertFalse(s.source_errors(['N41'],{'N41'}))
 def test_output_shape(self):self.assertTrue(s.check_output({},set()))
 def test_duplicate_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_text('{"x":1,"x":2}')
   with self.assertRaises(ValueError):s.read(p)
 def test_nonfinite_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_text('{"x":NaN}')
   with self.assertRaises(ValueError):s.read(p)
if __name__=='__main__':unittest.main()
