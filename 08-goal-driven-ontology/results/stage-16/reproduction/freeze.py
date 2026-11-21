"""Materialize paraphrased public excerpts and synthetic perturbations (no web calls)."""
import argparse, hashlib, json
from pathlib import Path
DOCS = {
"Q0": "青岛，年份2026，项目 E3702002313226505、标段 E3702002313226505001001。实验给出的答疑节选，不包含技术规格书原文、工程量清单原件或施工图原件。按资料中的项目/标段、日期、问题号和说话人判断。",
"Q4": "同项目同标段，平台第4版，6月10日，答疑通知（04），问题八。子项1：提问人称设计图材料表允许原厂柜或授权柜，问MCC柜类型。正式答复：按MEC电气施工图确定。子项2：提问人列出清单尺寸800×800×2200，图纸尺寸800×1000×2200。正式答复：尺寸依工程量清单。子项3：提问人称清单92台、图纸93台，问是否需要MCC2205。正式答复：MCC2205不需要。",
"Q6": "同项目同标段，平台第6版，6月15日，答疑（06），问题八子项1。正式答复：使用技术规格书判断MCC柜类别，限原厂生产的柜，不接收采用授权生产的柜。另有独立的开标、投标截止和保证金日期调整至7月3日。",
"Q9": "同项目同标段，平台第9版，6月26日，开标改到7月16日09:30，开标室也调整。该条目没有设备技术答复。",
"QA": "同项目同标段，平台第10版，6月26日，标题为答疑通知（08）。供电问题中答复了配电图排布及MCC柜进线电缆范围；另确认开标为7月16日09:30。所提供答复未再次讨论问题八子项1—3。",
"M0": "虚构项目 PL-204，标段 L-1，审查日期9月30日。资料台账完整，只用于确认条目存在及所属字段，不表示正文可读。J5：8月1日，L-1，问题三。J8：8月20日，L-1，问题三第(a)项，未随包提供正文；索引没有进一步内容。J9：9月3日，L-1，开标改期。索引仅说明文件和字段归属，不说明正式条款值。",
"M5": "J5，PL-204，L-1，问题三。第(a)项：正式答复，维修箱材质以设计技术图为准；现有材料未附设计技术图。第(b)项：正式答复，外观颜色为灰色。两项分别答复。",
"M9": "J9，PL-204，L-1，正式通知，开标延到9月18日。未涉及维修箱技术条件。",
"N0": "虚构项目 RS-105，标段 L-7 与 L-8，审查日期9月30日。本包发布台账已完成核对，N4、N6、N9均有正文，无未附的发布条目；下列答复只对各自标段生效。",
"N4": "N4，RS-105，L-7，9月1日，问题二：正式答复，安全标识板材质为铝，底色为蓝色。",
"N6": "N6，RS-105，L-8，9月13日，问题二：正式答复，安全标识板材质为钢，底色为黄色。该答复适用 L-8。",
"N9": "N9，RS-105，L-7，9月23日：开标日期变更，L-7 安全标识板要求不在此通知范围。",
"Y1": "宜昌，2025年6月18日，第1次澄清修改公告，问题42。投标人建议月进度款按完成工程量的80%支付，并询问是否采纳。招标方答复仍按招标文件执行。§二另说明施工合同条款依本次答疑文件。给定材料没有有效合同第12.4条正文或正式比例。"
}
IDS = {
    "front": [["Q0","Q6","Q4","Q9","QA","M0"],["M5","M9","N0","N6","N4","N9","Y1"]],
    "end":   [["Q0","Q4","Q9","QA","M0","M5"],["M9","N0","N4","N9","N6","Y1","Q6"]],
}
TASK = """这是离线语义建模测试。每份证据只适用其标注项目/标段。只依据本包，不查网、不沿用常识补值。编号表示证据定位。为每个字段提取机器值和最直接的证据编号。公开段是人工转述；另有明确标注的虚构段。空白不等于禁止、采纳或没有新文件。不要引用问题中的推测作为正式答复。
输出一个 JSON 对象，每个键对应恰好一个 [值, [证据编号...]]。字符串仅从给定选项选择；缺值用 UNKNOWN。证据列表只保留能直接支撑结论的最小集合；最多两个。不得跨项目引用。无需解释和 Markdown。
q_type_basis: DRAWING / SPEC / BOQ / UNKNOWN （青岛MCC柜类型正式依据）
q_allowed_type: OEM_ONLY / OEM_OR_AUTHORIZED / UNKNOWN （青岛MCC柜允许类型）
q_size_basis: DRAWING / SPEC / BOQ / UNKNOWN （青岛MCC柜尺寸正式依据）
q_mcc2205: REQUIRED / NOT_REQUIRED / UNKNOWN （青岛对象MCC2205）
q_opening: YYYY-MM-DD / UNKNOWN （青岛开标日期）
q_last_platform_notice_label: NOTICE_08 / NOTICE_10 / UNKNOWN （青岛平台第10版通知标题内的编号）
m_current_material_basis: DRAWING / SPEC / BOQ / UNKNOWN （PL-204 L-1维修箱材质当前正式依据）
m_color: GRAY / BLUE / UNKNOWN （PL-204 L-1维修箱颜色）
m_missing_locator: J8 / J9 / NONE / UNKNOWN （哪个缺正文定位可能影响PL-204 L-1维修箱材质）
n_material: ALUMINUM / STEEL / UNKNOWN （RS-105 L-7标识板材质）
n_color: BLUE / YELLOW / UNKNOWN （RS-105 L-7标识板颜色）
n_missing_locator: N6 / N9 / NONE / UNKNOWN （RS-105 L-7有无已知缺正文定位）
y_proposal_status: ADOPTED / NOT_ADOPTED_IN_REPLY / UNKNOWN （宜昌第42问提案是否在该答复中采纳）
y_current_ratio: 80 / OTHER / UNKNOWN （以字符串表示，问真实适用的百分比是否能由本包确定）
"""
METHOD = {
"one": "一次取齐全部证据后，直接输出最终 JSON 到指定结果文件；不要额外做第二轮。",
"batch": "先只读取 task.txt 与 part1.txt，输出非最终 JSON 到指定 draft 文件；未从第一批得到的字段用 UNKNOWN，证据可为空。先写盘完成草稿，第二次再读取 part2.txt，带上你的第一轮草稿增量修订并保存最终 JSON。不要重读第一批或访问合并材料。",
"strong": "一次取齐全部证据，先保存 JSON 草稿；再基于同一证据自查来源归属、缺件、版本范围与场景，保存最终 JSON。不得用外部信息。"
}
def materialize(dst):
    dst.mkdir(parents=True, exist_ok=True)
    def write(path, bytes_):
        (dst/path).parent.mkdir(parents=True,exist_ok=True)
        (dst/path).write_bytes(bytes_)
    write(Path("task.txt"),TASK.encode())
    for arm,(p1,p2) in IDS.items():
        for k,ids in {"part1":p1,"part2":p2,"full":p1+p2}.items():
            write(Path(arm)/f"{k}.txt",("\n\n".join(f"[{i}] {DOCS[i]}" for i in ids)+"\n").encode())
    write(Path("methods.json"),(json.dumps(METHOD,ensure_ascii=False,indent=2)+"\n").encode())
    digest={str(p.relative_to(dst)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dst.rglob("*")) if p.is_file() and p.name!="integrity.json"}
    (dst/"integrity.json").write_text(json.dumps(digest,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("destination",type=Path)
    materialize(p.parse_args().destination)
