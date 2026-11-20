"""Score frozen extraction outputs; no model call, no environment dependencies."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
FIELDS=('sign_days','sign_trigger','advance_pct','advance_workdays','advance_guarantee','install_days','install_trigger')
CELLS=('one','batch','strong')
GROUP=('complete','withheld')
def read(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def validate_freeze():
    f=read('freeze.json')
    for relative,h in f['hashes'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=h: raise ValueError(f'freeze mismatch: {relative}')
def same(a,b): return type(a) is type(b) and a==b
def decide(rule,key,offset,target,days_override=None,trigger_override=None):
    limit=rule[f'{key}_days']['value'] if days_override is None else days_override
    trigger=rule[f'{key}_trigger']['value'] if trigger_override is None else trigger_override
    if type(limit) is not int or not trigger or target!=trigger: return 'UNKNOWN'
    return 'PASS' if offset<=limit else 'FAIL'
def grade(out,key,t):
    gold=read('score/gold.json')
    g=gold[key]
    if type(out) is not dict or set(out)!=set((*FIELDS,'missing_docs')): raise ValueError('invalid output keys')
    available={'M','O'} if t=='batch-draft' else set(read('packets/order.json')[key])
    checks=[]
    for k in FIELDS:
        item=out[k]
        if type(item) is not dict or set(item)!= {'value','evidence'} or type(item['evidence']) is not list or not all(type(x) is str for x in item['evidence']): raise ValueError(f'invalid shape: {k}')
        v=item['value']
        if v is not None and (type(v) is not int if k.endswith(('_days','pct','workdays')) else type(v) is not str): raise ValueError(f'invalid value type: {k}')
        supplied=set(item['evidence'])
        checks.append({'field':k,'value':same(v,g[k]['value']),
                       'direct_citation':g[k]['source'] in supplied,
                       'exclusive_direct_citation':supplied=={g[k]['source']},
                       'unavailable_citations':sorted(supplied-available)})
    md=out['missing_docs']
    if type(md) is not list or not all(type(x) is str for x in md): raise ValueError('invalid missing_docs')
    rows=[]
    for cid,kind,offset,target,complete,withheld,historical in gold['cases']:
        a=decide(out,kind,offset,target)
        e=complete if key=='complete' else withheld
        rows.append({'id':cid,'predicted':a,'gold':e,'match':a==e})
    return {'value_correct':sum(c['value'] for c in checks),
            'direct_citations':sum(c['direct_citation'] for c in checks),
            'exclusive_direct_citations':sum(c['exclusive_direct_citation'] for c in checks),
            'unavailable_citations':sum(len(c['unavailable_citations']) for c in checks),
            'missing_docs_correct':md == g['missing_docs'],
            'case_correct':sum(r['match'] for r in rows),'case_count':len(rows),
            'unsafe_pass':sum(r['predicted']=='PASS' and r['gold']!='PASS' for r in rows),
            'nonpass_count':sum(r['gold']!='PASS' for r in rows),
            'correct_unknown':sum(r['predicted']=='UNKNOWN' and r['gold']=='UNKNOWN' for r in rows),
            'unknown_count':sum(r['gold']=='UNKNOWN' for r in rows),
            'checks':checks,'cases':rows}
def score():
    validate_freeze()
    gold=read('score/gold.json')
    old=gold['historical_days']; r=gold['complete']
    old_case_correct=sum(decide(r,k,d,t,old if k=='sign' else None)==hist for _,k,d,t,_,_,hist in gold['cases'])
    assert old_case_correct==len(gold['cases'])
    flip=[i for i,k,d,t,a,_,b in gold['cases'] if a!=b]
    return {'stage':15,'historical_reconstruction_control':{'correct':old_case_correct,'case_count':len(gold['cases']),'flip_case_ids':flip,'model_run':False},
            'final_cells':{f'{g}-{m}':grade(read(f'raw/{g}-{m}.json'),g,m) for g in GROUP for m in CELLS},
            'process_drafts_scored_against_final':{f'{g}-{m}-draft':grade(read(f'raw/{g}-{m}-draft.json'),g,m+'-draft') for g in GROUP for m in CELLS if m!='one'}}
def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out',type=Path)
    path=a.parse_args().out
    p=(json.dumps(score(),ensure_ascii=False,indent=2)+'\n')
    if path:
        with path.open('x',encoding='utf-8',newline='\n') as f: f.write(p)
    else: sys.stdout.write(p)
if __name__=='__main__': main()
