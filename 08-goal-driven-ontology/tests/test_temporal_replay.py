import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from temporal_replay import Method, replay, study, run, validate, DEPENDENCIES
ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/synthetic/stage-09/trajectories.json').read_text())

class TemporalReplayTests(unittest.TestCase):
    def test_full_and_incremental_match_labels(self):
        result = study(DATA)['summary']['methods']
        for mode in ('full', 'incremental'):
            self.assertEqual(result[mode]['correct'], 36)
            self.assertEqual(result[mode]['same_event_withdrawals'], 11)
            self.assertEqual(result[mode]['false_close'], 0)
    def test_negative_control_fails(self):
        r = study(DATA)['summary']['methods']['stale_negative_control']
        self.assertEqual(r['false_close'], 15)
        self.assertEqual(r['same_event_withdrawals'], 0)
        self.assertEqual(r['nonclose_at_withdrawal_event'], 1)
    def test_resource_counts(self):
        r = study(DATA)['summary']['methods']
        self.assertEqual(r['full']['predicate_evaluations'], 144)
        self.assertEqual(r['incremental']['predicate_evaluations'], 48)
        self.assertEqual(r['incremental']['dependency_group_checks'], 120)
    def test_label_change_cannot_change_predictions(self):
        changed = copy.deepcopy(DATA)
        for t in changed['trajectories']:
            for e in t['events']: e['expected'] = 'review'
        self.assertEqual(study(DATA)['predictions'], study(changed)['predictions'])
    def test_future_cannot_change_prefix(self):
        for t in DATA['trajectories']:
            for mode in ('full', 'incremental', 'stale_negative_control'):
                for stop in range(1, 6):
                    short = {**t, 'events': t['events'][:stop]}
                    self.assertEqual(replay(t, mode)[:stop], replay(short, mode))
    def test_duplicate_no_predicate_work(self):
        m = Method('incremental'); state = DATA['trajectories'][0]['initial_state']
        m.step(state)
        self.assertEqual(m.step(state)['predicate_evaluations'], 0)
    def test_memo_no_predicate_work(self):
        m = Method('incremental'); state = DATA['trajectories'][0]['initial_state']
        m.step(state)
        self.assertEqual(m.step({**state, 'memo':'changed'})['predicate_evaluations'], 0)
    def test_policy_dependency_included(self):
        m = Method('incremental'); state = {**DATA['trajectories'][0]['initial_state'], 'authorized':False,'require_authority':False}
        self.assertEqual(m.step(state)['decision'], 'close')
        self.assertEqual(m.step({**state, 'require_authority':True})['decision'], 'review')
    def test_input_mutation_does_not_mutate_previous(self):
        m = Method('incremental'); state = dict(DATA['trajectories'][0]['initial_state'])
        m.step(state); state['acceptance'] = 'revoked'
        self.assertEqual(m.step(state)['decision'], 'review')
    def test_unknown_fields_rejected(self):
        with self.assertRaises(ValueError): validate({**DATA['trajectories'][0]['initial_state'], 'x':1})
    def test_bad_types_rejected(self):
        for key,value in [('linked',1),('authorized','yes'),('require_authority',None),('invoice_qty',True),('accepted_qty',-1),('acceptance','shipped')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate({**DATA['trajectories'][0]['initial_state'],key:value})
    def test_duplicate_ids_rejected(self):
        changed = copy.deepcopy(DATA); changed['trajectories'].append(changed['trajectories'][0])
        with self.assertRaises(ValueError): study(changed)
    def test_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d); (output/'existing').write_text('keep')
            with self.assertRaises(ValueError): run(ROOT,output)
            self.assertEqual((output/'existing').read_text(),'keep')
    def test_repeat_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';run(ROOT,a);run(ROOT,b)
            self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()}, {p.name:p.read_bytes() for p in b.iterdir()})
    def test_all_single_field_changes_match_full(self):
        state=DATA['trajectories'][0]['initial_state']
        for key,values in {'linked':[None,False,True],'invoice_qty':[None,1,12],'accepted_qty':[None,0,12], 'acceptance':[None,'rejected','revoked','conflict','accepted'],'authorized':[None,False,True], 'require_authority':[False,True], 'memo':['other']}.items():
            for value in values:
                inc=Method('incremental');inc.step(state)
                new={**state,key:value}
                self.assertEqual(inc.step(new)['decision'],Method('full').step(new)['decision'])
