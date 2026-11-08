"""Reproduce a prospective, authored synthetic dataset; never run a model or reference evaluator."""
from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parent
SPLIT=json.loads((ROOT/'SPLIT.json').read_text())
FAMS={x['family_id']:x for x in SPLIT['families']}
policies={}; cases=[]; labels=[]
def dump(path,obj):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def policy(fid, paras, schema):
    ps=[{'source_id':fid+'-POL','locator':f'p{i:02d}','text':s} for i,s in enumerate(paras,1)]
    policies[fid]=ps
    dump('model-facing/'+fid+'/materials.json',{'family_id':fid,'split':FAMS[fid]['split'],'synthetic':True,'source_kind':'invented_policy','policy_paragraphs':ps,'document_schema':schema,'task':'Derive a source-grounded ontology and operational decision rules. Do not infer payment authorization. Do not read evaluator files.'})
def add(fid,n,facts,decision,reason,policy_indices,fact_indices=None,note=''):
    cid=f'{fid}-C{n:02d}'; sid=cid+'-DOC'
    paragraphs=[{'source_id':sid,'locator':f'p{i:02d}','text':json.dumps(f,ensure_ascii=False,sort_keys=True),'facts':f} for i,f in enumerate(facts,1)]
    if fact_indices is None: fact_indices=list(range(1,len(facts)+1))
    basis=[{'source_id':fid+'-POL','locator':f'p{i:02d}','support':'Normative authored policy clause: '+policies[fid][i-1]['text']} for i in policy_indices]
    basis += [{'source_id':sid,'locator':f'p{i:02d}','support':'Observed synthetic case facts: '+paragraphs[i-1]['text']} for i in fact_indices]
    cases.append({'case_id':cid,'family_id':fid,'split':FAMS[fid]['split'],'synthetic':True,'policy_source_id':fid+'-POL','question':'Is this acceptance-evidence exception eligible for a closure recommendation under this family policy?','sources':paragraphs})
    labels.append({'case_id':cid,'family_id':fid,'split':FAMS[fid]['split'],'expected_decision':decision,'required_evidence_ids':[b['source_id']+'#'+b['locator'] for b in basis],'required_reason_codes':[reason],'label_basis':basis,'payment_authorized':False,'author_rationale':note,'label_provenance':'Prospectively authored by an AI data author; not human gold and not model output.'})
