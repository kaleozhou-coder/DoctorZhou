# 第18阶段 03 详细设计与验收基线

- 外部夹具列表家族包含 family, registry, cases；每项 case 仅将 candidate 交运行器，expected 仅由计分器读取。
- registry.question 固定 project/scope/field；documents 含 doc/rev/rendition/project/text/readable 及 clauses。每个 clause 为 id/scope/field/role/quote/start/end 和可选 value。required_direct 是事前批准的完整 DIRECT 键集（DOC:REV:RENDITION:CLAUSE）；required_gap 为 null 或 {doc,rev,clause,scope,field,locator}，locator 同样是登记中的锚键，不能作为值的直接证据。单个家族明确以何项补件/生效前提决定 UNKNOWN。范围以受信登记为准，不信候选自称；MVP 用手工标注，不声称抽取原文字义。
- candidate.decision 为 {state:KNOWN|UNKNOWN,value:null|string}；evidence 每条精确 doc/rev/rendition/clause/role/quote/start/end/raw_sha256/normalized_sha256；candidate.gap 对齐官方结构或 null。unicode 代码点 [start,end) 基于 NFC+LF；严格文本和摘要绑定；同值跨版本、跨标段均不能代替适用证据。当前先测固定坐标定位，不将候选唯一性宣称为业务语义。
- DIRECT 代表此业务字段的直接依据，CONTEXT 仅背景/定位，CONFLICT 显示冲突不得用作支持。所有引用必须由精确登记身份/角色/位置和原文接受；未知或不可访问的材料不得披露原文。KNOWN 需无阻断冲突、无未满足精确补件、直接键集严格相等且支持值等于提出值。UNKNOWN 不输出可执行值、不提升任何来源为 DIRECT，必须提供所需精确 gap 及其 CONTEXT 定位才是正例。无截图、无 OCR 或图查询。
- 验收用至少 6 个不同合成家族，确保每家族有可受理（ELIGIBLE 或正确 PENDING）及负对照，分开报状态与原因精确匹配、错误可审核数和正确可审核数、不按字段数作自然样本量。用无门禁的值状态判断展示“数值可对、资格可错”，不作为 LLM 或公平策略 A/B。
- 运行前留存方案摘要和外部金标；分别运行 3.12/3.13，保留可重跑 JSON/测试；若实现与目标有差异，回写设计/限制并保留初版摘要。未来 A/B 的策略孰优待验证。
