import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from benchmark_eval import load_json, score_submission, verify_freeze


class BenchmarkScorerTests(unittest.TestCase):
    def setUp(self):
        self.labels = {'cases': [
            {'case_id':'c1','family_id':'f1','split':'test','expected_decision':'close_eligible'},
            {'case_id':'c2','family_id':'f1','split':'test','expected_decision':'needs_evidence'},
            {'case_id':'c3','family_id':'f2','split':'test','expected_decision':'needs_review'}]}
        self.sub = {'run': {'run_id':'probe','method':'truth-probe','execution_kind':'engineering_probe',
                            'benchmark_freeze_sha256':'a'*64,'split':'test'},
                    'predictions': [{'case_id':r['case_id'],'decision':r['expected_decision']} for r in self.labels['cases']]}
    def score(self, sub=None):
        return score_submission(self.labels, sub or self.sub, 'test', 'a'*64)
    def test_perfect_engineering_probe(self):
        m=self.score()['metrics']
        self.assertEqual(1.0,m['exact_decision_accuracy'])
        self.assertEqual(1.0,m['positive_close_recall'])
        self.assertEqual(0,m['false_close_n'])
    def test_empty_output_not_success(self):
        self.sub['predictions']=[]
        m=self.score()['metrics']
        self.assertEqual(0,m['completion_rate'])
        self.assertEqual(0,m['positive_close_recall'])
        self.assertEqual(0,m['exact_decision_accuracy'])
        self.assertEqual(1,m['conservative_false_close_rate_if_missing_negatives_close'])
    def test_refuse_all_has_zero_recall(self):
        for r in self.sub['predictions']:r['decision']='needs_review'
        m=self.score()['metrics']
        self.assertEqual(0,m['false_close_rate'])
        self.assertEqual(0,m['positive_close_recall'])
        self.assertAlmostEqual(1/3,m['exact_decision_accuracy'])
    def test_close_all_has_maximal_risk(self):
        for r in self.sub['predictions']:r['decision']='close_eligible'
        m=self.score()['metrics']
        self.assertEqual(1,m['false_close_rate'])
        self.assertEqual(1,m['positive_close_recall'])
    def test_missing_cannot_improve_denominator(self):
        self.sub['predictions']=self.sub['predictions'][1:]
        m=self.score()['metrics']
        self.assertEqual(3,m['case_n'])
        self.assertEqual(0,m['positive_close_recall'])
        self.assertAlmostEqual(2/3,m['exact_decision_accuracy'])
    def test_duplicate_predictions_rejected(self):
        self.sub['predictions'].append(self.sub['predictions'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate prediction'):self.score()
    def test_wrong_split_ids_rejected(self):
        self.sub['predictions'][0]['case_id']='development-secret'
        with self.assertRaisesRegex(ValueError,'wrong-split'):self.score()
    def test_unknown_state_rejected(self):
        self.sub['predictions'][0]['decision']='payment_approved'
        with self.assertRaisesRegex(ValueError,'Invalid decision'):self.score()
    def test_hash_mismatch_rejected(self):
        self.sub['run']['benchmark_freeze_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'hash differs'):self.score()
    def test_family_leakage_rejected(self):
        self.labels['cases'][1]['split']='development'
        with self.assertRaisesRegex(ValueError,'split leakage'):self.score()
    def test_missing_run_instrumentation_rejected(self):
        self.sub['run']['execution_kind']='model_run'
        with self.assertRaisesRegex(ValueError,'Model run requires'):self.score()
    def test_locator_existence_not_semantic_support(self):
        self.sub['predictions'][0]['source_refs']=[{'source_id':'P','locator':'p1'}]
        result=score_submission(self.labels,self.sub,'test','a'*64,{('P','p1')})
        self.assertEqual(1,result['source_locator_audit']['existence_rate'])
        self.assertIsNone(result['source_locator_audit']['semantic_support_rate'])
    def test_no_human_savings_inferred(self):
        self.assertIsNone(self.score()['human_time_savings'])
    def test_duplicate_label_ids_rejected(self):
        self.labels['cases'].append(copy.deepcopy(self.labels['cases'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate label'):self.score()
    def test_none_positive_metric_is_null(self):
        self.labels['cases'][0]['expected_decision']='needs_evidence'
        self.assertIsNone(self.score()['metrics']['positive_close_recall'])
    def test_freeze_detects_tampering_and_extra_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); f=root/'a.txt';f.write_text('original')
            (root/'FILE_SHA256.json').write_text(json.dumps({'a.txt':hashlib.sha256(f.read_bytes()).hexdigest()}))
            self.assertEqual(1,verify_freeze(root)['files_verified'])
            f.write_text('edited')
            with self.assertRaisesRegex(ValueError,'changed'):verify_freeze(root)
            f.write_text('original');(root/'extra.txt').write_text('extra')
            with self.assertRaisesRegex(ValueError,'inventory'):verify_freeze(root)
    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'FILE_SHA256.json').write_text(json.dumps({'../external.txt':'a'*64}))
            with self.assertRaises(ValueError):verify_freeze(root)
    def test_strict_json_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'bad.json'
            for contents in ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": 1e999}', '{"nested": [1e999]}']:
                f.write_text(contents)
                with self.assertRaises(ValueError):load_json(f)
    def test_malformed_rows_rejected_deliberately(self):
        for value in (None, 3, 'str'):
            changed=copy.deepcopy(self.sub);changed['predictions']=[value]
            with self.assertRaisesRegex(ValueError,'row must be an object'):self.score(changed)
    def test_model_metadata_types(self):
        self.sub['run'].update(execution_kind='model_run',model_identifier='example-model',model_snapshot=None,
                              raw_output_sha256='b'*64,ontology_artifact_sha256='c'*64,
                              input_tokens=0,output_tokens=0,wall_seconds=0,human_review_minutes=0,
                              sampling_parameters={})
        self.assertEqual(1,self.score()['metrics']['completion_rate'])
        for key,value in [('raw_output_sha256','not-a-hash'),('ontology_artifact_sha256','invalid'),
                          ('input_tokens',1.5),('output_tokens',True),('model_snapshot',{}),
                          ('sampling_parameters','garbage'),('wall_seconds',float('inf'))]:
            changed=copy.deepcopy(self.sub);changed['run'][key]=value
            with self.subTest(field=key):
                with self.assertRaises(ValueError):self.score(changed)
    def test_external_manifest_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            external=Path(tmp)/'manifest.json';external.write_text('{}')
            (root/'FILE_SHA256.json').symlink_to(external)
            with self.assertRaisesRegex(ValueError,'escapes'):verify_freeze(root)
    def test_payment_authorization_rejected(self):
        for value in (True, 0, None, 'false'):
            changed=copy.deepcopy(self.sub);changed['predictions'][0]['payment_authorized']=value
            with self.assertRaisesRegex(ValueError,'never authorize payment'):self.score(changed)
    def test_evidence_pointers_are_audited(self):
        self.sub['predictions'][0]['evidence_ids']=['P#p1','FAKE#x']
        self.sub['predictions'][0]['source_refs']=[{'source_id':'P','locator':'p1'}]
        result=score_submission(self.labels,self.sub,'test','a'*64,{('P','p1')})
        self.assertEqual(2,result['source_locator_audit']['checked_n'])
        self.assertEqual(0.5,result['source_locator_audit']['existence_rate'])
    def test_empty_source_refs_rejected(self):
        self.sub['predictions'][0]['source_refs']=[{'source_id':'','locator':'p1'}]
        with self.assertRaisesRegex(ValueError,'source_refs'):self.score()
    def test_evidence_pointer_shape_rejected(self):
        for value in ('e1','P#','#p1','P#p1#p2'):
            changed=copy.deepcopy(self.sub);changed['predictions'][0]['evidence_ids']=[value]
            with self.assertRaisesRegex(ValueError,'source_id#locator'):self.score(changed)
    def test_duplicate_evidence_ids_rejected(self):
        self.sub['predictions'][0]['evidence_ids']=['e1','e1']
        with self.assertRaisesRegex(ValueError,'duplicates'):self.score()

if __name__ == '__main__':unittest.main()
