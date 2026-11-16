"""Replay frozen internal-AI observations; no model/API calls or semantic grading."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root=ROOT):
    manifest=read(root/'results/stage-11/freeze.json')
    for name,sha in manifest['sha256'].items():
        if digest(root/name)!=sha: raise ValueError('Frozen input changed: '+name)
    return manifest

def score(output,gold,materials):
    valid_refs={d['id']+'.'+k for d in materials['documents'] for k in d['paragraphs']}
    result={'facts':[],'decisions':[],'schema_errors':[]}
    if not isinstance(output,dict): output={};result['schema_errors'].append('output must be an object')
    for section in ('facts','decisions'):
        rows=output.get(section,[])
        if not isinstance(rows,list): rows=[];result['schema_errors'].append(section+' must be an array')
        expected={r['id'] for r in gold[section]}
        for r in rows:
            if not isinstance(r,dict) or not isinstance(r.get('id'),str) or r.get('id') not in expected: result['schema_errors'].append(section+': unexpected row')
        for target in gold[section]:
            matches=[r for r in rows if isinstance(r,dict) and r.get('id')==target['id']]
            r=matches[0] if len(matches)==1 else {}
            refs=r.get('sources',[])
            structure=(len(matches)==1 and r.get('status')=='proposed' and isinstance(r.get('reason'),str) and bool(r['reason'].strip()) and isinstance(refs,list) and bool(refs) and all(isinstance(s,str) and s in valid_refs for s in refs))
            result[section].append({'id':target['id'],'expected':target['answer'],'observed':r.get('answer'),'answer_exact':r.get('answer')==target['answer'] and len(matches)==1,'schema_valid':structure,'pass':structure and r.get('answer')==target['answer'],'false_close':section=='decisions' and r.get('answer')=='ALLOW' and target['answer']!='ALLOW'})
            if not structure: result['schema_errors'].append(target['id']+': missing, duplicate, status, reason or source error')
    result['summary']={s: {'correct':sum(r['pass'] for r in result[s]),'total':len(result[s])} for s in ('facts','decisions')}
    result['summary']['contract_valid']=not result['schema_errors']
    result['summary']['false_closes']=sum(r['false_close'] for r in result['decisions'])
    result['summary']['nonallow_gold_count']=sum(r['expected']!='ALLOW' for r in result['decisions'])
    result['summary']['false_blocks']=sum(r['observed']=='BLOCKED' and r['expected']!='BLOCKED' for r in result['decisions'])
    result['summary']['unknown_when_allowed']=sum(r['observed']=='UNKNOWN' and r['expected']=='ALLOW' for r in result['decisions'])
    return result

def summarize(root=ROOT):
    verify(root)
    gold=read(root/'data/stage-11/gold.json'); materials=read(root/'data/stage-11/materials.json')
    scores={a:score(read(root/f'results/stage-11/arm_{a}.json'),gold,materials) for a in ('one','batch','strong')}
    return {'kind':'frozen internal AI observation, not fresh inference','scores':scores,'human_approvals':0,'human_minutes':None,'token_usage':None,'monetary_cost':None}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    (out/'summary.json').write_text(json.dumps(summarize(),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
