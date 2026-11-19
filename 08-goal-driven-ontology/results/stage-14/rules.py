"""Frozen K3 interpreter and synthetic rule evaluation. No network/dependencies."""
import itertools
import json
from pathlib import Path

def check(expr, leaves):
    if isinstance(expr, str):
        if expr not in leaves:
            raise ValueError(f'undeclared leaf: {expr}')
        return
    if not isinstance(expr, list) or not expr or expr[0] not in ('and','or','not'):
        raise ValueError('invalid expression')
    if (expr[0]=='not' and len(expr)!=2) or (expr[0]!='not' and len(expr)<3):
        raise ValueError('invalid arity')
    for x in expr[1:]:
        check(x,leaves)

def run(expr, facts):
    if expr is None:
        return None
    if isinstance(expr,str):
        v=facts.get(expr)
        if v is not None and type(v) is not bool:
            raise ValueError('not a boolean or null')
        return v
    op,*args=expr
    vals=[run(x,facts) for x in args]
    if op=='not':
        return None if vals[0] is None else not vals[0]
    if op=='and':
        return False if False in vals else None if None in vals else True
    if op=='or':
        return True if True in vals else None if None in vals else False
    raise ValueError('unknown operator')

def judgement(v):
    return 'UNKNOWN' if v is None else 'ALLOW' if v else 'DENY'

def compare(gold, proposed, leaves):
    result={'evaluated':3**len(leaves),'different':0,'differences_on_complete':0,'false_allow':0,'false_allow_first':None,'first_difference':None}
    for values in itertools.product((False,True,None),repeat=len(leaves)):
        facts=dict(zip(leaves,values))
        g,p=run(gold,facts),run(proposed,facts)
        if g is not p:
            result['different']+=1
            result['differences_on_complete']+=int(None not in values)
            if result['first_difference'] is None:
                result['first_difference']={'facts':facts,'gold':judgement(g),'predicted':judgement(p)}
        if g is not True and p is True:
            result['false_allow']+=1
            if result['false_allow_first'] is None:
                result['false_allow_first']={'facts':facts,'gold':judgement(g),'predicted':judgement(p)}
    return result

def grade(run_path, gold, docs_dir):
    pred=json.loads(Path(run_path).read_text())
    if set(pred)!={'expression','evidence','issues'}:
        raise ValueError(f'bad output envelope: {run_path}')
    leaves=sorted({x for case in gold['cases'] for x in case['facts']})
    if len(leaves)>10: raise ValueError('too many leaves for an exhaustive test')
    check(gold['expression'],leaves)
    if pred['expression'] is not None: check(pred['expression'],leaves)
    expected=set(gold['required_files'])
    docset={x.name:x.read_text() for x in Path(docs_dir).glob('*.txt')}
    if not expected<=docset.keys(): raise ValueError('gold references missing source')
    cited=set()
    invalid=[]
    for citation in pred['evidence']:
        f,q=citation['file'],citation['quote']
        if f not in docset or not isinstance(q,str) or not q.strip() or q not in docset[f]:
            invalid.append(citation)
        else:
            cited.add(f)
    cases=[]
    for case in gold['cases']:
        g=judgement(run(gold['expression'],case['facts']))
        if g!=case['expected']: raise ValueError(f"gold case mismatch {case['id']}: {g}")
        p=judgement(run(pred['expression'],case['facts']))
        cases.append({'id':case['id'],'gold':g,'predicted':p})
    return {'citation_required_covered':len(cited & expected),'citation_required_total':len(expected),
        'citation_extra':sorted(cited-expected),'citation_missing':sorted(expected-cited),'citation_invalid':invalid,
        'heldout_correct':sum(c['gold']==c['predicted'] for c in cases),'heldout_total':len(cases),
        'heldout_false_allow':sum(c['gold']!='ALLOW' and c['predicted']=='ALLOW' for c in cases),
        'cases':cases,'exhaustive':compare(gold['expression'],pred['expression'],leaves)}

def grade_all(root):
    p=Path(root)
    outputs={}
    for family in ('a','b'):
        gold=json.loads((p/'holdout'/f'family_{family}-gold.json').read_text())
        docs=p/'public_inputs'/f'family_{family}'
        outputs[family]={method:grade(p/'runs'/f'{family}_{method}.json',gold,docs)
                         for method in ('one','batch','review','batch_draft','review_draft')}
    return outputs

if __name__=='__main__':
    print(json.dumps(grade_all(Path(__file__).resolve().parent),ensure_ascii=False,indent=2))
