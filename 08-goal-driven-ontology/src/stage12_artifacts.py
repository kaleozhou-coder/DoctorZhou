"""Validate/replay frozen open-response observations and independent semantic review.
This program does not call a model or judge natural-language entailment."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VARIANTS=('short_early','short_late','long_early','long_late')
ARMS=('one','batch','strong')
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root=ROOT):
    for path,sha in read(root/'results/stage-12/freeze.json').items():
        if digest(root/path)!=sha: raise ValueError('Frozen input changed: '+path)
def check_output(data,questions,materials):
    errors=[]
    refs={d['id']+'.'+k for d in materials['documents'] for k in d['paragraphs']}
    if type(data) is not dict: return ['Not an object']
    for section,targets in [('questions',questions['questions']),('cases',questions['snapshots'])]:
        rows=data.get(section)
        if type(rows) is not list:
            errors.append(section+': not an array');continue
        ids=[r.get('id') for r in rows if type(r) is dict]
        expected=[r['id'] for r in targets]
        if ids!=expected: errors.append(section+': missing, duplicate, unexpected or reordered ids')
        for row in rows:
            if type(row) is not dict: errors.append('Not an item');continue
            label=str(row.get('id'))
            if type(row.get('answer')) is not str or not row['answer'].strip(): errors.append(label+': empty/nontext answer')
            if row.get('status')!='proposed': errors.append(label+': not proposed')
            if section=='cases' and (type(row.get('rationale')) is not str or not row['rationale'].strip()):errors.append(label+': missing rationale')
            sources=row.get('sources')
            if type(sources) is not list or not sources or any(type(x) is not str or x not in refs for x in sources): errors.append(label+': missing/invalid citation')
    return errors
def summarize_review(review,gold):
    out={}
    for section in ('questions','cases'):
        rows=review[section];expected=list(gold[section])
        if [r['id'] for r in rows]!=expected:raise ValueError('Review ids mismatch')
        for r in rows:
            if type(r.get('semantic_ok')) is not bool or type(r.get('citation_ok')) is not bool or type(r.get('note')) is not str:raise ValueError('Review requires booleans and note')
            if section=='cases' and r.get('normalized_meaning') not in ('permitted','blocked','undecided'):raise ValueError('Unrecognized normalization')
            if section=='cases' and r['semantic_ok']!=(r['normalized_meaning']==gold[section][r['id']]['meaning']):raise ValueError('Meaning/review inconsistent')
        out[section]={'semantic_correct':sum(r['semantic_ok'] for r in rows),'citation_supported':sum(r['citation_ok'] for r in rows),'total':len(rows)}
    out['false_permissions']=sum(r['normalized_meaning']=='permitted' and gold['cases'][r['id']]['meaning']!='permitted' for r in review['cases'])
    out['not_permitted_gold']=sum(r['meaning']!='permitted' for r in gold['cases'].values())
    return out
def summarize(root=ROOT):
    verify(root)
    q=read(root/'data/stage-12/questions.json');gold=read(root/'data/stage-12/gold.json')
    mapping=read(root/'results/stage-12/reveal.json')
    reviews=read(root/'results/stage-12/blind-review.json')
    out={}
    for anonymous,cell in mapping.items():
        if cell not in [v+'_'+a for v in VARIANTS for a in ARMS]:raise ValueError('Unexpected cell')
        v=next(v for v in VARIANTS if cell.startswith(v+'_'))
        data=read(root/('results/stage-12/raw/'+cell+'.json'))
        out[cell]=summarize_review(reviews[anonymous],gold)
        out[cell]['schema_errors']=check_output(data,q,read(root/('data/stage-12/'+v+'.json')))
    if len(out)!=12:raise ValueError('Missing or duplicated cell')
    return {'kind':'frozen observations and AI-reviewed semantics; not fresh model inference','cells':out,'human_approvals':0,'human_minutes':None,'token_usage':None,'monetary_cost':None}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    output=Path(a.output);output.mkdir(parents=True,exist_ok=False)
    (output/'summary.json').write_text(json.dumps(summarize(),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
