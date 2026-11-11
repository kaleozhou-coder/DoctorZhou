"""Independent engineering probes, not business samples or production proof."""
import copy, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import rule_ir_v2 as old
import rule_ir_v3 as ir
import input_contract_v2 as contract
from test_policy_baseline import envelope, fixture

ref = [{'source_id':'p','locator':'1'}]
def base():
    return {'version':ir.VERSION,'fields':{'s':{'path':['s'],'type':{'kind':'set','items':'integer'}}},'rules':[{'id':'r','when':{'op':'any','args':[{'op':'literal','type':'boolean','value':True},{'op':'eq','left':{'op':'count','arg':{'op':'field','name':'s'}},'right':{'op':'literal','type':'integer','value':1}}]},'decision':'close_eligible','reason':'probe','source_refs':ref}],'default':{'decision':'needs_review','reason':'fallback','source_refs':ref}}
results = {'scope':'Independent synthetic engineering probes only', 'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/rule_ir_v3.py',ROOT/'src/input_contract_v2.py']}, 'runtime':[], 'mutations':[], 'contract':[]}
for data in [[1,1],[None,1,1],[1,None,1],[1,1,None],[None,1,'bad'],[None],[]]:
    results['runtime'].append({'facts':{'s':data},'result':ir.evaluate(base(),{'s':data})})
assert results['runtime'][0]['result']['reason_codes'] == ['malformed_input']
assert all(results['runtime'][i]['result']['decision']=='close_eligible' for i in (1,2,3))
# Independent artifact mutations: every invalid artifact must be refused before rule execution.
mutations = []
for value in [None, [], {}, 0, True, 'bad']:
    for key in ['fields','rules','default']:
        p=base(); p[key]=value; mutations.append((key+':'+repr(value),p))
for kind,val in [('integer',None),({'kind':'set','items':'integer'},[None,1,1]),({'kind':'record','fields':{'a':'integer'}},{}),({'kind':'array','items':'integer'},[None])]:
    p=base(); p['fields']['unused']={'path':['unused'],'type':kind,'enum':[val]};mutations.append(('incomplete_enum:'+repr(val),p))
for enum in [[[1,2],[2,1]],[[1,1]],[[True]]]:
    p=base();p['fields']['s']['enum']=enum;mutations.append(('bad_enum:'+repr(enum),p))
p=base();p['default']['decision']='close_eligible';mutations.append(('default_close',p))
p=base();p['rules'][0]['when']={'op':'literal','type':'boolean','value':1};mutations.append(('bool_int_literal',p))
for name,p in mutations:
    try: validation=ir.validate(p); rejected=False
    except ir.RuleError as e: validation=str(e);rejected=True
    out=ir.evaluate(p,{})
    assert rejected and out['reason_codes']==['invalid_artifact'] and out['trace']==[], (name,out)
    results['mutations'].append({'name':name,'rejected':rejected,'validation':validation,'result':out})
p=base();p['fields']['s']['enum']=[None];p['rules']=[];p['default']['decision']='close_eligible'
p['version']=old.VERSION
assert old.validate(p) is old.UNKNOWN
results['legacy_exploit']=old.evaluate(p,{})
p['version']=ir.VERSION
results['fixed_exploit']=ir.evaluate(p,{})
# Build independent probes using only documented synthetic engineering fixture data.
called=[]
def close(*args):
    called.append(True)
    return {'decision':'close_eligible','reason_codes':['probe'],'payment_authorized':True}
def case():
    c=envelope('F06',fixture('F06'));c.pop('question')
    for s in c['sources']:
        s.pop('text',None)
        for entry in s['facts'].get('source_catalog',[]):
            for paragraph in entry['paragraphs']:paragraph.pop('text',None)
    return c
for name in ['multichannel','null_question','null_source_text','duplicate_json_key','duplicate_source_changed_text','empty_all','null_paragraph']:
    c=case()
    if name=='multichannel':
        c['question']=' ';c['raw_text']='Rejected';c['sources'][0]['text']='Accepted';c['sources'][0]['raw_text']='Rejected'
        c['sources'][-1]['facts']['source_catalog'].append({'source_id':'uncited','kind':'OTHER','paragraphs':[{'locator':'uncited','text':'Rejected'}]})
    elif name=='null_question':c['question']=None
    elif name=='null_source_text':c['sources'][0]['text']=None
    elif name=='null_paragraph':c['sources'][-1]['facts']['source_catalog'][0]['paragraphs'][0]['text']=None
    elif name=='duplicate_json_key':c=json.dumps(c)[:-1]+',"question":"Rejected","question":""}'
    elif name=='duplicate_source_changed_text':
        extra=copy.deepcopy(c['sources'][0]);extra['text']='Rejected';c['sources'].append(extra)
    elif name=='empty_all':
        c['question']='';c['raw_text']=''
        for s in c['sources']:s['text']='';s['raw_text']=''
    called.clear();out=contract.apply_contract(c,{},close)
    assert out['decision']==('close_eligible' if name=='empty_all' else 'needs_review'),(name,out)
    if name not in ('multichannel','empty_all'):assert not called
    if name=='multichannel':assert len(out['input_contract']['unverified_text_paths'])==5
    assert out['payment_authorized'] is False
    results['contract'].append({'name':name,'predictor_called':bool(called),'result':out})
cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_rule_ir_v3.py','-v']
r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
results['test_suite']={'command':'PYTHONDONTWRITEBYTECODE=1 '+' '.join(cmd),'returncode':r.returncode,'output':r.stdout+r.stderr}
assert r.returncode==0
cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_input_contract_v2.py','-v']
r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
results['contract_suite']={'command':'PYTHONDONTWRITEBYTECODE=1 '+' '.join(cmd),'returncode':r.returncode,'output':r.stdout+r.stderr}
assert r.returncode==0
out=ROOT/'results/stage-06/reviewer-probe.json'
out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'artifact_mutations':len(mutations),'runtime_probes':len(results['runtime']),'contract_probes':len(results['contract']),'confirmed_null_duplicate_masking':True,'suite_returncodes':[results['test_suite']['returncode'],results['contract_suite']['returncode']]}))
