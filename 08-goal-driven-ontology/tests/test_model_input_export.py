import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from export_model_inputs import export_inputs

class ModelInputExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'benchmark';self.root.mkdir()
        self.material=self.root/'model-facing/F01/materials.json';self.material.parent.mkdir(parents=True)
        self.material.write_text(json.dumps({'family_id':'F01','policy':{'p1':'Synthetic policy.'}}))
        (self.root/'manifest.json').write_text(json.dumps({'families':[{'family_id':'F01','split':'test','model_materials':'model-facing/F01/materials.json'}]}))
        (self.root/'evaluator').mkdir();(self.root/'evaluator/labels.json').write_text('{"secret":"NEVER_EXPORT"}')
        self.freeze()
    def freeze(self):
        data={str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file() and p.name!='FILE_SHA256.json'}
        (self.root/'FILE_SHA256.json').write_text(json.dumps(data))
    def test_only_allowlisted_materials(self):
        output=self.base/'out.zip';export_inputs(self.root,output)
        with zipfile.ZipFile(output) as zf:
            self.assertEqual({'model-input-manifest.json','model-facing/F01/materials.json'},set(zf.namelist()))
            self.assertTrue(all(b'NEVER_EXPORT' not in zf.read(name) for name in zf.namelist()))
    def test_archive_byte_reproducibility(self):
        a=export_inputs(self.root,self.base/'a.zip');b=export_inputs(self.root,self.base/'b.zip')
        self.assertEqual(a['export_sha256'],b['export_sha256'])
    def test_embedded_label_key_rejected(self):
        self.material.write_text(json.dumps({'family_id':'F01','nested':{'expected_decision':'close_eligible'}}));self.freeze()
        with self.assertRaisesRegex(ValueError,'Evaluator fields'):export_inputs(self.root,self.base/'out.zip')
    def test_manifest_cannot_export_evaluator(self):
        (self.root/'manifest.json').write_text(json.dumps({'families':[{'family_id':'F01','split':'test','model_materials':'evaluator/labels.json'}]}));self.freeze()
        with self.assertRaisesRegex(ValueError,'model-facing'):export_inputs(self.root,self.base/'out.zip')
    def test_frozen_package_not_changed_by_export(self):
        with self.assertRaisesRegex(ValueError,'inside'):export_inputs(self.root,self.root/'out.zip')
    def test_undeclared_family_rejected(self):
        with self.assertRaisesRegex(ValueError,'does not exist'):export_inputs(self.root,self.base/'out.zip',['F99'])
    def test_changed_input_rejected(self):
        self.material.write_text('{}')
        with self.assertRaisesRegex(ValueError,'changed'):export_inputs(self.root,self.base/'out.zip')

if __name__=='__main__':unittest.main()
