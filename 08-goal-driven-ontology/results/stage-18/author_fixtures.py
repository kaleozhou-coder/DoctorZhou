"""Authorship only. No gate implementation may be imported or executed here."""
import copy
import hashlib
import json
import unicodedata
from pathlib import Path

root=Path(__file__).parent
families=[]
def family(name,p,s,f):
    reg={"question":{"project":p,"scope":s,"field":f},"documents":[],"required_direct":[],"required_gap":None}
    row={"family":name,"registry":reg,"cases":[]}
    families.append(row)
    return row

def document(row,doc,rev,clause,role,quote,value=None,*,scope=None,project=None,field=None,
             rendition="TXT",readable=True, prefix="完全虚构资料｜测试工件\n"):
    registry=row["registry"]; q=registry["question"]
    text=prefix+quote+"\n（记录结束）\n"
    normalized=unicodedata.normalize("NFC",text.replace("\r\n","\n").replace("\r","\n"))
    start=normalized.index(quote)
    rec={"id":clause,"scope":scope or q["scope"],"field":field or q["field"],"role":role,"quote":quote,
         "start":start,"end":start+len(quote)}
    if value is not None: rec["value"]=value
    registry["documents"].append({"doc":doc,"rev":rev,"rendition":rendition,"project":project or q["project"],
                                  "text":text,"readable":readable,"clauses":[rec]})
    return {"doc":doc,"rev":rev,"rendition":rendition,"clause":clause,"role":role,"quote":quote,
         "start":start,"end":start+len(quote),"raw_sha256":hashlib.sha256(text.encode()).hexdigest(),
         "normalized_sha256":hashlib.sha256(normalized.encode()).hexdigest()}

def same_rendition(row, first, second):
    # Join published clauses in a single document so the wrong-lot test changes
    # only the clause/scope and retains the same physical source identity.
    docs=row["registry"]["documents"]
    a,b=docs[-2:]
    assert (a["doc"],a["rev"])==(b["doc"],b["rev"])
    old=len(a["text"])
    a["text"]+=b["text"]
    b["clauses"][0]["start"]+=old
    b["clauses"][0]["end"]+=old
    a["clauses"].extend(b["clauses"])
    docs.pop()
    second["rendition"]=first["rendition"]
    second["start"]+=old
    second["end"]+=old
    sha=hashlib.sha256(a["text"].encode()).hexdigest()
    for ev in (first,second):
        ev["raw_sha256"]=ev["normalized_sha256"]=sha

def ref(r): return ":".join(r[k] for k in ["doc","rev","rendition","clause"])
def set_direct(row,*r): row["registry"]["required_direct"]=[ref(e) for e in r]
def set_gap(row,gap_doc,gap_rev,gap_clause,loc):
    q=row["registry"]["question"]
    row["registry"]["required_gap"]=dict(doc=gap_doc,rev=gap_rev,clause=gap_clause,scope=q["scope"],field=q["field"],locator=ref(loc))
    return copy.deepcopy(row["registry"]["required_gap"])
def case(row,name,status,reason,evidence,value=None,*,gap=None,state=None):
    c={"id":name,"candidate":{"decision":{"state":state or ("KNOWN" if value is not None else "UNKNOWN"),"value":value},
                             "evidence":copy.deepcopy(evidence),"gap":copy.deepcopy(gap)},
      "expected":{"status":status,"reason":reason}}
    row["cases"].append(c)

r=family("RB-41-角色语境","RB-41","SHELF-A","inspection_period_days")
a=document(r,"RB-ORDER","B2","A1","DIRECT","RB-41 货架 A 段：正式签发的巡检方案规定本段巡检周期为 12 自然日。","12")
b=document(r,"RB-GUIDE","G4","B7","CONTEXT","RB-41 货架 A 段配套培训讲义：练习中用 12 自然日举例；本页不发布正式巡检规范。")
c=document(r,"RB-REQUEST","P3","E1","CONTEXT","RB-41 货架 A 段运营建议单拟改为 8 自然日，未获发布，作为被拒建议保留。")
set_direct(r,a)
case(r,"RB-01","ELIGIBLE","DIRECT_VERIFIED",[a,b,c],"12")
case(r,"RB-02","BLOCKED","REQUIRED_DIRECT_MISSING",[b,c],"12")
case(r,"RB-03","BLOCKED","EVIDENCE_ROLE_MISMATCH",[dict(b,role="DIRECT")],"12")

r=family("PC-08-同版错标段","PC-08","LOT-B","notice_days")
a=document(r,"PC-TENDER","R7","L18","DIRECT","PC-08 标段 B 的现行 R7 正式澄清：交付验收预约须提前 6 自然日通知。","6")
b=document(r,"PC-TENDER","R7","L19","DIRECT","PC-08 标段 C 的同一 R7 正式澄清：交付验收预约须提前 6 自然日通知。","6",scope="LOT-C",rendition="TXT-C")
same_rendition(r,a,b)
c=document(r,"PC-SCOPE","L1","S1","CONTEXT","PC-08 分标说明：B 为消防传感器，C 为排风风机；同版号不代表跨标段共用条款。")
set_direct(r,a)
case(r,"PC-01","ELIGIBLE","DIRECT_VERIFIED",[a,c],"6")
case(r,"PC-02","BLOCKED","DIRECT_SCOPE_MISMATCH",[b],"6")
case(r,"PC-03","BLOCKED","DIRECT_SCOPE_MISMATCH",[a,b],"6")

