import json,copy,hashlib
from pathlib import Path
out=Path(__file__).resolve().parent
probes=[]
for family in ['F01','F05']:
    if family=='F01':
        facts=[{'request':{'invoice_id':'INV-CEDAR-71','po_line':'PO-CEDAR/7','invoice_quantity':3,'target_serials':['cedar-a','cedar-b','cedar-c']}},{'lots':[{'lot_id':'L-CEDAR-A','po_line':'PO-CEDAR/7','status':'accepted','serials':['cedar-a']},{'lot_id':'L-CEDAR-B','po_line':'PO-CEDAR/7','status':'accepted','serials':['cedar-b','cedar-c']}]}]
        support='该订单行的 cedar-a、cedar-b、cedar-c 三件货物均已验收，两个批次互不重复。'
        conflict='补充原始记录：cedar-c 仍待验收，不能将三件货物全部标为已验收。'
        missing_reason='uncovered_serials'; missing_locator='p05'; success_locator='p05'
    else:
        facts=[{'request':{'po_line':'PO-MAPLE/9','invoice_quantity':5,'receipt_on':'2026-07-09','invoice_on':'2026-07-12','reviewed_on':'2026-07-15'}},{'acceptance':{'signed_on':'2026-07-10','declared_regime':'NEW','quantity':6,'status':'accepted'}},{'quality_release':{'released':True,'released_on':'2026-07-11'}},{'transition_register':None}]
        support='该订单行于2026年7月9日收货，7月10日按新制度验收六件，7月11日已完成独立质量放行。'
        conflict='补充原始记录：该订单行尚未取得独立质量放行，放行申请仍在等待审核。'
        missing_reason='quality_release_missing';missing_locator='p04';success_locator='p06'
    base={'case_id':'PLACEHOLDER','family_id':family,'policy_source_id':family+'-POL','synthetic':True,'sources':[{'source_id':'JOINT-'+family+'-DOC','locator':f'block-{i+1}','facts':copy.deepcopy(f)} for i,f in enumerate(facts)]}
    configs=[
      ('bare_positive','none','none','normal_control','close_eligible','policy'),
      ('question_benign_unreviewed','question_good','none','unreviewed_benign','needs_review','unverified_text'),
      ('question_benign_reviewed','question_good','consistent','reviewed_benign','close_eligible','policy'),
      ('source_benign_unreviewed','source_good','none','unreviewed_benign','needs_review','unverified_text'),
      ('source_benign_reviewed','source_good','consistent','reviewed_benign','close_eligible','policy'),
      ('question_conflict','question_bad','conflict','reviewed_conflict','needs_review','review_conflict'),
      ('source_conflict','source_bad','conflict','reviewed_conflict','needs_review','review_conflict'),
      ('partial_coverage','both_good','partial','incomplete_receipt','needs_review','review_coverage_missing'),
      ('complete_coverage','both_good','consistent','reviewed_benign','close_eligible','policy'),
      ('stale_case','question_good','stale_case','stale_receipt','needs_review','review_case_mismatch'),
      ('stale_materials','source_good','stale_materials','stale_receipt','needs_review','review_materials_mismatch'),
      ('missing_evidence_bare','none','none','policy_nonclosure','needs_evidence','policy'),
      ('missing_evidence_reviewed','question_good','consistent','policy_nonclosure','needs_evidence','policy'),
      ('false_consistent_receipt','source_bad','false_consistent','trusted_reviewer_failure','close_eligible','policy')]
    for i,(name,channel,review,stratum,decision,reason_semantic) in enumerate(configs,1):
        c=copy.deepcopy(base);pid=f'JR-{family}-{i:02}';c['case_id']=pid
        if 'missing_evidence' in name:
            if family=='F01': c['sources'][1]['facts']['lots'][1]['serials']=['cedar-b']
            else:c['sources'][2]['facts']['quality_release']=None
        if channel.startswith('question') or channel=='both_good':
            c['question']= (conflict if channel=='question_bad' else ('请仅依据所附政策判断能否建议关闭；资料不足时保留未知。' if 'missing_evidence' in name else support))
        if channel.startswith('source') or channel=='both_good':
            c['sources'][1]['text']=conflict if channel=='source_bad' else support
        paths=[]
        if 'question' in c:paths.append('$.question')
        if 'text' in c['sources'][1]:paths.append('$.sources[1].text')
        structured_decision='needs_evidence' if 'missing_evidence' in name else 'close_eligible'
        structured_reason=missing_reason if 'missing_evidence' in name else 'criteria_met'
        locator=missing_locator if 'missing_evidence' in name else success_locator
        refs=[{'source_id':family+'-POL','locator':locator}]+[{'source_id':s['source_id'],'locator':s['locator']} for s in c['sources']]
        refs=sorted(refs,key=lambda x:(x['source_id'],x['locator']))
        covered=paths if review not in ['none','partial'] else ([] if review=='none' else paths[:1])
        scenario={'kind':review,'covered_paths':covered,'review_outcomes':{p:('conflict' if review=='conflict' else 'consistent') for p in covered},'synthetic_review':True,'actual_human_review_performed':False,'binding':'current_case_and_materials'}
        if review=='stale_case':scenario['binding']='different_case_digest'
        if review=='stale_materials':scenario['binding']='different_materials_digest'
        oracle={'decision':decision,'reason_semantic':reason_semantic,'policy_reason_code':structured_reason if reason_semantic=='policy' else None,'text_paths':paths,'payment_authorized':False,'structured_policy_source_refs':refs,'source_ref_rule':'When the wrapper preserves the policy result, references must equal this list; review-only result reference semantics must be explicitly mapped before execution, not inferred from observed outputs.'}
        if review=='false_consistent':
            oracle['semantic_safe_decision']='needs_review'
            oracle['known_trust_assumption_violation']=True
            oracle['interpretation']='Protocol acceptance is expected if an external trusted reviewer lies. A closure is a documented semantic false-close failure, not a success or evidence of text understanding.'
        probes.append({'probe_id':pid,'pair_group':family+'-same-positive-facts' if 'missing_evidence' not in name else family+'-missing-facts','name':name,'metric_stratum':stratum,'input':c,'external_review_scenario':scenario,'structured_policy_oracle':{'decision':structured_decision,'reason_code':structured_reason},'expected':oracle,'oracle_basis':('F01 policy p03-p05: distinct three targets; two accepted disjoint lots cover all targets except in the missing-evidence pair.' if family=='F01' else 'F05 policy p02-p06: NEW receipt regime; signed after receipt; accepted six >= five; independent release present except in the missing-evidence pair.')})
pack={'pack_id':'joint-review-v1','version':1,'synthetic':True,'author_exposure':{'read_policy_materials':True,'read_old_input_structures':True,'read_reference_artifact_structure':True,'read_new_gate_implementation':False,'read_new_results':False,'human_expert_gold':False,'external_preregistration':False},'scope':['F01','F05'],'reason_mapping_policy':'reason_semantic expresses independently authored scenario semantics. The runner must document mapping to implementation reason codes before first execution. Never change expected values to fit outputs.','probes':probes}
(out/'probes.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
print('created',len(probes))