C='close_eligible'; E='needs_evidence'; R='needs_review'
COMMON='This is an invented policy for positive-quantity goods in unit EA, a single invoice line, and its unique explicitly mapped purchase-order line. No service, return, credit, unit conversion, payment approval, or real transaction is covered. All named people, records, dates and organizational roles are synthetic. A closure recommendation never authorizes payment.'
CONTRACT='Apply the numbered decision checks below in their stated order and return exactly one primary reason code for the first decisive check. If all checks pass return close_eligible / criteria_met. Missing information is not rejection. needs_review means an explicit contradiction, adverse finding or structural inconsistency requiring a person; needs_evidence means evidence is absent or insufficient. Only supplied paragraphs are sources; never invent missing facts or locators.'
policy('F01',[
COMMON,
'The request states invoice_id, po_line, invoice_quantity, and distinct target_serials. Each accepted lot record carries po_line, status, lot_id, and distinct serials. The supplied snapshot contains all lot records currently available for this case. Acceptance by the designated receiving service is already authenticated; no additional signer check is required. A serial denotes one EA. Only status accepted records mapped to the request po_line can cover target_serials; wrong-line or pending records are ignored.',
'Check 1: If invoice_quantity differs from the number of distinct target_serials, return needs_review / target_count_mismatch.',
'Check 2: Among accepted, same-line lot records intersecting target_serials, any shared serial (including a serial outside the target) across different lot_id values returns needs_review / overlapping_lots. Repeated identical occurrences of the same lot_id and same payload are one record. Different payloads for one lot_id return needs_review / lot_identity_conflict before checking overlap. Records not intersecting the target do not participate.',
'Check 3: Form the union of serials of the remaining participating records. If that union does not include every target serial, return needs_evidence / uncovered_serials. Quantities on different lots are not added blindly, and extra serials are allowed. Otherwise return close_eligible / criteria_met.',
CONTRACT],{'request':{'invoice_id':'string','po_line':'string','invoice_quantity':'positive integer','target_serials':'distinct string array'},'lots':'array of {lot_id,po_line,status:accepted|pending,serials}; complete current snapshot'})
req=lambda q=4,t=None:{'request':{'invoice_id':'INV-L','po_line':'PO-L/1','invoice_quantity':q,'target_serials':t if t is not None else ['s1','s2','s3','s4']}}
def lot(id,s,line='PO-L/1',status='accepted'):return {'lot_id':id,'po_line':line,'status':status,'serials':s}
lotcases=[
(req(),[lot('a',['s1','s2']),lot('b',['s3','s4'])],C,'criteria_met',[1,2,4,5]),
(req(),[lot('a',['s1','s2','s3','s4','s5'])],C,'criteria_met',[1,2,4,5]),
(req(),[lot('a',['s1','s2']),lot('a',['s1','s2']),lot('b',['s3','s4'])],C,'criteria_met',[1,2,4,5]),
(req(),[lot('a',['s1','s2','s3'])],E,'uncovered_serials',[1,2,5]),
(req(),[lot('a',['s1','s2']),lot('b',['s3','s4'],line='PO-L/2')],E,'uncovered_serials',[1,2,5]),
(req(),[lot('a',['s1','s2']),lot('b',['s3','s4'],status='pending')],E,'uncovered_serials',[1,2,5]),
(req(),[lot('a',['s1','s2','s3']),lot('b',['s3','s4'])],R,'overlapping_lots',[1,2,4]),
(req(5),[lot('a',['s1','s2','s3','s4'])],R,'target_count_mismatch',[1,2,3]),
(req(),[lot('a',['s1','s2']),lot('a',['s1','s2','s3','s4'])],R,'lot_identity_conflict',[1,2,4]),
(req(),[lot('a',['s1','s2','x']),lot('b',['s3','s4','x'])],R,'overlapping_lots',[1,2,4])]
for n,(r,ls,d,reason,pi) in enumerate(lotcases,1):add('F01',n,[r,{'lots':ls}],d,reason,pi,note='Evaluate target cardinality, lot identity and overlap before union coverage; duplicate lot IDs are not independent evidence.')
policy('F02',[
COMMON,
'The request has po_line and invoice_quantity. Exactly one positive acceptance record is supplied, with signer, po_line and accepted_quantity. Its status and authenticity are uncontested. Authority is proven only by the independent delegation_registry snapshot. Each grant names signer, exact po_line, valid_from and valid_to ISO dates (both inclusive), and max_quantity for one record. A title, department or a grant for another line proves no authority. Assessment uses the acceptance signed_on date, not invoice or review date.',
'Check 1: An acceptance for another po_line returns needs_review / acceptance_line_mismatch. Check 2: An explicit deny entry for the same signer and exact po_line covering signed_on takes precedence over every grant and returns needs_review / explicit_authority_denial.',
'Check 3: If no grant matches signer and exact po_line and contains signed_on inclusively, return needs_evidence / authority_unproven. Check 4: Among matching grants use the largest max_quantity, do not sum limits; accepted_quantity above that maximum returns needs_review / authority_limit_exceeded.',
'Check 5: accepted_quantity below invoice_quantity returns needs_evidence / quantity_shortfall. Otherwise return close_eligible / criteria_met. Empty registry, expired grants and future grants are evidence gaps rather than explicit denials; an explicit deny matters only in its line and date scope.',
CONTRACT],{'request':'{po_line,invoice_quantity}','acceptance':'{po_line,signer,signed_on,accepted_quantity}','delegation_registry':'complete snapshot array {type:grant|deny,signer,po_line,valid_from,valid_to,max_quantity for grant}'})
def grant(q=10,line='PO-A/1',start='2026-01-01',end='2026-12-31',typ='grant'):
    d={'type':typ,'signer':'Mira','po_line':line,'valid_from':start,'valid_to':end}
    if typ=='grant':d['max_quantity']=q
    return d
def authfacts(gs,aq=6,aline='PO-A/1',signed='2026-06-15'):
    return [{'request':{'po_line':'PO-A/1','invoice_quantity':6}},{'acceptance':{'po_line':aline,'signer':'Mira','signed_on':signed,'accepted_quantity':aq}},{'delegation_registry':gs}]
