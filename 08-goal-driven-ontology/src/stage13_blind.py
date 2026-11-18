"""Prepare blinded question rows and combine frozen reviews; does not invoke AI."""
import argparse
from collections import Counter
import hashlib
import json
import random
from pathlib import Path
from stage13_artifacts import ROOT, ARMS, LAYOUTS, read, summarize

BASE = ROOT/'results/stage-13'
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

def prepare(target):
    rows=[]
    hashes={}
    for layout in LAYOUTS:
        for arm in ARMS:
            cell=f'{layout}_{arm}'
            raw=BASE/'raw'/f'{cell}.json'
            content=read(raw)
            hashes[raw.name]=hashlib.sha256(raw.read_bytes()).hexdigest()
            rows.extend((cell, row) for row in content['questions'])
    random.Random(813).shuffle(rows)
    anonymized={f'A{i:02d}':row for i,(_,row) in enumerate(rows,1)}
    reveal={f'A{i:02d}':{'cell':cell,'question':row['id']} for i,(cell,row) in enumerate(rows,1)}
    target.mkdir(parents=True,exist_ok=True)
    write(target/'blind-rows.json',anonymized)
    write(target/'reveal.json',reveal)
    write(target/'raw-final-sha256.json',hashes)

def combine(target):
    scores=read(BASE/'blind-review.json')
    mapping=read(BASE/'reveal.json')
    blind=read(BASE/'blind-rows.json')
    gold=read(ROOT/'data/stage-13/gold.json')
    executable=summarize()
    assert len(scores)==len(mapping)==len(blind)==45
    assert set(scores)==set(mapping)==set(blind)
    per_cell={cell:Counter() for cell in executable['cells']}
    paired={}
    for key, meta in mapping.items():
        q=meta['question']
        row=blind[key]
        assert q==row['id']
        s=scores[key]
        assert set(s)=={'meaning','support','wrong_citation','note'}
        assert all(type(s[k]) is bool for k in ('meaning','support','wrong_citation'))
        assert isinstance(s['note'],str) and s['note'].strip()
        required=set(gold[q]['required'])
        missing=sorted(required-set(row['sources']))
        values={'meaning':s['meaning'],'full_support':s['support'],'strict_required_ids':not missing,
                'wrong_citation':s['wrong_citation'],'unknown_candidate':row['answer'].strip().lower() in ('unknown','insufficient evidence')}
        paired.setdefault(meta['cell'],{})[q]={'blind_id':key,**values,'missing_required_ids':missing,'note':s['note']}
        counts=per_cell[meta['cell']]
        counts.update({'total':1,**{k:int(v) for k,v in values.items()}})
    totals={}
    for arm in ARMS:
        total=Counter()
        for layout in LAYOUTS:
            cell=f'{layout}_{arm}'
            c=executable['cells'][cell]
            total.update(per_cell[cell])
            total.update({k:c[k] for k in ('false_permissions','nonpermitted_gold')})
            total.update({'heldout_correct':c['correct'],'heldout_total':c['total'],'heldout_unknown':c['unknown'],'schema_invalid':int(bool(c['schema_errors']))})
            cites=set(read(BASE/'raw'/f'{cell}.json')['model']['sources'])
            total.update({'model_required_ids_complete':int({'N41','N08','N26'}<=cites)})
        totals[arm]=dict(total)
    write(target/'aggregate.json',{'totals':totals,'by_cell_open':{k:dict(v) for k,v in per_cell.items()},
                                  'paired_open':paired,'heldout':executable})

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument('mode',choices=['prepare','combine'])
    arg.add_argument('--output',type=Path,required=True)
    a=arg.parse_args()
    if a.mode=='prepare':prepare(a.output)
    else:combine(a.output)
if __name__=='__main__':main()
