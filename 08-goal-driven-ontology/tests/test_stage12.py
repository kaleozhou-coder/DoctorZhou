import copy,importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stage12',ROOT/'src/stage12_artifacts.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Stage12(unittest.TestCase):
 def setUp(self):
  self.q=m.read(ROOT/'data/stage-12/questions.json');self.g=m.read(ROOT/'data/stage-12/gold.json');self.mat=m.read(ROOT/'data/stage-12/short_early.json')
  self.o={section:[dict(id=x['id'],answer='fixture answer, not model output',sources=['D1.3'],status='proposed',**({'rationale':'fixture'} if section=='cases' else {})) for x in self.q[key]] for section,key in [('questions','questions'),('cases','snapshots')]}
  self.r={section:[dict(id=key,semantic_ok=True,citation_ok=True,note='fixture',**({'normalized_meaning':val['meaning']} if section=='cases' else {})) for key,val in self.g[section].items()] for section in ('questions','cases')}
 def test_freeze(self):m.verify(ROOT)
 def test_replay(self):self.assertEqual(m.summarize(ROOT),m.read(ROOT/'results/stage-12/summary.json'))
 def test_fixture_valid(self):self.assertEqual(m.check_output(self.o,self.q,self.mat),[])
 def test_missing(self):
  self.o['questions'].pop();self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_duplicate(self):
  self.o['cases'].append(self.o['cases'][0]);self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_order(self):
  self.o['cases'].reverse();self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_wrong_ref(self):
  self.o['questions'][0]['sources']=['D99.1'];self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_no_refs(self):
  self.o['questions'][0]['sources']=[];self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_status(self):
  self.o['cases'][0]['status']='approved';self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_answer(self):
  self.o['cases'][0]['answer']='';self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_rationale(self):
  self.o['cases'][0]['rationale']=None;self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_nonobject(self):self.assertTrue(m.check_output([],self.q,self.mat))
 def test_nonarray(self):
  self.o['questions']={};self.assertTrue(m.check_output(self.o,self.q,self.mat))
 def test_valid_ref_not_entailment(self):
  self.o['questions'][0]['sources']=['D4.4'];self.assertEqual(m.check_output(self.o,self.q,self.mat),[])
 def test_review_summary(self):self.assertEqual(m.summarize_review(self.r,self.g)['cases']['semantic_correct'],6)
 def test_false_permission(self):
  self.r['cases'][0].update(normalized_meaning='permitted',semantic_ok=False);self.assertEqual(m.summarize_review(self.r,self.g)['false_permissions'],1)
 def test_semantic_vs_citation(self):
  self.r['questions'][0]['citation_ok']=False
  x=m.summarize_review(self.r,self.g);self.assertEqual(x['questions']['semantic_correct'],6);self.assertEqual(x['questions']['citation_supported'],5)
 def test_review_nonbool(self):
  self.r['questions'][0]['semantic_ok']='true'
  with self.assertRaises(ValueError):m.summarize_review(self.r,self.g)
 def test_review_wrong_meaning(self):
  self.r['cases'][0]['normalized_meaning']='permitted'
  with self.assertRaises(ValueError):m.summarize_review(self.r,self.g)
 def test_paired_core(self):
  core=[d for d in self.mat['documents']]
  expected={x['id']:x for x in core}
  for v in m.VARIANTS:
   docs=m.read(ROOT/f'data/stage-12/{v}.json')['documents']
   self.assertEqual({d['id']:d for d in docs if d['id'].startswith('D')},expected)
 def test_batches_exact(self):
  for v in m.VARIANTS:
   first=m.read(ROOT/f'data/stage-12/{v}_first.json')['documents'];second=m.read(ROOT/f'data/stage-12/{v}_second.json')['documents']
   self.assertEqual(first+second,m.read(ROOT/f'data/stage-12/{v}.json')['documents'])
 def test_position(self):
  for v in m.VARIANTS:
   docs=m.read(ROOT/f'data/stage-12/{v}.json')['documents']
   self.assertEqual(docs[0 if v.endswith('early') else -1]['id'],'D3')
 def test_output_hashes(self):
  for path,sha in m.read(ROOT/'results/stage-12/output-sha256.json').items():self.assertEqual(m.digest(ROOT/path),sha)
if __name__=='__main__':unittest.main()