authcases=[([grant()],6,'PO-A/1','2026-06-15',C,'criteria_met'),([grant(end='2026-06-15')],6,'PO-A/1','2026-06-15',C,'criteria_met'),([grant(4),grant(6)],6,'PO-A/1','2026-06-15',C,'criteria_met'),([],6,'PO-A/1','2026-06-15',E,'authority_unproven'),([grant(line='PO-A/2')],6,'PO-A/1','2026-06-15',E,'authority_unproven'),([grant(end='2026-06-14')],6,'PO-A/1','2026-06-15',E,'authority_unproven'),([grant(),grant(typ='deny')],6,'PO-A/1','2026-06-15',R,'explicit_authority_denial'),([grant(4),grant(4)],6,'PO-A/1','2026-06-15',R,'authority_limit_exceeded'),([grant()],6,'PO-A/2','2026-06-15',R,'acceptance_line_mismatch'),([grant()],5,'PO-A/1','2026-06-15',E,'quantity_shortfall')]
for n,(gs,aq,al,dt,d,reason) in enumerate(authcases,1):add('F02',n,authfacts(gs,aq,al,dt),d,reason,[1,2,3,4,5],note='Line and date scope are exact. Independent grants do not combine their quantity caps.')
policy('F03',[
COMMON,
'The request identifies invoice_quantity and po_line. All inspection entries have an authenticated authorized inspector and independent report_id. Entries map to a po_line, phase final or preliminary, status accepted/rejected/pending/unknown, and quantity. Only final entries for the target po_line are relevant; preliminary and other-line entries never affect a decision. The snapshot is the complete set of available reports, not proof that absent evidence exists.',
'Check 1: If relevant final entries include both accepted and rejected, return needs_review / contradictory_final_status even if the accepted quantity covers the invoice or its timestamp is later. There is no last-write-wins rule.',
'Check 2: If a relevant final rejection exists and no acceptance exists, return needs_review / final_rejection. An explicit rejection cannot be converted to missing evidence.',
'Check 3: If no relevant final acceptance exists, return needs_evidence / final_acceptance_missing. Check 4: Each report describes a cumulative whole-line measurement, not additive lots. Use the maximum accepted quantity among relevant final acceptances. If it is less than invoice_quantity return needs_evidence / quantity_shortfall; otherwise return close_eligible / criteria_met. Pending/unknown alongside acceptance do not contradict it.',
CONTRACT],{'request':'{po_line,invoice_quantity}','inspection_register':'array {report_id,po_line,phase:final|preliminary,status:accepted|rejected|pending|unknown,quantity,recorded_on}; complete available snapshot'})
def report(id,st,q=5,phase='final',line='PO-S/1',date='2026-07-01'):return {'report_id':id,'po_line':line,'phase':phase,'status':st,'quantity':q,'recorded_on':date}
statuscases=[([report('a','accepted')],C,'criteria_met'),([report('a','accepted'),report('b','rejected',phase='preliminary')],C,'criteria_met'),([report('a','accepted'),report('b','unknown')],C,'criteria_met'),([],E,'final_acceptance_missing'),([report('a','accepted',phase='preliminary')],E,'final_acceptance_missing'),([report('a','accepted',2),report('b','accepted',3)],E,'quantity_shortfall'),([report('a','rejected')],R,'final_rejection'),([report('a','rejected'),report('b','accepted',date='2026-07-02')],R,'contradictory_final_status'),([report('a','pending'),report('b','unknown')],E,'final_acceptance_missing'),([report('a','accepted'),report('b','rejected',line='PO-S/2')],C,'criteria_met')]
for n,(rs,d,reason) in enumerate(statuscases,1):add('F03',n,[{'request':{'po_line':'PO-S/1','invoice_quantity':5}},{'inspection_register':rs}],d,reason,[1,2,3,4,5],note='Final negative evidence is distinct from no final evidence. Whole-line reports cannot be summed.')
policy('F04',[
COMMON,
'The request gives po_line, invoice_quantity and as_of. The authenticated acceptance_ledger contains records {record_id,po_line,status,quantity,created_on} and events {event_id,type,old_id,new_id for supersede,effective_on}. Acceptances and events are authoritative only when created_on/effective_on is at or before as_of. Ignore all future records/events. This is a complete available ledger. All case records concern the same target line and exact unit EA; record IDs are unique. Status is accepted or rejected. Supersession is whole-record, not partial quantity.',
'Check 1: Active-as-of supersede events must reference both extant as-of record IDs; revoke events must reference an extant as-of old_id. An absent endpoint returns needs_evidence / ledger_endpoint_missing. Check 2: In the directed old_id -> new_id graph, any cycle returns needs_review / supersession_cycle; otherwise any old_id with more than one distinct new_id returns needs_review / supersession_fork. Identical duplicate edges have no extra effect.',
'Check 3: A revoke event permanently invalidates its old_id at effective_on. A supersede event retires its old_id at effective_on regardless of the replacement status. Revocation does not restore predecessors or propagate to successors. A successor remains usable unless itself revoked or superseded. No approval of the retired predecessor can override the successor. Retired and revoked records are excluded.',
'Check 4: If any remaining record is rejected, return needs_review / active_rejection, even if another remaining record is accepted. If there is no remaining accepted record, return needs_evidence / live_acceptance_missing. Check 5: Remaining accepted records are cumulative whole-line totals. Their maximum, never their sum, must cover invoice_quantity; otherwise needs_evidence / quantity_shortfall. If it covers return close_eligible / criteria_met.',
CONTRACT],{'request':'{po_line,invoice_quantity,as_of:ISO date}','acceptance_ledger':'{records:array {record_id,po_line,status:accepted|rejected,quantity,created_on},events:array {event_id,type:revoke|supersede,old_id,new_id for supersede,effective_on}}'})
def rec(id,q=8,st='accepted',dt='2026-05-01'):return {'record_id':id,'po_line':'PO-R/1','status':st,'quantity':q,'created_on':dt}
def ev(id,old,new=None,dt='2026-06-01'):
    x={'event_id':id,'type':'supersede' if new is not None else 'revoke','old_id':old,'effective_on':dt}
    if new is not None:x['new_id']=new
    return x
