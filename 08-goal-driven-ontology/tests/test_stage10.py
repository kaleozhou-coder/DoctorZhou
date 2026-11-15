import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def module(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'src'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Stage10(unittest.TestCase):
 def test_schema_and_equal_materials(self):
  self.assertEqual(module('stage10_artifacts').verify(ROOT)['target_propositions'],23)
 def test_baseline_replay(self):
  m=module('run_stage10_baseline');p=json.loads((ROOT/'data/stage-10/materials.json').read_text())
  self.assertEqual(m.extract(p),json.loads((ROOT/'results/stage-10/arm_rule.json').read_text()))
 def test_mask_replay_and_overwrite_protection(self):
  m=module('stage10_artifacts')
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);m.prepare(ROOT,p/'a');m.prepare(ROOT,p/'b')
   for f in (p/'a').iterdir():self.assertEqual(f.read_bytes(),(p/'b'/f.name).read_bytes())
   with self.assertRaises(ValueError):m.prepare(ROOT,p/'a')
 def test_blind_grade_shape(self):
  s=module("stage10_artifacts").summarize(ROOT)
  self.assertEqual(len(s["ai_judged_results"]),4)
 def test_frozen_inputs(self):
  import hashlib
  for path,digest in json.loads((ROOT/"results/stage-10/review/input-sha256.json").read_text()).items():
   self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
 def test_baseline_has_no_gold_access(self):
  source=(ROOT/'src/run_stage10_baseline.py').read_text();self.assertNotIn('gold',source)
if __name__=='__main__':unittest.main()
