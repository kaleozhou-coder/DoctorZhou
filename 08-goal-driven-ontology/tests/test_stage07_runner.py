import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import run_stage07

class JointRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'run'
        cls.reports=run_stage07.run(cls.output)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def test_new_directory_created(self):
        self.assertTrue((self.output/'summary.json').is_file())
    def test_refuses_overwriting_results(self):
        with self.assertRaises(ValueError):run_stage07.run(self.output)
    def test_all_28_full_protocol_metadata(self):
        rows=self.reports['receipt_ir']['items'];self.assertEqual(28,len(rows))
        self.assertTrue(all(x['all_expected_fields_match'] for x in rows))
    def test_known_false_attestations_not_hidden(self):
        rows=[x for x in self.reports['receipt_ir']['items'] if x['stratum']=='trusted_reviewer_failure']
        self.assertEqual(2,len(rows));self.assertTrue(all(x['semantic_safe_decision_match'] is False for x in rows))
    def test_receipts_not_claimed_as_humans(self):
        s=json.loads((self.output/'summary.json').read_text());self.assertEqual(0,s['actual_human_reviews'])
        self.assertEqual(0,s['actual_model_runs']);self.assertEqual(20,s['simulated_receipt_count']);self.assertEqual(22,s['simulated_reviewed_paths'])
    def test_benign_review_recovery_has_known_cost(self):
        self.assertEqual(6,self.reports['receipt_ir']['groups']['reviewed_benign']['closed'])
        self.assertEqual(0,self.reports['gate_v2_ir']['groups']['reviewed_benign']['closed'])
    def test_unknown_evidence_cannot_be_overridden(self):
        self.assertEqual(4,self.reports['receipt_ir']['groups']['policy_nonclosure']['needs_evidence'])
    def test_reference_source_paths_are_retained(self):
        self.assertTrue(all(x['checks']['source_refs'] for x in self.reports['receipt_ir']['items']))