ledgercases=[([rec('a')],[],C,'criteria_met'),([rec('a'),rec('b')],[ev('e','a','b')],C,'criteria_met'),([rec('a'),rec('b'),rec('c')],[ev('e1','a','b'),ev('e2','b','c'),ev('e3','a')],C,'criteria_met'),([rec('a')],[ev('e','a')],E,'live_acceptance_missing'),([rec('a')],[ev('e','a','missing')],E,'ledger_endpoint_missing'),([rec('a'),rec('b',4)],[ev('e','a','b')],E,'quantity_shortfall'),([rec('a'),rec('b',8,'rejected')],[ev('e','a','b')],R,'active_rejection'),([rec('a'),rec('b')],[ev('e1','a','b'),ev('e2','b','a')],R,'supersession_cycle'),([rec('a'),rec('b'),rec('c')],[ev('e1','a','b'),ev('e2','a','c')],R,'supersession_fork'),([rec('a')],[ev('e','a',dt='2026-06-16')],C,'criteria_met')]
for n,(rs,es,d,reason) in enumerate(ledgercases,1):add('F04',n,[{'request':{'po_line':'PO-R/1','invoice_quantity':8,'as_of':'2026-06-15'}},{'acceptance_ledger':{'records':rs,'events':es}}],d,reason,[1,2,3,4,5],note='Resolve dated ledger integrity before checking live status and cumulative quantity.')
policy('F05',[
COMMON,
'The request includes invoice_quantity, po_line and receipt_on (ISO date or null). The boundary is 2026-07-01 inclusive. Governing regime is selected by receipt_on, never invoice_on, reviewed_on or signed_on. A receipt before the boundary uses OLD; one on or after uses NEW. The regime claim on the acceptance is not itself authoritative. Check 1: null receipt_on returns needs_evidence / receipt_date_missing.',
'The single acceptance is signed by an authenticated authorized receiver, maps to the target line, and has signed_on, declared_regime OLD or NEW, quantity, and status accepted or rejected. Check 2: signed_on before receipt_on returns needs_review / acceptance_before_receipt. Check 3: rejected returns needs_review / explicit_rejection.',
'Check 4: Under OLD an OLD acceptance is valid even if signed after the boundary; a NEW declaration is needs_review / regime_mismatch. Under NEW a NEW acceptance requires an independent quality_release, whose released value is true and whose released_on is on or after receipt_on. Absent release, released false, null released_on, or released_on before receipt_on returns needs_evidence / quality_release_missing. A false release is no proof of release, not a rejection.',
'Under NEW an OLD acceptance is grandfathered only by an independent transition_register entry for the exact po_line, explicitly permitted=true, and grandfather_until on or after receipt_on (inclusive). Missing entry, permitted=false, null grandfather_until, or expired deadline returns needs_evidence / grandfathering_unproven. A valid grandfathered OLD acceptance does not require quality_release. A transition entry for another line cannot be used. No inference from contract or invoice dates is allowed.',
'Check 5: After regime evidence is valid, acceptance.quantity must be at least invoice_quantity or return needs_evidence / quantity_shortfall. Otherwise close_eligible / criteria_met. Apply receipt-date, chronology, rejection, regime/evidence and quantity checks in exactly that order. All case dates are valid ISO dates or explicitly null, and the one supplied acceptance has no revocation or dispute.',
CONTRACT],{'request':'{po_line,invoice_quantity,receipt_on:date|null,invoice_on,reviewed_on}','acceptance':'{signed_on,declared_regime:OLD|NEW,quantity,status:accepted|rejected}','quality_release':'null or {released:boolean,released_on:date|null}','transition_register':'null or {po_line,permitted:boolean,grandfather_until:date|null}'})
def temporal(receipt='2026-07-01',reg='NEW',signed='2026-07-02',release=None,trans=None,q=7,st='accepted'):
    return [{'request':{'po_line':'PO-T/1','invoice_quantity':7,'receipt_on':receipt,'invoice_on':'2026-07-05','reviewed_on':'2026-08-01'}},{'acceptance':{'signed_on':signed,'declared_regime':reg,'quantity':q,'status':st}},{'quality_release':release},{'transition_register':trans}]
