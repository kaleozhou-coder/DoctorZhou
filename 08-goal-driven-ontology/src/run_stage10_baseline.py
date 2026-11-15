"""Transparent sentence-selection baseline; not a language model or ontology learner."""
import argparse,json,re,pathlib
CUES=re.compile(r'\b(requir\w*|must|only|not|never|neither|unknown|at most|exactly|approval|approver|means|absolute|replaces|unchanged)\b',re.I)
def extract(packet):
    return [dict(case_id=c['case_id'],facts=[dict(subject='policy',relation='states',value=s.strip(),sources=[d['id']],status='proposed') for d in c['documents'] for s in re.split(r'(?<=[.!?])\s+',d['text']) if CUES.search(s)]) for c in packet]
def main():
    a=argparse.ArgumentParser();a.add_argument('--materials',type=pathlib.Path,required=True);a.add_argument('--output',type=pathlib.Path,required=True);v=a.parse_args()
    if v.output.exists(): raise SystemExit('Refusing to overwrite output')
    v.output.write_text(json.dumps(extract(json.loads(v.materials.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
