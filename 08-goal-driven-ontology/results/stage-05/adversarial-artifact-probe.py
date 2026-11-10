import json,sys,hashlib,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src'))
import rule_ir_v2 as ir
artifact={'version':'rule-ir-v2','fields':{'x':{'path':['x'],'type':'integer','enum':[None]}},'rules':[],'default':{'decision':'close_eligible','reason':'bypass','source_refs':[]}}
result={'artifact':artifact,'facts':{},'validate_returns_UNKNOWN':ir.validate(artifact) is ir.UNKNOWN,'evaluate':ir.evaluate(artifact,{},set()),'implementation_sha256':hashlib.sha256((root/'src/rule_ir_v2.py').read_bytes()).hexdigest(),'probe_kind':'post-freeze adversarial review, excluded from first-run scores'}
assert result['validate_returns_UNKNOWN'] and result['evaluate']['decision']=='close_eligible'
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path)
args=parser.parse_args()
if args.output:
    with args.output.open('x') as out:
        out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