release={'released':True,'released_on':'2026-07-01'}
transition={'po_line':'PO-T/1','permitted':True,'grandfather_until':'2026-07-01'}
tempcases=[(temporal(receipt='2026-06-30',reg='OLD'),C,'criteria_met'),(temporal(release=release),C,'criteria_met'),(temporal(reg='OLD',trans=transition),C,'criteria_met'),(temporal(receipt=None,release=release),E,'receipt_date_missing'),(temporal(),E,'quality_release_missing'),(temporal(reg='OLD',trans={**transition,'grandfather_until':'2026-06-30'}),E,'grandfathering_unproven'),(temporal(signed='2026-06-30',release=release),R,'acceptance_before_receipt'),(temporal(receipt='2026-06-30',reg='NEW',release=release),R,'regime_mismatch'),(temporal(st='rejected',release=release),R,'explicit_rejection'),(temporal(release={'released':True,'released_on':'2026-06-30'}),E,'quality_release_missing')]
for n,(facts,d,reason) in enumerate(tempcases,1):add('F05',n,facts,d,reason,[1,2,3,4,5,6],note='Receipt date selects the regime; independent transition/release evidence cannot be substituted by a policy-version assertion.')
policy('F06',[
COMMON,
'The request gives target invoice_id, po_line and invoice_quantity. A closure_claim points to exactly one evidence pointer {source_id,locator}. The source_catalog is the complete available set of paragraphs; catalog metadata assigns each source kind ACCEPTANCE_RECORD, SHIPPING_NOTICE or TRAINING_MANUAL. All catalog records are authenticated. A quoted/example paragraph is not an assertion about the transaction. Structured fields and paragraph text encode the same explicit facts; an absent field means unknown. Interpret the cited paragraph itself, never an adjacent paragraph or a similar-looking identifier.',
'Check 1: If the exact source_id+locator pair is absent from source_catalog, return needs_evidence / cited_locator_missing. A source existing with another locator does not satisfy this check.',
'Check 2: Evidence requires kind ACCEPTANCE_RECORD and paragraph_mode asserted. Any other kind or mode (including quoted and example) returns needs_evidence / source_not_acceptance. Check 3: The cited paragraph must explicitly name the target invoice_id and exact po_line. If either is absent (null), return needs_evidence / linkage_missing. If present but unequal, return needs_review / cited_scope_mismatch. A same-source header is not enough.',
'Check 4: If the cited paragraph states status rejected or not_accepted, return needs_review / explicit_nonacceptance. Missing/unknown/pending status returns needs_evidence / acceptance_assertion_missing. Only literal accepted is a positive assertion. An occurrence of the word accepted inside a quotation or the phrase not accepted is not positive evidence.',
'Check 5: Positive evidence must explicitly state accepted_quantity, unit EA and signer_role RECEIVING_OFFICER. Null quantity or unit, or missing/other signer_role returns needs_evidence / acceptance_detail_missing. Explicit non-EA unit returns needs_review / unit_mismatch before signer-role checking (but after null quantity/unit checking). The officer role in an authenticated acceptance is sufficient authority under this policy, unlike F02. Quantity less than invoice_quantity returns needs_evidence / quantity_shortfall. Otherwise close_eligible / criteria_met.',
CONTRACT],{'request':'{invoice_id,po_line,invoice_quantity}','closure_claim':'{source_id,locator}','source_catalog':'array {source_id,kind,paragraphs:array {locator,paragraph_mode,invoice_id,po_line,status,accepted_quantity,unit,signer_role,text}}; actual cited locators need not exist'})
def semdoc(n,kind='ACCEPTANCE_RECORD',mode='asserted',invoice='INV-P',line='PO-P/1',status='accepted',q=3,unit='EA',signer='RECEIVING_OFFICER',locator='s01',cite='s01',text=None):
    sid=f'F06-C{n:02d}-ATT'
    p={'locator':locator,'paragraph_mode':mode,'invoice_id':invoice,'po_line':line,'status':status,'accepted_quantity':q,'unit':unit,'signer_role':signer,'text':text if text else f'{mode} record: invoice={invoice}; line={line}; status={status}; quantity={q}; unit={unit}; role={signer}.'}
    return [{'request':{'invoice_id':'INV-P','po_line':'PO-P/1','invoice_quantity':3}},{'closure_claim':{'source_id':sid,'locator':cite}},{'source_catalog':[{'source_id':sid,'kind':kind,'paragraphs':[p]}]}]
