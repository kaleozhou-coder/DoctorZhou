"""Export only allowlisted policy material, never evaluator cases or labels.

This packaging boundary is not an OS security sandbox. Give the resulting zip
alone to future model workers; do not give them the repository root.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile
from benchmark_eval import digest, inside, load_json, verify_freeze

FORBIDDEN_KEYS = {'case_id', 'expected_decision', 'label_basis', 'required_evidence_ids', 'required_reason_codes'}


def inspect_keys(value):
    if isinstance(value, dict):
        if FORBIDDEN_KEYS.intersection(value):
            raise ValueError(f'Evaluator fields in model material: {sorted(FORBIDDEN_KEYS.intersection(value))}')
        for child in value.values(): inspect_keys(child)
    elif isinstance(value, list):
        for child in value: inspect_keys(child)


def export_inputs(benchmark, destination, family_ids=None):
    benchmark, destination = Path(benchmark), Path(destination)
    if destination.resolve().is_relative_to(benchmark.resolve()):
        raise ValueError('Export destination must not be inside the frozen benchmark')
    verified = verify_freeze(benchmark)
    manifest = load_json(benchmark/'manifest.json')
    families = manifest.get('families')
    if not isinstance(families, list): raise ValueError('Manifest requires families list')
    known_ids = [row['family_id'] for row in families]
    if len(known_ids) != len(set(known_ids)): raise ValueError('Duplicate family IDs')
    if family_ids is not None and set(family_ids)-set(known_ids):
        raise ValueError('Requested family does not exist')
    files, public_rows = {}, []
    for row in families:
        family_id = row['family_id']
        if family_ids is not None and family_id not in family_ids: continue
        rel = row.get('model_materials')
        if not isinstance(rel, str) or not rel.startswith('model-facing/') or not rel.endswith('.json'):
            raise ValueError('Only explicitly declared model-facing JSON may be exported')
        path = inside(benchmark, rel)
        material = load_json(path)
        inspect_keys(material)
        if material.get('family_id') != family_id:
            raise ValueError('Material family differs from manifest')
        if rel in files: raise ValueError('Model material path used by multiple families')
        files[rel] = path.read_bytes()
        public_rows.append({'family_id': family_id, 'split': row['split'], 'model_materials': rel, 'sha256': digest(path)})
    if not files: raise ValueError('No model materials selected')
    public_manifest = {
        'kind': 'model_construction_inputs_only',
        'benchmark_freeze_sha256': verified['freeze_sha256'],
        'families': public_rows,
        'boundary': 'Contains policy/schema materials only; no hidden transaction cases, labels, data-authoring script, reference implementation or model results.',
        'security_note': 'A zip allowlist is not filesystem access control. Future construction workers must receive this export alone.'
    }
    files['model-input-manifest.json'] = (json.dumps(public_manifest, ensure_ascii=False, indent=2)+'\n').encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Fixed metadata makes the archive byte-reproducible for the same inputs.
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, content)
    return {'export_sha256':digest(destination),'files':sorted(files),'family_n':len(public_rows),
            'benchmark_freeze_sha256':verified['freeze_sha256']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--family',action='append')
    args=p.parse_args()
    print(json.dumps(export_inputs(args.benchmark,args.output,args.family),ensure_ascii=False,indent=2))

if __name__ == '__main__':main()
