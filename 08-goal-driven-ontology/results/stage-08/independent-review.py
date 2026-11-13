"""Independent read-only data audit; only independent-review artifacts are written."""
import argparse, copy, hashlib, importlib.util, json
from pathlib import Path
from fractions import Fraction as Q
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline-root', type=Path, help='Optional separate historical repository root for cross-copy comparison')
args=parser.parse_args()
OLD=args.baseline_root.resolve() if args.baseline_root else ROOT
comparison_mode='cross_copy' if args.baseline_root else 'same_repository_frozen_history'
read=lambda p:json.loads(p.read_text())
pack=read(OLD/'benchmark/joint-review-v1/probes.json')
receipts=read(OLD/'results/stage-07/first-run/simulated-receipts.json')
arms=['ir_only','gate_v2_ir','receipt_ir']
preds={a:read(OLD/f'results/stage-07/first-run/{a}.predictions.json') for a in arms}
summary=read(ROOT/'results/stage-08/final-run/summary.json')
rows=read(ROOT/'results/stage-08/final-run/ledger.json')
checks=[]
def check(name, truth):
    assert truth,name
    checks.append(name)
for rel in ['benchmark/joint-review-v1/probes.json','results/stage-07/first-run/simulated-receipts.json']+[f'results/stage-07/first-run/{a}.predictions.json' for a in arms]:
    manifest=read(ROOT/'experiments/stage-08/input-freeze.json')
    check('frozen SHA256 '+rel,hashlib.sha256((OLD/rel).read_bytes()).hexdigest()==manifest[rel])
    if args.baseline_root:
        check('cross-copy historic bytes '+rel,(OLD/rel).read_bytes()==(ROOT/rel).read_bytes())
check('84 unique ledger rows',len(rows)==84 and len({(x['arm'],x['probe_id']) for x in rows})==84)
lookup={(x['arm'],x['probe_id']):x for x in rows}
counts={}
for scope,exclude in [('all_28_including_failure_controls',False),('26_excluding_trusted_failure_controls',True)]:
    counts[scope]={}
    for arm in arms:
        c=dict(n=0,receipt_units=0,declared_path_units=0,downstream_review_units=0,evidence_request_units=0,closed=0,known_trust_control_false_close=0)
        for p,r,d in zip(pack['probes'],receipts,preds[arm]):
            failure=p['metric_stratum']=='trusted_reviewer_failure'
            if exclude and failure:continue
            v=dict(receipt_units=int(arm=='receipt_ir' and r['receipt'] is not None),declared_path_units=len(r['receipt']['reviewed_paths']) if arm=='receipt_ir' and r['receipt'] is not None else 0,downstream_review_units=int(d['decision']=='needs_review'),evidence_request_units=int(d['decision']=='needs_evidence'),closed=int(d['decision']=='close_eligible'),known_trust_control_false_close=int(failure and d['decision']=='close_eligible'))
            for key,value in v.items():
                check(f'{scope}/{arm}/{p["probe_id"]}/{key}',lookup[arm,p['probe_id']][key]==value)
                c[key]+=value
            c['n']+=1
        counts[scope][arm]=c
        check(scope+'/'+arm+' counts',summary['scopes'][scope]['arms'][arm]==c)
    s=summary['scopes'][scope]; g=counts[scope]['gate_v2_ir']; r=counts[scope]['receipt_ir']; saving=g['downstream_review_units']-r['downstream_review_units']
    check(scope+' saving',s['downstream_review_units_saved']==saving)
    for mode,label in [('receipt_units','receipt_break_even_ratio'),('declared_path_units','path_break_even_ratio')]:
        check(scope+'/'+label,Q(s[label])==Q(saving,r[mode]))
    for item in s['sensitivity']:
        ratio=Q(item['upstream_cost_ratio']);mode=item['upstream_mode']
        expected={a:Q(c[mode])*ratio+c['downstream_review_units']+c['evidence_request_units'] for a,c in counts[scope].items()}
        check(scope+' grid '+mode+str(ratio),all(Q(item['normalized_cost'][a])==expected[a] for a in arms) and Q(item['receipt_minus_gate'])==expected['receipt_ir']-expected['gate_v2_ir'])
check('unmeasured fields',summary['actual_human_seconds'] is None and summary['measured_cost_currency'] is None and summary['actual_human_reviews']==summary['actual_model_runs']==0)
spec=importlib.util.spec_from_file_location('candidate',ROOT/'src/run_stage08.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.verify(ROOT);check('freeze validation',True)
for label,mutate in [
 ('duplicate probe',lambda p,r,d:p['probes'].append(copy.deepcopy(p['probes'][0]))),
 ('receipt order',lambda p,r,d:r.reverse()),
 ('prediction missing',lambda p,r,d:d['ir_only'].pop()),
 ('extra arm',lambda p,r,d:d.update(extra=[])),
 ('unknown state',lambda p,r,d:d['ir_only'][0].update(decision='approve')),
 ('payment true',lambda p,r,d:d['ir_only'][0].update(payment_authorized=True)),
 ('payment absent',lambda p,r,d:d['ir_only'][0].pop('payment_authorized')),
 ('unbound receipt',lambda p,r,d:next(x['receipt'] for x in r if x['receipt']).update(review_id='wrong')),
 ('duplicate paths',lambda p,r,d:next(x['receipt'] for x in r if x['receipt']).update(reviewed_paths=['$.x','$.x']))]:
    p,r,d=copy.deepcopy((pack,receipts,preds));mutate(p,r,d)
    try:m.ledger(p,r,d)
    except ValueError:check('reject '+label,True)
    else:raise AssertionError(label)
for mode,ratio,e in [('both',Q(1),Q(1)),('receipt_units',Q(-1),Q(1)),('receipt_units',Q(1),Q(-1))]:
    try:m.cost(counts['26_excluding_trusted_failure_controls']['receipt_ir'],ratio,mode,e)
    except ValueError:check('reject cost '+mode+str(ratio)+str(e),True)
    else:raise AssertionError('invalid cost accepted')
# Optional public-helper hardening, not relevant to the frozen Fraction-only runner.
observations=[]
c=counts['26_excluding_trusted_failure_controls']['receipt_ir']
for x in [float('nan'),float('inf')]:
    try:out=m.cost(c,x);observations.append('cost accepts nonfinite float '+str(x)+' -> '+str(out))
    except (ValueError,TypeError):pass
p,r,d=copy.deepcopy((pack,receipts,preds));d['receipt_ir'][0]['input_contract']['review_assertion_accepted']='not_bool'
try:m.ledger(p,r,d);observations.append('ledger copies unvalidated receipt_accepted metadata')
except ValueError:pass
report=dict(comparison_mode=comparison_mode,passed_checks=len(checks),counts=counts,nonblocking_hardening=observations,actual_model_calls=0)
# Print only: reruns must not overwrite retained first-review records.
print(json.dumps(report,ensure_ascii=False,indent=2))