semcases=[(semdoc(1),C,'criteria_met'),(semdoc(2,q=5),C,'criteria_met'),(semdoc(3,locator='appendix.7',cite='appendix.7'),C,'criteria_met'),(semdoc(4,cite='s99'),E,'cited_locator_missing'),(semdoc(5,kind='SHIPPING_NOTICE'),E,'source_not_acceptance'),(semdoc(6,mode='quoted'),E,'source_not_acceptance'),(semdoc(7,invoice=None),E,'linkage_missing'),(semdoc(8,line='PO-P/2'),R,'cited_scope_mismatch'),(semdoc(9,status='not_accepted',text='Invoice INV-P, line PO-P/1: goods not accepted. Quantity 3 EA; receiving officer records the negative outcome.'),R,'explicit_nonacceptance'),(semdoc(10,unit='BOX'),R,'unit_mismatch')]
for n,(facts,d,reason) in enumerate(semcases,1):
    add('F06',n,facts,d,reason,[1,2,3,4,5,6],note='The catalog is a source snapshot. Pointer existence and semantic entailment are evaluated separately; parent catalog paragraph is required even when a cited locator is absent.')
    # Existing nested attachment paragraphs are also first-class locatable sources, not inferred aliases.
    case=cases[-1]
    for src in facts[2]['source_catalog']:
        for p in src['paragraphs']:
            case['sources'].append({'source_id':src['source_id'],'locator':p['locator'],'text':p['text'],'facts':{k:v for k,v in p.items() if k not in ('locator','text')},'source_kind':src['kind']})
    # For missing-locator cases the nonexistent pointer can never enter the required evidence list.
    if reason!='cited_locator_missing':
        p=case['sources'][-1]
        b={'source_id':p['source_id'],'locator':p['locator'],'support':'Actual cited synthetic attachment paragraph: '+p['text']}
        labels[-1]['label_basis'].append(b);labels[-1]['required_evidence_ids'].append(b['source_id']+'#'+b['locator'])
