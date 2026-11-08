"""Runner-only tests with self-authored toy records, never benchmark labels."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import run_policy_baseline as runner


class RunnerTests(unittest.TestCase):
    def test_empty_freeze_rejected(self):
        with self.assertRaises(ValueError):
            runner.verify_implementation(Path('.'), {'files': {}})

    def test_changed_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = {}
            paths = ['src/policy_baseline.py', 'src/run_policy_baseline.py', 'src/benchmark_eval.py',
                     'tests/test_policy_baseline.py', 'tests/test_policy_baseline_runner.py']
            paths += [f'benchmark/v1/model-facing/F{i:02d}/materials.json' for i in range(1, 7)]
            for name in paths:
                p = root / name
                p.parent.mkdir(exist_ok=True, parents=True)
                p.write_text('original')
                files[str(p.relative_to(root))] = runner.sha(p)
            runner.verify_implementation(root, {'files': files})
            (root / 'src' / 'policy_baseline.py').write_text('changed')
            with self.assertRaises(ValueError):
                runner.verify_implementation(root, {'files': files})

    def test_escaping_freeze_rejected(self):
        paths = ['src/policy_baseline.py', 'src/run_policy_baseline.py', 'src/benchmark_eval.py',
                 'tests/test_policy_baseline.py', 'tests/test_policy_baseline_runner.py']
        paths += [f'benchmark/v1/model-facing/F{i:02d}/materials.json' for i in range(1, 7)]
        files = {k: '0' * 64 for k in paths}
        files = {'../escape': '0' * 64, **files}
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            runner.verify_implementation(Path('.'), {'files': files})

    def test_nonempty_output_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'out'
            output.mkdir()
            (output / 'first-run.txt').write_text('preserve')
            with self.assertRaisesRegex(ValueError, 'Output directory must be empty'):
                runner.run(Path(td), output, Path(td) / 'missing-freeze.json')

    def test_all_submissions_written_before_label_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / 'out'
            freeze = root / 'freeze.json'
            runner.write(freeze, {'files': {}, 'benchmark_freeze_sha256': '0' * 64})
            for i, split in enumerate(runner.SPLITS):
                family = f'TOY{i}'
                runner.write(root / 'model-facing' / family / 'materials.json',
                             {'family_id': family, 'split': split})
                runner.write(root / 'evaluator' / 'inputs' / (family + '.json'),
                             {'cases': [{'case_id': family, 'family_id': family}]})
            original_load = runner.load_json
            def observed_load(path):
                if Path(path).name == 'labels.json':
                    for split in runner.SPLITS:
                        self.assertTrue((output / f'{split}.submission.json').exists())
                    raise RuntimeError('label phase reached after persistence')
                return original_load(path)
            with patch.object(runner, 'verify_implementation'), \
                 patch.object(runner, 'verify_freeze', return_value={'freeze_sha256': '0' * 64}), \
                 patch.object(runner, 'predict_case', side_effect=lambda c, m: {'case_id': c['case_id']}), \
                 patch.object(runner, 'sha', return_value='0' * 64), \
                 patch.object(runner, 'load_json', side_effect=observed_load):
                with self.assertRaisesRegex(RuntimeError, 'label phase'):
                    runner.run(root, output, freeze)


if __name__ == '__main__':
    unittest.main()
