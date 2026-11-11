"""Versioned regression and adversarial artifact tests. Not business samples."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import rule_ir_v2 as old
import rule_ir_v3 as ir
import test_rule_ir_v2 as previous


class ScalarCompatibilityTests(previous.ScalarCompatibilityTests):
    def setUp(self):
        p = patch.object(previous, 'ir', ir)
        p.start(); self.addCleanup(p.stop)
        super().setUp()


class CollectionCompatibilityTests(previous.CollectionTests):
    def setUp(self):
        p = patch.object(previous, 'ir', ir)
        p.start(); self.addCleanup(p.stop)
        super().setUp()
        self.p['version'] = ir.VERSION


class ArtifactBoundaryTests(unittest.TestCase):
    def setUp(self):
        ref = [{'source_id': 'policy', 'locator': 'p1'}]
        self.p = {'version': ir.VERSION,
                  'fields': {'x': {'path': ['x'], 'type': 'integer', 'enum': [1]}},
                  'rules': [{'id': 'rule', 'when': {'op': 'literal', 'type': 'boolean', 'value': True},
                             'decision': 'close_eligible', 'reason': 'fixture_only', 'source_refs': ref}],
                  'default': {'decision': 'needs_review', 'reason': 'fallback', 'source_refs': ref}}

    def rejected(self, artifact):
        with self.assertRaises(ir.RuleError):
            ir.validate(artifact)
        # Rejection must precede rule traversal, even if early rules always close.
        out = ir.evaluate(artifact, {})
        self.assertEqual(out['decision'], 'needs_review')
        self.assertEqual(out['reason_codes'], ['invalid_artifact'])
        self.assertEqual(out['trace'], [])
        self.assertIs(out['payment_authorized'], False)

    def test_original_exploit_retained_and_closed_in_v3(self):
        p = copy.deepcopy(self.p)
        p['fields']['x']['enum'] = [None]
        p['rules'] = []
        p['default'] = {'decision': 'close_eligible', 'reason': 'bypass', 'source_refs': []}
        legacy = copy.deepcopy(p); legacy['version'] = old.VERSION
        self.assertIs(old.validate(legacy), old.UNKNOWN)
        self.assertEqual(old.evaluate(legacy, {})['decision'], 'close_eligible')
        self.rejected(p)

    def test_null_every_scalar_kind(self):
        for kind in ir.TYPES:
            with self.subTest(kind=kind):
                self.p['fields']['x'].update(type=kind, enum=[None])
                self.rejected(self.p)

    def test_nested_null_and_missing_enum_members(self):
        record = {'kind': 'record', 'fields': {'id': 'string', 'tags': {'kind': 'set', 'items': 'string'}}}
        for kind, value in [
                ({'kind': 'array', 'items': 'integer'}, [None]),
                ({'kind': 'set', 'items': 'string'}, [None]),
                (record, {'id': 'a'}),
                (record, {'id': None, 'tags': []}),
                (record, {'id': 'a', 'tags': [None]}),
                ({'kind': 'array', 'items': record}, [{'id': 'a'}])]:
            with self.subTest(kind=kind, value=value):
                self.p['fields']['x'].update(type=kind, enum=[value])
                self.rejected(self.p)

    def test_later_invalid_fields_not_hidden(self):
        for bad in ({'path': [], 'type': 'string'}, {'path': ['bad'], 'type': 'not-a-type'}):
            self.p['fields']['bad'] = bad
            self.rejected(self.p)

    def test_null_unused_field_cannot_hide_invalid_rules(self):
        self.p['fields']['x']['enum'] = [None]
        for rules in ([], None, [{}]):
            with self.subTest(rules=rules):
                self.p['rules'] = rules
                self.rejected(self.p)

    def test_valid_enum_does_not_skip_default_validation(self):
        self.p['default']['decision'] = 'close_eligible'
        self.rejected(self.p)

    def test_valid_enum_does_not_skip_refs(self):
        self.p['rules'][0]['source_refs'] = []
        self.rejected(self.p)

    def test_validation_requires_explicit_true(self):
        for value in (None, ir.UNKNOWN, False, True, {}, {'valid': False}, {'valid': 1}, {'valid': 'true'}):
            with self.subTest(value=str(value)), patch.object(ir, 'validate', return_value=value):
                self.assertEqual(ir.evaluate(self.p, {})['reason_codes'], ['invalid_artifact'])

    def test_duplicate_enum_normalized(self):
        for kind, values in [('integer', [1, 1]),
                             ({'kind': 'set', 'items': 'integer'}, [[1, 2], [2, 1]])]:
            with self.subTest(kind=kind):
                self.p['fields']['x'].update(type=kind, enum=values)
                self.rejected(self.p)

    def test_complete_collection_enum_valid_and_order_insensitive(self):
        self.p['fields']['x'].update(type={'kind': 'set', 'items': 'integer'}, enum=[[2, 1]])
        self.p['rules'][0]['when'] = {'op': 'eq', 'left': {'op': 'count', 'arg': {'op': 'field', 'name': 'x'}},
                                    'right': {'op': 'literal', 'type': 'integer', 'value': 2}}
        self.assertIs(ir.validate(self.p)['valid'], True)
        for data in ([1, 2], [2, 1]):
            self.assertEqual(ir.evaluate(self.p, {'x': data})['decision'], 'close_eligible')
        self.assertEqual(ir.evaluate(self.p, {'x': [1, 3]})['reason_codes'], ['malformed_input'])

    def test_runtime_null_still_unknown(self):
        self.p['rules'][0]['when'] = {'op': 'eq', 'left': {'op': 'field', 'name': 'x'},
                                    'right': {'op': 'literal', 'type': 'integer', 'value': 1}}
        for facts in ({}, {'x': None}):
            self.assertEqual(ir.evaluate(self.p, facts)['reason_codes'], ['condition_unknown'])

    def test_unknown_cannot_mask_duplicate_set_members(self):
        self.p['fields']['x'] = {'path': ['x'], 'type': {'kind': 'set', 'items': 'integer'}}
        comparison = {'op': 'eq', 'left': {'op': 'count', 'arg': {'op': 'field', 'name': 'x'}},
                      'right': {'op': 'literal', 'type': 'integer', 'value': 1}}
        self.p['rules'][0]['when'] = {'op': 'any', 'args': [
            {'op': 'literal', 'type': 'boolean', 'value': True}, comparison]}
        for values in ([1, 1], [None, 1, 1], [1, None, 1], [1, 1, None]):
            with self.subTest(values=values):
                self.assertEqual(ir.evaluate(self.p, {'x': values})['reason_codes'], ['malformed_input'])
        # Unique known values + null remain UNKNOWN; true OR UNKNOWN is true.
        self.assertEqual(ir.evaluate(self.p, {'x': [None, 1]})['decision'], 'close_eligible')

    def test_v2_tag_rejected_by_v3(self):
        self.p['version'] = old.VERSION
        self.rejected(self.p)

    def test_structural_validity_not_semantic_correctness(self):
        # An unconditional close rule is structurally valid: no safety proof claimed.
        self.assertIs(ir.validate(self.p)['valid'], True)
        self.assertEqual(ir.evaluate(self.p, {})['decision'], 'close_eligible')


if __name__ == '__main__':
    unittest.main()