# Stable exact IDs and split membership are externalized instead of inferred from filenames.
assert len(cases)==60 and len({c['case_id'] for c in cases})==60
for fid in FAMS:
    cs=[c for c in cases if c['family_id']==fid]; ls=[l for l in labels if l['family_id']==fid]
    assert len(cs)==10 and {l['expected_decision'] for l in ls}=={C,E,R}
    dump('evaluator/inputs/'+fid+'.json',{'family_id':fid,'split':FAMS[fid]['split'],'cases':cs})
dump('evaluator/labels.json',{'benchmark_id':SPLIT['benchmark_id'],'label_schema_version':'1.0','cases':labels})
manifest={'benchmark_id':SPLIT['benchmark_id'],'version':'1.0.0','status':'prospective_frozen_synthetic_materials_no_model_runs','authored_on':'2026-11-07','split_file':'SPLIT.json','case_count':60,'model_facing_root':'model-facing/','evaluator_only_root':'evaluator/','families':[],'cases':[],'limitations':['All policies, documents and labels are invented by one AI data author; labels are not independently adjudicated human gold.','Six purposively chosen families and ten dependent perturbations per family cannot establish generalization or real-world performance.','No model, reference implementation or experimental arm was executed during authoring.','Policy text and cases are co-designed prospectively; this is not a naturally occurring business corpus.','All synthetic times, identities and transaction identifiers are fictional. No customer source or external download was used.','Only positive-quantity goods and exact unit semantics are covered; no automated payment or legal compliance claim is supported.','Source basis is an exact sufficient authored basis, not an exhaustive list of all logically equivalent explanations.']}
for fid,fam in FAMS.items():
    ls=[l for l in labels if l['family_id']==fid]
    manifest['families'].append({**fam,'model_materials':'model-facing/'+fid+'/materials.json','evaluator_inputs':'evaluator/inputs/'+fid+'.json','case_ids':[l['case_id'] for l in ls],'decision_counts':{d:sum(l['expected_decision']==d for l in ls) for d in [C,E,R]}})
for c in cases:manifest['cases'].append({'case_id':c['case_id'],'family_id':c['family_id'],'split':c['split'],'input_file':'evaluator/inputs/'+c['family_id']+'.json','label_file':'evaluator/labels.json'})
dump('manifest.json',manifest)
# A strict scorer may require these IDs/reasons but must not judge ontology structure by lexical identity.
dump('evaluator/prediction.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Synthetic benchmark case prediction','type':'object','additionalProperties':False,'required':['case_id','decision','evidence_ids','reason_codes','payment_authorized'],'properties':{'case_id':{'type':'string','enum':[c['case_id'] for c in cases]},'decision':{'enum':[C,E,R]},'evidence_ids':{'type':'array','items':{'type':'string'},'uniqueItems':True},'reason_codes':{'type':'array','items':{'type':'string'},'minItems':1,'maxItems':1,'uniqueItems':True},'payment_authorized':{'const':False}}})
# Structural checks only: no executable decision function is used to generate or verify authored decisions.
for l,c in zip(labels,cases):
    assert l['case_id']==c['case_id'] and l['family_id']==c['family_id']
    ids={p['source_id']+'#'+p['locator'] for p in c['sources']+policies[c['family_id']]}
    assert set(l['required_evidence_ids'])<=ids
    assert len(l['required_evidence_ids'])==len(set(l['required_evidence_ids']))
# Registry is derived from stored source paragraphs, never from pointers or expected evidence IDs.
registry={}
for fid in FAMS:
    material=json.loads((ROOT/('model-facing/'+fid+'/materials.json')).read_text())
    stored_inputs=json.loads((ROOT/('evaluator/inputs/'+fid+'.json')).read_text())
    paragraphs=list(material['policy_paragraphs'])
    paragraphs.extend(p for c in stored_inputs['cases'] for p in c['sources'])
    for p in paragraphs:
        registry.setdefault(p['source_id'],set()).add(p['locator'])
dump('evaluator/source-registry.json',{'sources':[{'source_id':sid,'locators':sorted(locs)} for sid,locs in sorted(registry.items())]})
# FILE_SHA256 excludes itself (no recursive hash); all other files, including this script and docs, are covered.
files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='FILE_SHA256.json'}
dump('FILE_SHA256.json',files)
print('Authored 6 synthetic families / 60 cases. Structural checks passed; no models or decision evaluators run.')
