"""Standalone offline fixture author; imports no scheduler, scorer or gate."""
import hashlib
import json
import unicodedata
from pathlib import Path

# Fictional scenario text authored independently of planner; distinct source workflows and risks.
# id, name, disputed decision, second old unknown, stable neighboring value/field, replacement old known
specs = [
("IR14","河滨泵站质保交割","维保响应上限小时","井位照片最低张数","质保期（月）","18","设备到货提前通知日","3","5","8","4","赶在汛前交货的盖章变更","巡检照片到底含不含夜间尚待原件"),
("LX22","档案馆搬库及保密箱交接","加固周转箱每车上限","销毁前复核等待小时","运输批次数","6","搬库暂停阈值箱数","12","10","16","24","档案组补发跨楼层暂停令","销毁工单只补列表"),
("CN36","校园餐具清洗验收","每批随机复验套数","周末补送免收费本数","饭盒封签最低号码段","10","清洗液残留抽验件数","5","9","20","32","食安组电子签名决定","供应商周末补送承诺尚无正式版本"),
("KT41","医院床帘阶段供货","每抽样组经向检测片数","第三阶段安装补贴比例","首次到场工期（日）","15","首批检验权重（%）","8","11","6","30","第三次采购更正的明确计分表","拆分项价格表有修订目录，无签发正文"),
("EV55","会展临时电设施退租","雨后复用前绝缘复查点数","第二次夜班交接名单份数","入口编号","7","布设巡查提前小时","4","6","5","3","值班签收的调整记录","人数计划是草稿，须班组审定"),
("HP09","乡镇图书车数字平台迁移","账号回放抽检数量","遗留借阅冻结小时","离线借阅限量","2","甲线路备份留存天数","14","21","12","48","运营方签发经权限核对的移交清单","补报指向旧系统附件且正文尚未提交"),
]

families=[]; gold=[]
def doc(reg,doc,rev,clause,scope,field,role,line,value=None):
    text=f"完全虚构合成资料｜{reg['question']['project']}｜{doc} {rev}\n{line}\n（本条结束）\n"
    textn=unicodedata.normalize('NFC',text)
    a=textn.index(line); sha=hashlib.sha256(text.encode()).hexdigest()
    r=dict(id=clause,scope=scope,field=field,role=role,quote=line,start=a,end=a+len(line))
    if value is not None:r["value"]=value
    reg["documents"].append(dict(doc=doc,rev=rev,rendition="TXT",project=reg['question']['project'],text=text,readable=True,clauses=[r]))
    return dict(doc=doc,rev=rev,rendition="TXT",clause=clause,role=role,quote=line,start=a,end=a+len(line),raw_sha256=sha,normalized_sha256=hashlib.sha256(textn.encode()).hexdigest())
def ref(x):return ':'.join(x[key] for key in ('doc','rev','rendition','clause'))
def candidate(value,evidence=None,gap=None):
    return {"decision":{"state":"UNKNOWN" if value is None else "KNOWN","value":value},"evidence":evidence or [],"gap":gap}
