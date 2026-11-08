"""Strict prospective-benchmark scorer. This is infrastructure, not a model.

No network, no inferred labels, no model calls. Missing outputs remain in every
applicable denominator. Locator validity and semantic support are separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

STATES = ('close_eligible', 'needs_evidence', 'needs_review')
SPLITS = ('development', 'validation', 'test')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reject_constant(value):
    raise ValueError(f'Nonstandard JSON constant: {value}')


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj


def ensure_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite JSON number')
    if isinstance(value, dict):
        for item in value.values(): ensure_finite(item)
    if isinstance(value, list):
        for item in value: ensure_finite(item)


def load_json(path):
    result = json.loads(Path(path).read_text(), parse_constant=reject_constant,
                        object_pairs_hook=unique_object)
    ensure_finite(result)
    return result


def inside(root, relative):
    relative_path = Path(relative)
    if relative_path.is_absolute() or '..' in relative_path.parts:
        raise ValueError(f'Unsafe relative path: {relative}')
    path = root / relative_path
    # A sealed input must not depend on content outside its root through symlinks.
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes benchmark: {relative}')
    return path


def verify_freeze(root):
    root = Path(root)
    manifest_path = inside(root, 'FILE_SHA256.json')
    frozen = load_json(manifest_path)
    if not isinstance(frozen, dict) or not frozen:
        raise ValueError('FILE_SHA256.json must contain a nonempty path:hash object')
    actual = {str(p.relative_to(root)) for p in root.rglob('*')
              if p.is_file() and p != manifest_path}
    if actual != set(frozen):
        raise ValueError(f'Freeze inventory mismatch: missing={sorted(set(frozen)-actual)}, extra={sorted(actual-set(frozen))}')
    for rel, expected in sorted(frozen.items()):
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError(f'Invalid SHA256 for {rel}')
        if digest(inside(root, rel)) != expected:
            raise ValueError(f'Frozen file changed: {rel}')
    return {'files_verified': len(frozen), 'freeze_sha256': digest(manifest_path)}


def unique_index(rows, key, kind):
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f'{kind} row must be an object')
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f'{kind} must have nonempty {key}')
        if value in result:
            raise ValueError(f'Duplicate {kind} ID: {value}')
        result[value] = row
    return result


def validate_labels(labels):
    if not isinstance(labels, dict) or not isinstance(labels.get('cases'), list) or not labels['cases']:
        raise ValueError('Labels must contain nonempty cases list')
    rows = labels['cases']
    unique_index(rows, 'case_id', 'label')
    family_splits = {}
    for row in rows:
        if row.get('expected_decision') not in STATES:
            raise ValueError(f'Invalid expected_decision in {row["case_id"]}')
        if row.get('split') not in SPLITS or not isinstance(row.get('family_id'), str) or not row['family_id']:
            raise ValueError(f'Invalid family/split in {row["case_id"]}')
        family = row['family_id']
        if family in family_splits and family_splits[family] != row['split']:
            raise ValueError(f'Family split leakage: {family}')
        family_splits[family] = row['split']
    return rows


def check_string_list(values, field):
    if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
        raise ValueError(f'{field} must be a list of nonempty strings')
    if len(values) != len(set(values)):
        raise ValueError(f'{field} contains duplicates')


def validate_submission(submission, selected, split):
    if not isinstance(submission, dict):
        raise ValueError('Submission must be an object')
    ensure_finite(submission)
    meta = submission.get('run')
    if not isinstance(meta, dict):
        raise ValueError('Submission requires run metadata')
    for key in ('run_id', 'method', 'execution_kind', 'benchmark_freeze_sha256'):
        if not isinstance(meta.get(key), str) or not meta[key]:
            raise ValueError(f'Missing run.{key}')
    if not re.fullmatch(r'[0-9a-f]{64}', meta['benchmark_freeze_sha256']):
        raise ValueError('benchmark_freeze_sha256 must be a lowercase SHA256 hex digest')
    if meta['execution_kind'] not in ('engineering_probe', 'model_run'):
        raise ValueError('execution_kind must distinguish engineering_probe/model_run')
    if meta.get('split') != split:
        raise ValueError('Submission run.split differs from requested split')
    if meta['execution_kind'] == 'model_run':
        # Unavailable usage can be null, never silently replaced with estimates.
        for key in ('model_identifier', 'model_snapshot', 'raw_output_sha256',
                    'ontology_artifact_sha256', 'input_tokens', 'output_tokens',
                    'wall_seconds', 'human_review_minutes', 'sampling_parameters'):
            if key not in meta:
                raise ValueError(f'Model run requires metadata key {key} (null allowed where unavailable)')
        for key in ('model_identifier', 'raw_output_sha256', 'ontology_artifact_sha256'):
            if not isinstance(meta[key], str) or not meta[key]:
                raise ValueError(f'Model run must identify {key}')
        for key in ('raw_output_sha256', 'ontology_artifact_sha256'):
            if not re.fullmatch(r'[0-9a-f]{64}', meta[key]):
                raise ValueError(f'Invalid SHA256: {key}')
        if meta['model_snapshot'] is not None and (not isinstance(meta['model_snapshot'], str) or not meta['model_snapshot']):
            raise ValueError('model_snapshot must be null or a nonempty string')
        if meta['sampling_parameters'] is not None and not isinstance(meta['sampling_parameters'], dict):
            raise ValueError('sampling_parameters must be null or an object')
        for key in ('input_tokens', 'output_tokens'):
            if meta[key] is not None and (isinstance(meta[key], bool) or not isinstance(meta[key], int)):
                raise ValueError(f'run.{key} must be an integer or null')
        for key in ('input_tokens', 'output_tokens', 'wall_seconds', 'human_review_minutes'):
            value = meta[key]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise ValueError(f'Invalid run.{key}')
    predictions = submission.get('predictions')
    if not isinstance(predictions, list):
        raise ValueError('Submission requires predictions list')
    indexed = unique_index(predictions, 'case_id', 'prediction')
    unexpected = set(indexed) - set(selected)
    if unexpected:
        raise ValueError(f'Unknown or wrong-split prediction IDs: {sorted(unexpected)}')
    for row in indexed.values():
        allowed = {'case_id', 'decision', 'evidence_ids', 'reason_codes', 'source_refs', 'payment_authorized'}
        if set(row)-allowed:
            raise ValueError(f'Unexpected prediction fields: {sorted(set(row)-allowed)}')
        if 'payment_authorized' in row and row['payment_authorized'] is not False:
            raise ValueError('A closure recommendation must never authorize payment')
        if row.get('decision') not in STATES:
            raise ValueError(f'Invalid decision in {row["case_id"]}')
        for key in ('evidence_ids', 'reason_codes'):
            check_string_list(row.get(key, []), key)
        for pointer in row.get('evidence_ids', []):
            if pointer.count('#') != 1 or not all(pointer.split('#')):
                raise ValueError('evidence_ids must be source_id#locator pointers')
        refs = row.get('source_refs', [])
        if not isinstance(refs, list) or any(not isinstance(x, dict) or not isinstance(x.get('source_id'), str)
                                           or not isinstance(x.get('locator'), str) or not x['source_id'] or not x['locator'] for x in refs):
            raise ValueError('source_refs must be source_id/locator objects')
    return indexed


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def metrics(rows):
    negatives = [r for r in rows if r['expected_decision'] != 'close_eligible']
    positives = [r for r in rows if r['expected_decision'] == 'close_eligible']
    missing = [r for r in rows if r['decision'] is None]
    false_closes = [r for r in negatives if r['decision'] == 'close_eligible']
    true_closes = [r for r in positives if r['decision'] == 'close_eligible']
    negative_missing = sum(r['decision'] is None for r in negatives)
    return {
        'case_n': len(rows), 'positive_n': len(positives), 'negative_n': len(negatives),
        'missing_n': len(missing), 'completion_rate': ratio(len(rows)-len(missing), len(rows)),
        'exact_decision_correct_n': sum(r['decision'] == r['expected_decision'] for r in rows),
        'exact_decision_accuracy': ratio(sum(r['decision'] == r['expected_decision'] for r in rows), len(rows)),
        'false_close_n': len(false_closes), 'false_close_rate': ratio(len(false_closes), len(negatives)),
        'positive_close_recall': ratio(len(true_closes), len(positives)),
        'conservative_false_close_rate_if_missing_negatives_close': ratio(len(false_closes)+negative_missing, len(negatives)),
        'decision_counts': dict(Counter(r['decision'] or 'MISSING' for r in rows)),
        'false_close_case_ids': [r['case_id'] for r in false_closes],
        'missing_case_ids': [r['case_id'] for r in missing],
    }


def score_submission(labels, submission, split, freeze_sha256, source_registry=None):
    ensure_finite(labels)
    selected = {r['case_id']: r for r in validate_labels(labels) if r['split'] == split}
    if not selected:
        raise ValueError(f'No cases for split: {split}')
    predictions = validate_submission(submission, selected, split)
    if submission['run']['benchmark_freeze_sha256'] != freeze_sha256:
        raise ValueError('Submission benchmark hash differs from frozen package')
    rows = []
    refs_total, refs_valid = 0, 0
    for case_id, label in sorted(selected.items()):
        prediction = predictions.get(case_id)
        rows.append({'case_id': case_id, 'family_id': label['family_id'],
                     'expected_decision': label['expected_decision'],
                     'decision': prediction['decision'] if prediction else None,
                     'evidence_ids': prediction.get('evidence_ids', []) if prediction else [],
                     'reason_codes': prediction.get('reason_codes', []) if prediction else []})
        if prediction and source_registry is not None:
            pointers = {(r['source_id'], r['locator']) for r in prediction.get('source_refs', [])}
            pointers.update(tuple(value.split('#')) for value in prediction.get('evidence_ids', []))
            for pointer in pointers:
                refs_total += 1
                refs_valid += pointer in source_registry
    by_family = {fid: metrics([r for r in rows if r['family_id'] == fid])
                 for fid in sorted({r['family_id'] for r in rows})}
    return {
        'schema_version': '1.0', 'run': submission['run'],
        'evaluation_type': 'synthetic_prospective_benchmark', 'split': split,
        'metrics': metrics(rows), 'by_family': by_family,
        'family_n': len(by_family),
        'source_locator_audit': {'registry_supplied': source_registry is not None, 'checked_n': refs_total, 'existing_n': refs_valid,
                                 'existence_rate': ratio(refs_valid, refs_total),
                                 'semantic_support_rate': None,
                                 'note': 'A locator existing does not show that the cited text supports the claim.'},
        'human_review_minutes': submission['run'].get('human_review_minutes'),
        'human_time_savings': None,
        'intervals': None,
        'interval_note': 'No population confidence claim: few deliberately authored families, not an IID sample.',
        'success_or_superiority_claim': None,
        'notes': ['Missing predictions remain in accuracy and positive-recall denominators.',
                  'Missing negatives are not silently considered safe; conservative risk is also reported.',
                  'Three states are not interchangeable; low false-close risk alone is not success.',
                  'Source support, ontology quality, human time, and real-world effectiveness require separate assessment.'],
        'predictions': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--submission', type=Path)
    parser.add_argument('--split', choices=SPLITS, default='test')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    verified = verify_freeze(args.benchmark)
    if args.verify_only:
        print(json.dumps(verified, indent=2))
        return
    if not args.submission or not args.output:
        parser.error('--submission and --output are required unless --verify-only')
    labels = load_json(args.benchmark / 'evaluator' / 'labels.json')
    registry_path = args.benchmark / 'evaluator' / 'source-registry.json'
    registry = None
    if registry_path.exists():
        registry_document = load_json(registry_path)
        if not isinstance(registry_document, dict): raise ValueError('Source registry must be an object')
        source_rows = registry_document.get('sources')
        if not isinstance(source_rows, list): raise ValueError('Source registry requires sources list')
        unique_index(source_rows, 'source_id', 'source registry')
        registry = set()
        for row in source_rows:
            check_string_list(row.get('locators'), 'locators')
            registry.update((row['source_id'], loc) for loc in row['locators'])
    result = score_submission(labels, load_json(args.submission), args.split, verified['freeze_sha256'], registry)
    result['input_sha256'] = {'labels': digest(args.benchmark/'evaluator'/'labels.json'),
                              'submission': digest(args.submission), 'scorer': digest(__file__)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.output), 'metrics': result['metrics']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
