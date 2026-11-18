"""Replay frozen extracted expressions. Never calls a model or interprets source prose."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIELDS=frozenset(('identity_verified','active_hold','routine_packet_complete','minor_repair_scope','exception_reconciled','exception_authorized'))
LAYOUTS=('head','middle','tail')
ARMS=('one','batch','strong')
def read(path):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    def constant(v):raise ValueError('nonfinite JSON')
    return json.loads(path.read_text(),object_pairs_hook=pairs,parse_constant=constant)
def verify(root=ROOT):
    for p,sha in read(root/'results/stage-13/freeze.json').items():
        if hashlib.sha256((root/p).read_bytes()).hexdigest()!=sha:raise ValueError('Frozen input changed: '+p)
def validate_expr(expr,depth=0,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if depth>16 or budget[0]>200:raise ValueError('expression too complex')
    if type(expr) is not dict or len(expr)!=1:raise ValueError('expression must have one operator')
    op,value=next(iter(expr.items()))
    if op=='field':
        if type(value) is not str or value not in FIELDS:raise ValueError('unknown field')
    elif op=='not':validate_expr(value,depth+1,budget)
    elif op in ('and','or'):
        if type(value) is not list or len(value)<2:raise ValueError('and/or require at least two expressions')
        for e in value:validate_expr(e,depth+1,budget)
    else:raise ValueError('unknown operator')
def eval_expr(expr,facts):
    op,value=next(iter(expr.items()))
    if op=='field':return facts[value]
    if op=='not':
        r=eval_expr(value,facts)
        return None if r is None else not r
    values=[eval_expr(e,facts) for e in value]
    if op=='and':return False if False in values else (None if None in values else True)
    return True if True in values else (None if None in values else False)
def evaluate(expr,facts):
    validate_expr(expr)
    if type(facts) is not dict or set(facts)!=FIELDS or any(v is not None and type(v) is not bool for v in facts.values()):raise ValueError('facts must supply exactly six Boolean/null fields')
    return {True:'permitted',False:'blocked',None:'unknown'}[eval_expr(expr,facts)]
def source_errors(sources,refs):
    if type(sources) is not list or not sources or any(type(s) is not str or s not in refs for s in sources):return ['missing/invalid source IDs']
    if len(set(sources))!=len(sources):return ['duplicate source IDs']
    return []
def check_output(data,refs):
    errors=[]
    if type(data) is not dict or set(data)!={'questions','model'}:return ['output must contain exactly questions and model']
    rows=data['questions']
    if type(rows) is not list:return ['questions must be an array']
    if [r.get('id') if type(r) is dict else None for r in rows]!=['Q1','Q2','Q3','Q4','Q5']:errors.append('question IDs mismatch')
    for row in rows:
        if type(row) is not dict or set(row)!={'id','answer','sources','status'}:errors.append('bad question row');continue
        if type(row['answer']) is not str or not row['answer'].strip():errors.append('empty answer')
        if row['status']!='proposed':errors.append('question not proposed')
        errors.extend(source_errors(row['sources'],refs))
    model=data['model']
    if type(model) is not dict or set(model)!={'status','permit','sources'}:errors.append('bad model shape')
    else:
        if model['status']!='proposed':errors.append('model not proposed')
        errors.extend(source_errors(model['sources'],refs))
        try:validate_expr(model['permit'])
        except ValueError as e:errors.append(str(e))
    return errors
def summarize(root=ROOT):
    verify(root)
    cases=read(root/'data/stage-13/hidden_cases.json')
    cells={}
    for layout in LAYOUTS:
        refs={b['id'] for b in read(root/('data/stage-13/'+layout+'.json'))['blocks']}
        for arm in ARMS:
            cell=layout+'_'+arm;raw=root/('results/stage-13/raw/'+cell+'.json')
            try:
                output=read(raw);errors=check_output(output,refs)
            except (ValueError,OSError) as e:
                output={};errors=[str(e)]
            predictions=[]
            for case in cases:
                result='unknown' if errors else evaluate(output['model']['permit'],case['facts'])
                predictions.append({'id':case['id'],'expected':case['expected'],'actual':result,'correct':result==case['expected']})
            cells[cell]={'schema_errors':errors,'cases':predictions,'correct':sum(c['correct'] for c in predictions),'total':len(cases),'unknown':sum(c['actual']=='unknown' for c in predictions),'false_permissions':sum(c['actual']=='permitted' and c['expected']!='permitted' for c in predictions),'nonpermitted_gold':sum(c['expected']!='permitted' for c in predictions)}
    return {'kind':'frozen expression replay, not fresh inference or semantic proof','cells':cells,'human_approvals':0,'human_minutes':None,'token_usage':None,'provider_model_version':None,'monetary_cost':None}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    path=Path(args.output);path.mkdir(parents=True,exist_ok=False)
    (path/'summary.json').write_text(json.dumps(summarize(),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
