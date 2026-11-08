"""Offline audit of pinned official XML examples; no invented acceptance conclusions."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'data/public'
NS = {'cbc':'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2','cac':'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'}
QUANTITIES={'Quantity','InvoicedQuantity','CreditedQuantity','DeliveredQuantity','ReceivedQuantity','ShortQuantity','BackorderQuantity'}

def local(tag): return tag.rsplit('}',1)[-1]
def walk(node,path):
    counts={}
    for child in node:
        tag=local(child.tag); counts[tag]=counts.get(tag,0)+1
        p=f'{path}/{tag}[{counts[tag]}]'
        yield child,p
        yield from walk(child,p)

def audit():
    manifest=json.loads((PUBLIC/'manifest.json').read_text())
    docs=[]
    for item in manifest:
        path=PUBLIC/item['path']; raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if digest != item['sha256']: raise ValueError('Hash mismatch: '+item['path'])
        root=ET.fromstring(raw)
        refs=[]
        for tag in ['OrderReference','DespatchDocumentReference']:
            for e in root.findall('cac:'+tag,NS):
                refs.append({'relation':tag,'target_id':e.findtext('cbc:ID',default='',namespaces=NS),'locator':f'/{local(root.tag)}/{tag}/ID'})
        facts=[{'field':local(e.tag),'value':e.text,'unit':e.attrib.get('unitCode'),'locator':p} for e,p in walk(root,'/'+local(root.tag)) if local(e.tag) in QUANTITIES]
        docs.append({'path':item['path'],'sha256_verified':True,'root_type':local(root.tag),'id':root.findtext('cbc:ID',default='',namespaces=NS),'ubl_version':root.findtext('cbc:UBLVersionID',default='',namespaces=NS),'references':refs,'quantity_facts':facts})
    report={'type':'offline_source_audit','data_origin':'official_specification_examples_not_real_transactions','xml_parse_and_hash_verified':len(docs),'documents':docs,'limits':['XML well-formedness only; no XSD, Schematron or signature validation was executed.','Document/header references do not prove a unique invoice-line/receipt-line match.','These examples do not supply an independent acceptance-policy or payment-authorization gold standard.','Received quantities are not relabeled as accepted quantities.']}
    (ROOT/'results/public-xml-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Parsed XML and verified pinned hashes:',len(docs))
    for d in docs:
        print(d['root_type'],d['id'],d['references'])
        for f in d['quantity_facts']: print(' ',f['locator'],f['value'],f['unit'])
    return report
if __name__=='__main__': audit()
