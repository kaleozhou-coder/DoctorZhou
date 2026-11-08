"""Execute frozen manual rules before loading labels; no model calls.

The v1 scorer has only engineering_probe/model_run tags. Rule executions use
engineering_probe plus explicit method=manual_policy_baseline. Unlike the v1
label-replay probes, the prediction phase does not parse labels or registry.
Integrity verification reads their bytes solely for hashing beforehand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from benchmark_eval import load_json, score_submission, verify_freeze, check_string_list, SPLITS
from policy_baseline import predict_case


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def verify_implementation(project, freeze):
    required = {'src/policy_baseline.py', 'src/run_policy_baseline.py', 'src/benchmark_eval.py'}
    required.update({'tests/test_policy_baseline.py', 'tests/test_policy_baseline_runner.py'})
    required.update(f'benchmark/v1/model-facing/F{i:02d}/materials.json' for i in range(1, 7))
    files = freeze.get('files')
    if not isinstance(files, dict) or not required.issubset(files):
        raise ValueError('Implementation freeze must cover code, tests and all six policies')
    for relative, expected in files.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe implementation freeze path')
        if not (project / path).resolve().is_relative_to(project.resolve()):
            raise ValueError('Implementation freeze path escapes project')
        if sha(project / path) != expected:
            raise ValueError(f'Implementation freeze mismatch: {relative}')


def run(benchmark, output, implementation_freeze):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty; preserve prior run and use a new directory')
    project = Path(__file__).resolve().parents[1]
    freeze = load_json(implementation_freeze)
    verify_implementation(project, freeze)
    # Hash-only integrity verification reads all benchmark bytes, including labels;
    # semantic label parsing starts only after every submission is persisted.
    verified = verify_freeze(benchmark)
    if verified['freeze_sha256'] != freeze.get('benchmark_freeze_sha256'):
        raise ValueError('Executed benchmark differs from the implementation freeze')
    submissions = {}
    # All predictions are completed and persisted before labels are loaded.
    for split in SPLITS:
        predictions = []
        for material_path in sorted((benchmark / 'model-facing').glob('*/materials.json')):
            material = load_json(material_path)
            if material['split'] != split:
                continue
            case_path = benchmark / 'evaluator' / 'inputs' / (material['family_id'] + '.json')
            for case in load_json(case_path)['cases']:
                predictions.append(predict_case(case, material))
        submission = {
            'run': {'run_id': f'stage03-manual-rules-{split}',
                    'method': 'manual_policy_baseline',
                    'execution_kind': 'engineering_probe',
                    'baseline_kind': 'deterministic_policy_program_not_label_replay',
                    'split': split,
                    'benchmark_freeze_sha256': verified['freeze_sha256'],
                    'implementation_freeze_sha256': sha(implementation_freeze),
                    'implementation_sha256': sha(project / 'src' / 'policy_baseline.py'),
                    'model_calls': 0, 'human_review_minutes': None},
            'predictions': predictions}
        write(output / f'{split}.submission.json', submission)
        submissions[split] = submission

    # Scoring phase starts here, never in the rule implementation.
    labels = load_json(benchmark / 'evaluator' / 'labels.json')
    registry_doc = load_json(benchmark / 'evaluator' / 'source-registry.json')
    registry = {(s['source_id'], loc) for s in registry_doc['sources'] for loc in s['locators']}
    summary = {'experiment': 'manual_policy_baseline', 'model_calls': 0,
               'benchmark': verified, 'implementation_freeze_sha256': sha(implementation_freeze),
               'claims': 'Structured synthetic rule execution only; not an LLM A/B or human study.',
               'splits': {}}
    for split, submission in submissions.items():
        report = score_submission(labels, submission, split, verified['freeze_sha256'], registry)
        selected = {r['case_id']: r for r in labels['cases'] if r['split'] == split}
        # Label reason-field schema is deliberately explicit; no fallback inference.
        reason_rows = []
        indexed = {p['case_id']: p for p in submission['predictions']}
        for case_id, label in sorted(selected.items()):
            check_string_list(label['required_reason_codes'], 'required_reason_codes')
            pred = indexed.get(case_id)
            predicted_reasons = pred['reason_codes'] if pred else None
            reason_rows.append({'case_id': case_id,
                                'predicted': predicted_reasons,
                                'expected': label['required_reason_codes'],
                                'correct': predicted_reasons == label['required_reason_codes']})
        report['primary_reason_audit'] = {
            'correct_n': sum(r['correct'] for r in reason_rows),
            'case_n': len(selected), 'rows': reason_rows}
        report['input_sha256'] = {'submission': sha(output / f'{split}.submission.json'),
                                  'labels': sha(benchmark / 'evaluator' / 'labels.json'),
                                  'scorer': sha(project / 'src' / 'benchmark_eval.py')}
        write(output / f'{split}.report.json', report)
        summary['splits'][split] = {
            'metrics': report['metrics'], 'by_family': report['by_family'],
            'primary_reason_correct_n': report['primary_reason_audit']['correct_n'],
            'source_locator_audit': report['source_locator_audit']}
    write(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--implementation-freeze', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.benchmark, args.output, args.implementation_freeze), indent=2))


if __name__ == '__main__':
    main()