r=family("QG-60-同文无签署","QG-60","CENTRE","replacement_years")
q="QG-60 中央库：防水圈的周期性更换期限为 4 年。"
a=document(r,"QG-MANUAL","FINAL","P4","DIRECT",q,"4",prefix="完全虚构资料｜已完成签发的中央库手册\n")
b=document(r,"QG-MANUAL","DRAFT","P4","CONTEXT",q,prefix="完全虚构资料｜同文送审样，未签发\n")
c=document(r,"QG-MANUAL","FINAL","P4","DIRECT",q,"4",rendition="PRIVATE",readable=False,prefix="完全虚构资料｜不可访问的另一复本\n")
set_direct(r,a)
case(r,"QG-01","ELIGIBLE","DIRECT_VERIFIED",[a,b],"4")
case(r,"QG-02","BLOCKED","EVIDENCE_ROLE_MISMATCH",[dict(b,role="DIRECT")],"4")
case(r,"QG-03","BLOCKED","REQUIRED_DIRECT_MISSING",[b],"4")
case(r,"QG-04","BLOCKED","SOURCE_NOT_ADMISSIBLE",[a,c],"4")

r=family("WD-33-撤回且替代正文缺件","WD-33","DEPOT-N","initial_training_hours")
a=document(r,"WD-OLD","V1","R3","CONFLICT","WD-33 北库先前手册 V1 写首训 16 小时；对应条款已被撤回，不能作为现行规定。")
b=document(r,"WD-CIRC","V2","W9","CONTEXT","WD-33 北库正式撤回通知 W9 撤回 V1 的 R3；首训时长以 WD-NEW V3 的 T2 正文为准。该正文未随本批资料传入。")
g=set_gap(r,"WD-NEW","V3","T2",b)
case(r,"WD-01","PENDING","REQUIRED_GAP_VERIFIED",[b,a],gap=g)
case(r,"WD-02","BLOCKED","EVIDENCE_ROLE_MISMATCH",[dict(a,role="DIRECT"),b],"16")
case(r,"WD-03","BLOCKED","REQUIRED_GAP_MISMATCH",[b],gap=dict(g,clause="T3"))

r=family("SP-71-完整补件两段联合","SP-71","KIOSK-X","reset_wait_hours")
a=document(r,"SP-RATIFY","R5","C2","DIRECT","SP-71 X 区终端的正式生效签发页 C2 指定 SP-ANNEX R5 第 B11 条为断电复位等待时间的现行规定；本签发页不载数值。")
b=document(r,"SP-ANNEX","R5","B11","DIRECT","SP-71 X 区终端 R5 附页 B11：断电复位至少等待 9 小时。","9")
c=document(r,"SP-CHANGE","R4","H1","CONTEXT","SP-71 X 区终端升级背景：更换控制器但不据此推定复位等待时长。")
set_direct(r,a,b)
case(r,"SP-01","ELIGIBLE","DIRECT_VERIFIED",[a,b,c],"9")
case(r,"SP-02","BLOCKED","REQUIRED_DIRECT_MISSING",[b,c],"9")
case(r,"SP-03","BLOCKED","DIRECT_VALUE_MISMATCH",[a,b],"8")
case(r,"SP-04","BLOCKED","EVIDENCE_HASH_MISMATCH",[a,dict(b,raw_sha256="0"*64)],"9")

r=family("LM-23-到件仅封面仍缺正文","LM-23","PLANT-W","noise_limit_dba")
a=document(r,"LM-INDEX","C1","I2","CONTEXT","LM-23 西区机房勘验移交目录 I2 载明夜间噪声限值见 LM-ATT C3 §Q7；收到的附件只有封面与页码登记，尚无 Q7 正文。")
b=document(r,"LM-ATT","C3","COVER","CONTEXT","LM-23 西区机房 C3 扫描覆盖页：页脚出现「65 dBA」制表测试字样，但未载 Q7 或发布夜间限值。")
c=document(r,"LM-REC","C2","S2","CONFLICT","LM-23 西区机房项目经理向签发组建议夜间用 65 dBA；未采纳，最终条款不可由此推断。")
g=set_gap(r,"LM-ATT","C3","Q7",a)
case(r,"LM-01","PENDING","REQUIRED_GAP_VERIFIED",[a,b,c],gap=g)
case(r,"LM-02","BLOCKED","REQUIRED_GAP_MISMATCH",[b],gap=dict(g,locator=ref(b)))
case(r,"LM-03","BLOCKED","EVIDENCE_ROLE_MISMATCH",[dict(b,role="DIRECT")],"65")
case(r,"LM-04","BLOCKED","QUOTE_SPAN_MISMATCH",[dict(a,start=a["start"]+1),b],gap=g)

(root/"fixtures.json").write_text(json.dumps(families,ensure_ascii=False,indent=2)+"\n")
