"""Rebuild masked review packet and mechanically verify frozen AI artifacts.
Does NOT regenerate AI extraction or AI grading. No model API.
"""
import argparse,hashlib,json,pathlib,random
ARMS=['one','batch','strong','rule']
def load(p): return json.loads(p.read_text())
def dump(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def prepare(root,out):
    if out.exists() and any(out.iterdir()): raise ValueError('Output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    arms=ARMS.copy();random.Random(15112026).shuffle(arms)
    mapping={f'Candidate-{i+1}':a for i,a in enumerate(arms)}
    dump(out/'masked.json',{k:load(root/f'results/stage-10/arm_{a}.json') for k,a in mapping.items()})
    dump(out/'reveal.json',mapping)
    paths=list((root/'data/stage-10').glob('*.json'))+list((root/'results/stage-10').glob('arm*.json'))
    dump(out/'input-sha256.json',{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})
def verify(root):
    material=load(root/'data/stage-10/materials.json');gold=load(root/'data/stage-10/gold.json')
    assert len(material)==len(gold)==6
    assert sum(len(c['facts']) for c in gold)==23
    for i,c in enumerate(material):
        assert c['documents']==load(root/'data/stage-10/batch1.json')[i]['documents']+load(root/'data/stage-10/batch2.json')[i]['documents']
    counts={}
    for arm in ARMS:
        x=load(root/f'results/stage-10/arm_{arm}.json')
        assert [c['case_id'] for c in x]==[c['case_id'] for c in material]
        counts[arm]=sum(len(c['facts']) for c in x)
        for c in x:
            for f in c['facts']:
                assert set(f)=={'subject','relation','value','sources','status'},(arm,c['case_id'],f)
                assert f['status']=='proposed'
                assert f['sources'] and set(f['sources'])<={'D1','D2'}
    return {'cases':6,'target_propositions':23,'candidate_objects':counts,'human_reviewed':0,'human_minutes':None,'money_cost':None}
def summarize(root):
    grades=load(root/'results/stage-10/blind-grades.json')['candidates']
    mapping=load(root/'results/stage-10/review/reveal.json')
    gold=load(root/'data/stage-10/gold.json')
    expected={(c['case_id'],i) for c in gold for i in range(len(c['facts']))}
    assert set(grades)==set(mapping)
    result={}
    for masked,g in grades.items():
        assert len(g['targets'])==23
        assert {(t['case_id'],t['gold_index']) for t in g['targets']}==expected
        for t in g['targets']:
            assert type(t['covered']) is bool and type(t['source_complete']) is bool
        result[mapping[masked]]={'covered':sum(t['covered'] for t in g['targets']), 'source_complete':sum(t['source_complete'] for t in g['targets']), 'denominator':23, 'unsupported_reported':len(g['unsupported']), 'dangerous_overclaims_reported':len(g['dangerous_overclaims'])}
    return {'mechanical_validation':verify(root),'ai_judged_results':result,'inference':'No observed batch advantage; synthetic ceiling, single run, AI-authored gold and AI grading.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);p.add_argument('--prepare',type=pathlib.Path);a=p.parse_args()
    if a.prepare:prepare(a.root,a.prepare)
    print(json.dumps(summarize(a.root),indent=2))
if __name__=='__main__':main()
