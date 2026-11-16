import copy, importlib.util, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stage11',ROOT/'src/stage11_artifacts.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Stage11(unittest.TestCase):
 def setUp(self):
  self.gold=m.read(ROOT/'data/stage-11/gold.json');self.materials=m.read(ROOT/'data/stage-11/materials.json')
  self.perfect={s:[dict(r,status='proposed',reason='test fixture only',sources=['D1.3']) for r in self.gold[s]] for s in ('facts','decisions')}
 def test_freeze(self):m.verify(ROOT)
 def test_replay(self):self.assertEqual(m.summarize(ROOT),m.read(ROOT/'results/stage-11/summary.json'))
 def test_perfect(self):self.assertEqual(m.score(self.perfect,self.gold,self.materials)['summary']['facts']['correct'],12)
 def test_orientation_flip(self):
  self.perfect['facts'][0]['answer']='SUFFICIENT_ONLY';self.assertFalse(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass'])
 def test_unknown_false_close(self):
  self.perfect['decisions'][1]['answer']='ALLOW';self.assertEqual(m.score(self.perfect,self.gold,self.materials)['summary']['false_closes'],1)
 def test_duplicate(self):
  self.perfect['facts'].append(copy.deepcopy(self.perfect['facts'][0]));self.assertFalse(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass'])
 def test_missing(self):
  self.perfect['facts']=self.perfect['facts'][1:];self.assertFalse(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass'])
 def test_reference(self):
  self.perfect['facts'][0]['sources']=['D99.1'];self.assertFalse(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass'])
 def test_status(self):
  self.perfect['facts'][0]['status']='approved';self.assertFalse(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass'])
 def test_bad_rows(self):
  self.perfect['facts']={};self.assertEqual(m.score(self.perfect,self.gold,self.materials)['summary']['facts']['correct'],0)
 def test_sources_not_entailment(self):
  self.perfect['facts'][0]['sources']=['D4.4'];self.assertTrue(m.score(self.perfect,self.gold,self.materials)['facts'][0]['pass']) # Semantic citation review is explicitly separate.
 def test_expected_unknowns(self):self.assertEqual([r['id'] for r in self.gold['decisions'] if r['answer']=='UNKNOWN'],['C02','C07','C08','C11','C16'])
 def test_frozen_outputs(self):
  for path,sha in m.read(ROOT/'results/stage-11/output-sha256.json').items():self.assertEqual(m.digest(ROOT/path),sha)
 def test_same_final_material(self):
  batch=m.read(ROOT/'data/stage-11/batch1.json')['documents']+m.read(ROOT/'data/stage-11/batch2.json')['documents'];self.assertEqual(batch,self.materials['documents'])
if __name__=='__main__':unittest.main()
