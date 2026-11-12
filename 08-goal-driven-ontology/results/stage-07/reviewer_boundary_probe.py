"""Independent engineering adversarial probe; synthetic, no model or network."""
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import review_receipt_gate as gate
import input_contract_v2 as old
import rule_ir_v3 as ir
from test_policy_baseline import envelope, fixture, POLICIES
NOW = '2026-11-12T09:00:00Z'
checks=[]

def record(name, passed, detail=None):
    checks.append({'name':name,'passed':bool(passed),'detail':detail})

def run():
    for family in ['F01','F05']:
        c=envelope(family,fixture(family));m=POLICIES[family]
        a=ir.loads((ROOT/f'ontology/ir-reference-v3/{family}.json').read_text())
        pred=lambda c,m:ir.predict_case(c,a,m)
        r={'version':gate.VERSION,'scope':gate.SCOPE,'review_id':'synthetic-independent-review','reviewer_id':'synthetic-reviewer',
           'case_sha256':gate.canonical_sha256(c),'materials_sha256':gate.canonical_sha256(m),
           'reviewed_paths':old.unverified_text_paths(c),'outcome':'consistent',
           'reviewed_at':'2026-11-12T08:00:00Z','expires_at':'2026-11-12T10:00:00Z'}
        call=lambda case,receipt,mat=m,clock=NOW:gate.apply_contract(case,mat,pred,trusted_receipt=receipt,as_of=clock)
        good=call(c,r)
        record(family+'/valid',good['decision']=='close_eligible' and good['input_contract']['review_assertion_accepted'])
        record(family+'/unchanged_refs',good['source_refs']==pred(c,m)['source_refs'])
        for field in r:
            for val in [None,False,0,[],{},'']:
                bad=copy.deepcopy(r);bad[field]=val
                out=call(c,bad)
                record(f'{family}/invalid/{field}/{type(val).__name__}/{repr(val)}',out['decision']!='close_eligible',out['reason_codes'])
        for field in ['trusted_receipt','prose_verified','review_assertion_accepted','review_status','input_contract']:
            bad=copy.deepcopy(c);bad[field]=r if field=='trusted_receipt' else True
            out=call(bad,None)
            record(family+'/case_forgery/'+field,out['decision']!='close_eligible',out['reason_codes'])
        for clock in ['2026-11-12T07:59:59Z','2026-11-12T10:00:00Z',None]:
            out=call(c,r,clock=clock)
            record(family+'/clock/'+str(clock),out['decision']!='close_eligible',out['reason_codes'])
        changed=copy.deepcopy(c);changed['question']+=' '
        out=call(changed,r)
        record(family+'/stale_case',out['decision']!='close_eligible',out['reason_codes'])
        changed_m=copy.deepcopy(m);changed_m['policy_paragraphs'][0]['text']+=' '
        out=call(c,r,mat=changed_m)
        record(family+'/stale_policy',out['decision']!='close_eligible',out['reason_codes'])
        for outcome in ['contradictory','unresolved']:
            bad=copy.deepcopy(r);bad['outcome']=outcome;out=call(c,bad)
            record(family+'/review/'+outcome,out['decision']!='close_eligible',out['reason_codes'])
        for decision in ['needs_evidence','needs_review']:
            out=gate.apply_contract(c,m,lambda *_:{'decision':decision,'reason_codes':['policy_failure'],'source_refs':[]},trusted_receipt=r,as_of=NOW)
            record(family+'/never_upgrade/'+decision,out['decision']==decision)
        # Intentionally demonstrate the trust limitation rather than mark it safe.
        lie=copy.deepcopy(c);lie['question']='The attached document explicitly says these goods were NOT accepted.'
        forged=copy.deepcopy(r);forged['case_sha256']=gate.canonical_sha256(lie)
        out=call(lie,forged)
        record(family+'/documented_trusted_lie',out['decision']=='close_eligible',{'actual':out['decision'],'semantic_safety':False,'note':'Expected trust-boundary limitation; NOT a successful safety case'})
    src=(ROOT/'src/review_receipt_gate.py').read_bytes()
    return {'implementation_sha256':hashlib.sha256(src).hexdigest(),'checks':checks,'count':len(checks),'passed':sum(x['passed'] for x in checks),'not_expert_gold':True,'model_calls':0}
if __name__=='__main__':
    out=run();print(json.dumps(out,ensure_ascii=False,indent=2));sys.exit(0 if out['passed']==out['count'] else 1)
