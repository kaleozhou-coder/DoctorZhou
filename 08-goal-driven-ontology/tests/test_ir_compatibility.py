import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from run_ir_compatibility import run


class CompatibilityRunnerTests(unittest.TestCase):
    def fixture(self, root):
        def put(name, obj, raw=False):
            path=root/name; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(obj if raw else json.dumps(obj))
            return path
        put("src/rule_ir.py", "# fixture only\n", True)
        artifact=put("ontology/example.json", {})
        put("benchmark/v1/model-facing/F05/materials.json", {})
        put("benchmark/v1/evaluator/inputs/F05.json", {"cases":[{"case_id":"c"}]})
        put("benchmark/v1/evaluator/labels.json", {"cases":[
            {"case_id":"c","family_id":"F05","expected_decision":"needs_evidence","required_reason_codes":["missing"]},
            {"case_id":"other","family_id":"F04","expected_decision":"needs_review","required_reason_codes":["other"]}]})
        freeze=put("freeze.json",{"sha256":{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ["src/rule_ir.py","ontology/example.json"]}})
        return artifact,freeze

    def test_coverage_and_preserved_predictions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root);output=root/"out"
            pred={"case_id":"c","decision":"needs_evidence","reason_codes":["missing"]}
            with patch("run_ir_compatibility.verify_freeze"), patch("run_ir_compatibility.predict_case",return_value=pred):
                summary=run(root,artifact,"F05",freeze,output)
            self.assertEqual((summary["executed_cases"],summary["unsupported_not_executed_cases"]),(1,1))
            self.assertEqual(summary["decision_correct"],1)
            self.assertTrue((output/"predictions.json").exists())
            with self.assertRaises(ValueError):
                run(root,artifact,"F05",freeze,output)

    def test_modified_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root)
            artifact.write_text("{} ")
            with self.assertRaises(ValueError):
                run(root,artifact,"F05",freeze,root/"out")

    def test_missing_implementation_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root);freeze.write_text('{"sha256":{}}')
            with self.assertRaises(ValueError):
                run(root,artifact,"F05",freeze,root/"out")

    def test_duplicate_case_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root)
            (root/"benchmark/v1/evaluator/inputs/F05.json").write_text(json.dumps({"cases":[{"case_id":"c"},{"case_id":"c"}]}))
            with patch("run_ir_compatibility.verify_freeze"), self.assertRaises(ValueError):
                run(root,artifact,"F05",freeze,root/"out")

    def test_duplicate_labels_rejected_after_prediction_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root);output=root/"out"
            path=root/"benchmark/v1/evaluator/labels.json";doc=json.loads(path.read_text())
            doc["cases"].append(doc["cases"][0]);path.write_text(json.dumps(doc))
            pred={"case_id":"c","decision":"needs_evidence","reason_codes":["missing"]}
            with patch("run_ir_compatibility.verify_freeze"), patch("run_ir_compatibility.predict_case",return_value=pred), self.assertRaises(ValueError):
                run(root,artifact,"F05",freeze,output)
            self.assertTrue((output/"predictions.json").exists())
            self.assertFalse((output/"summary.json").exists())

    def test_family_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); artifact,freeze=self.fixture(root)
            with self.assertRaises(ValueError):
                run(root,artifact,"../F05",freeze,root/"out")

if __name__ == "__main__":
    unittest.main()