def gap(scope,field,loc,slot):return dict(doc=f'ANN-{slot}',rev='R2',clause='A2',scope=scope,field=field,locator=ref(loc))
def build(p,title,sid,field,transition,priority,intake,old_v=None,v=None,mislead=False,wrong_review=False):
    scope=f'LOT-{sid}'
    reg=dict(question=dict(project=p,scope=scope,field=field),documents=[],required_direct=[],required_gap=None)
    # Structured states captured by the first round; all availability/authority labels pre-attested.
    if transition in ['stable_known','update_known','reopen_known']:
        role='DIRECT' if transition=='stable_known' else 'CONTEXT'
        prior=doc(reg,'INTAKE','R1','S1',scope,field,role,
                  f'{p} {title} {scope} 的正式首批条款：{field}为 {old_v}。',old_v if role=='DIRECT' else None)
        old=candidate(old_v,[dict(prior,role='DIRECT')])
    else:
        earlier=doc(reg,'COVER','R1','C1',scope,field,'CONTEXT',
                    f'{p} {scope} 首批登记：{field}需核 ANN-{sid} R2 §A2 后确定，未收到正文。')
        old=candidate(None,[earlier],gap(scope,field,earlier,sid))
    if transition in ['recover_unknown','update_known','stable_known']:
        authoritative=prior if transition=='stable_known' else doc(reg,f'ANN-{sid}','R2','A2',scope,field,'DIRECT',
          f'{p} {title}已签发的 {scope} 生效条款：{field}为 {v}；以本条为准。',v)
        reg["required_direct"]=[ref(authoritative)]
        reviewed=candidate(v,[authoritative])
        if mislead:
            draft=doc(reg,f'ANN-{sid}','DRAFT3','A2',scope,field,'CONTEXT',authoritative['quote'])
            # Metadata distinguishes unsigned copy despite exact quote (extracted header not in quote).
            d=reg['documents'][-1]
            d['text']=d['text'].replace('｜'+d['doc']+' DRAFT3\n','｜'+d['doc']+' DRAFT3\n')
            if wrong_review: reviewed=candidate(v,[dict(draft,role='DIRECT')])
        expected=dict(status="ELIGIBLE",reason="DIRECT_VERIFIED")
    else:
        if transition=='stay_unknown':
            locator=earlier
        else:
            locator=doc(reg,'CHANGE','R2','R4',scope,field,'CONTEXT',
                       f'{p} {title}的新签发通知明确撤回 {scope} 的旧{field}，待 ANN-{sid} R2 §A2；本次发件不含替代正文。')
        g=gap(scope,field,locator,sid); reg["required_gap"]=g
        reviewed=candidate(None,[locator],g)
        if wrong_review:
            reviewed=candidate(None,[locator],{**g,"clause":"A3"})
        expected=dict(status="PENDING",reason="REQUIRED_GAP_VERIFIED")
    slot=dict(id=sid,priority=priority,intake_signal=intake,old=old,reviewed=reviewed,gate_registry=reg)
    label=dict(id=sid,transition=transition,expected=expected,final=dict(state="UNKNOWN" if v is None else "KNOWN",value=v))
    return slot,label

for i,(p,title,first,still,neighbor,neighbor_v,changed,old_v,new_v,recovered,sibling_v,sig,not_sig) in enumerate(specs):
    # Priority inputs follow visible intake signals, not the held-out judgment.
    # Every family O1/O2 old unknown; O3 ordinary later fallback. Review queue is split by nominal intake urgency.
    # Two high-priority families already prioritize O1; one erroneous O1 simulation.
    urg_recover=(2,6,8,5,6,7)[i]
    urg_pending=(8,7,7,7,6,6)[i]
    values=[
      ("N01",changed,"update_known",1,"已登记正式更正通知，处理主批次",old_v,new_v,False,False),
      ("N02","安全停止后必要复核时长","reopen_known",3,"对来文撤回通知进行影响复核",str(i+5),None,False,False),
      ("N03","夜检记录明确移交份数","update_known",(4,4,4,4,2,4)[i],sig,str(i+1),str(i+3),False,False),
      ("S01",neighbor,"stable_known",5,"近期复核过；仅例行检查",neighbor_v,neighbor_v,False,False),
      ("S02","既有按月巡查值","stable_known",9,"未出现在新来文主题",sibling_v,sibling_v,False,False),
      ("O01",first,"recover_unknown",urg_recover,"收到关联来文，队列按接收等级而非内容最终结论",None,recovered,True,i==3),
      ("O02",still,"stay_unknown",urg_pending,not_sig,None,None,False,False),
      ("O03","滞后退场取样要求","stay_unknown",10,"旧缺件且无新来文对应题名",None,None,False,i==4)
    ]
    row={"family":p,"title":title,"slots":[]}; g={"family":p,"slots":[]}
    for args in values:
        s,l=build(p,title,*args);row["slots"].append(s);g["slots"].append(l)
    families.append(row); gold.append(g)
for name,data in (("corpus.json",families),("gold.json",gold)):
    (Path(__file__).parent/name).write_text(json.dumps({"families":data},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
