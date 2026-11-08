# 课题8：目标导向、证据约束的 AI 辅助本体建模文献核查
核查日期：2026-11-06。范围：采购应付审核中的“验收证据缺失”。本报告是定向范围综述，不是系统综述，不证明全球首次，也没有执行开源代码、访问客户数据或发表任何内容。

## 核心结论
已有研究直接覆盖目标→CQ→概念、协作增量建模、LLM 生成本体、人机分阶段校正，以及 CQ→公理溯源。因此不能把这些单项或简单组合包装成创新。尤其 2011 年 Tropos 目标建模论文直接影响课题命名与定位；2025 年 Ontogenia 和 2026 年 CQ4OE 必须进入强基线。

较有价值但尚未获证实的研究假设：在采购验收证据不完整、晚到、冲突或撤回时，以固定业务目标约束本体扩展，保留证据来源和待确认状态，通过有限人工介入，使审核判断风险低于一次性全材料建模及现有 CQ 分解方法，同时减少模型冗余和人工修订成本。创新应落在机制、可复现实验和业务损失，不是场景名称。

## 十项核实来源
### S01 · Methodology for the Design and Evaluation of Ontologies
- 作者：Michael Grüninger; Mark S. Fox。年份：1995。
- 原始来源：https://eil.mie.utoronto.ca/theory/enterprise-modelling/entmethod/
- DOI：未核实，不猜测。
- 核查深度：作者实验室方法页面，非逐页阅读全文。
- 确切贡献：从动机场景、非形式化 CQ 到术语、形式化 CQ、语义约束，以 CQ 限定本体范围。
- 重叠：业务目标先行、问题驱动建模。
- 不可声称：用 CQ 确定范围或评价本体不是创新。
- 可检验延伸：未提供 LLM 证据缺失风险实验。

### S02 · eXtreme Design with Content Ontology Design Patterns
- 作者：Valentina Presutti; Enrico Daga; Aldo Gangemi; Eva Blomqvist。年份：2009。
- 原始来源：https://ceur-ws.org/Vol-516/pap21.pdf
- DOI：未核实，不猜测。
- 核查深度：CEUR 原文 PDF，摘要与方法。
- 确切贡献：协作、增量、迭代的模式化本体设计，并有 NeOn Toolkit 插件。
- 重叠：小步建模、复用、迭代。
- 不可声称：增量与迭代本体工程本身已有成熟先例。
- 可检验延伸：没有 LLM 驱动的采购审核证据状态对照。

### S03 · Using Goal Modeling to Capture Competency Questions in Ontology-based Systems
- 作者：Paulo C. Barbosa Fernandes; Renata S.S. Guizzardi; Giancarlo Guizzardi。年份：2011。
- 原始来源：https://periodicos.ufmg.br/index.php/jidm/article/view/124
- DOI：未核实，不猜测。
- 正文：https://www.inf.ufes.br/~gguizzardi/SBBD2011_Revision_5.pdf
- 核查深度：期刊作者年份及作者版正文；作者版有占位页眉，不用于卷页元数据。
- 确切贡献：用 Tropos 从组织目标推导 CQ，再连接概念；以医疗场景展示方法。
- 重叠：直接覆盖业务目标→CQ→概念链。
- 不可声称：业务目标驱动本体或目标-CQ关联不能作为首次贡献。
- 可检验延伸：可研究 LLM 在证据逐步到达下如何控制候选模型的准入与撤回。

### S04 · The NeOn Methodology framework: A scenario-based methodology for ontology development
- 作者：Mari Carmen Suárez-Figueroa; Asunción Gómez-Pérez; Mariano Fernández-López。年份：2015。
- 原始来源：https://journals.sagepub.com/doi/10.3233/AO-150145
- DOI：10.3233/AO-150145
- 核查深度：出版社书目与摘要；全文受限，不声称全文核实。
- 确切贡献：九种开发场景、生命周期和过程指南构成方法框架。
- 重叠：需求、复用、演化的工程组织。
- 不可声称：多阶段工程工作流不是新的。
- 可检验延伸：不足以直接证明目标导向 LLM 方法在验收证据缺失下的收益。

### S05 · LLMs4OL: Large Language Models for Ontology Learning
- 作者：Hamed Babaei Giglou; Jennifer D'Souza; Sören Auer。年份：2023。
- 原始来源：https://arxiv.org/abs/2307.16648
- DOI：10.48550/arXiv.2307.16648
- arXiv：2307.16648
- 实现/材料：https://github.com/HamedBabaei/LLMs4OL
- 核查深度：作者 arXiv 摘要与接受说明；代码地址来自公开仓库检索，未运行。
- 确切贡献：评估九类 LLM 的术语类型、分类体系、非分类关系三个任务，涉及 WordNet、GeoNames、UMLS。
- 重叠：LLM 辅助本体子任务。
- 不可声称：用 LLM 抽取概念关系不是创新。
- 可检验延伸：完整业务 CQ、证据决策和人机成本不是该摘要所述评估目标。

### S06 · OntoChat: a Framework for Conversational Ontology Engineering using Language Models
- 作者：Bohui Zhang; Valentina Anita Carriero; Katrin Schreiberhuber; Stefani Tsaneva; Lucía Sánchez González; Jongmo Kim; Jacopo de Berardinis。年份：2024。
- 原始来源：https://arxiv.org/abs/2403.05921
- DOI：10.48550/arXiv.2403.05921
- arXiv：2403.05921
- 正文：https://arxiv.org/html/2403.05921v1
- 实现/材料：https://github.com/King-s-Knowledge-Graph-Lab/OntoChat
- 核查深度：arXiv 元数据与全文 §§3–4，代码和 MIT 声明来自原文；未执行。
- 确切贡献：对话支持用户故事、CQ 提取过滤分析及本体测试；Music Meta 试验含领域专家和本体工程师反馈。
- 重叠：人在回路的目标澄清与 CQ 工作台。
- 不可声称：对话、人工引导、CQ 生成与覆盖测试不新。
- 可检验延伸：以受控不完整证据评估审核错误与必要追问，而非只评价故事和 CQ 质量。

### S07 · Ontology Generation using Large Language Models
- 作者：Anna Sofia Lippolis; Mohammad Javad Saeedizade; Robin Keskisärkkä; Sara Zuppiroli; Miguel Ceriani; Aldo Gangemi; Eva Blomqvist; Andrea Giovanni Nuzzolese。年份：2025。
- 原始来源：https://arxiv.org/abs/2503.05388
- DOI：10.48550/arXiv.2503.05388
- arXiv：2503.05388
- 正文：https://arxiv.org/html/2503.05388v1
- 实现/材料：https://github.com/dersuchendee/Onto-Generation
- 核查深度：原文 §§4–6 与仓库页面；未运行。
- 确切贡献：Memoryless CQbyCQ 与 Ontogenia，从故事/CQ 生成 OWL；比较独立和增量建模，评价 CQ 覆盖、冗余与专家判断。
- 重叠：最接近 CQ 驱动增量建模及小模型评价。
- 不可声称：增量 CQ 建模和少冗余模型不能独立称新。
- 可检验延伸：其增量指多 CQ 合并/累积，并非外部证据随时间到达；可研究证据更新后的修订正确性与业务风险。

### S08 · Extended NeOn-GPT: Advancing LLM-Powered Ontology Learning Through Ontology Reuse and Automated Verification
- 作者：Nadeen Fathallah; Arunav Das; Stefano De Giorgis; Andrea Poltronieri; Peter Haase; Liubov Kovriguina; Albert Meroño-Peñuela; Elena Simperl; Steffen Staab; Alsayed Algergawy。年份：2026。
- 原始来源：https://journals.sagepub.com/doi/10.1177/22104968261453138
- DOI：10.1177/22104968261453138
- 实现/材料：https://github.com/NadeenAhmad/neon-gpt-extended
- 核查深度：出版社全文摘要及代码脚注；仓库页面打开，未运行。
- 确切贡献：NeOn 多步生成，加本体复用、外部工具验证和修复；跨四领域比较多模型。
- 重叠：工程流水线、复用、验证修复。
- 不可声称：多步提示或自动校验修复不是新贡献。
- 可检验延伸：本课题应增加审核证据状态与成本约束，而非重复结构/词汇相似性。

### S09 · Enhancing Ontology Engineering with Large Language Models: A Stage-Wise Human-in-the-Loop Study
- 作者：Xuefei Ding; Omid Pournik; Saadullah Farooq Abbasi; Linxue Bai; Gregory Epiphaniou; Nicholas Matragkas; Stuart Harrison; Carlos Luis Parra-calderón; Theodoros Arvanitis。年份：2026。
- 原始来源：https://journals.sagepub.com/doi/full/10.3233/SHTI260304
- DOI：10.3233/SHTI260304
- 核查深度：出版社全文 §§2–3 与表1。
- 确切贡献：医疗标准文本三个检查点的人机协同对照：术语、类层次、关系；人工输入改善后续阶段匹配指标。
- 重叠：分阶段人工输入、语料约束、抑制关系过生成。
- 不可声称：HITL 比 LLM-only 好不是新的研究问题。
- 可检验延伸：需预算匹配、证据批次控制和实际审核结果指标，避免把多给人工信息误当算法优势。

### S10 · CQ4OE: A benchmark for assessing LLM-assisted ontology generation from competency questions
- 作者：Jiayi Li; Ziyuan Wang; Daniel Garijo; María Poveda-Villalón。年份：2026。
- 原始来源：https://arxiv.org/abs/2609.26029
- DOI：10.48550/arXiv.2609.26029
- arXiv：2609.26029
- 正文：https://arxiv.org/html/2609.26029v1
- 实现/材料：https://github.com/oeg-upm/cq4oe-benchmark
- 核查深度：arXiv 正文及仓库 README；DOI 页面标 pending registration，优先引用 arXiv ID；未运行。
- 确切贡献：CQ→术语/公理金标准，CQ2Term 与 CQ2Onto，六本体；比较一次性、迭代和多智能体。
- 重叠：CQ 溯源、多维评估和强基线。
- 不可声称：CQ 到公理可追踪或一次性与迭代对照本身不新。
- 可检验延伸：可增加 ABox 证据批次及审核状态标签；其 CQ 公理覆盖不等于在真实证据上答对业务问题。

## 最接近工作的关键辨析
1. Ontogenia 的 Independent 不是“所有文档一次性生成”：它是每个 CQ 独立生成。其 Incremental 是多 CQ 模块合并或把先前输出放回提示。不能把论文原有对照误写成本文要求的全材料基线。
2. CQ4OE 已有 normal 一次性输入全部 CQ、CQ-by-CQ 和多智能体基线，因此本文不能只击败随意写的一次性提示。应同时包含全材料业务基线和强 CQ 基线。
3. CQ4OE 是主要面向 TBox 的基准，并不直接验证采购单据事实、晚到附件或时间截面的审核判定。其词项对齐误差会传入后续指标。可借其评估结构，不能把公理匹配率当实际问答准确率。
4. 阶段式 HITL 文献证明了已有类似比较，但其人工输入额外提供信息。本文必须记录人工分钟数、信息量、追问次数，不能让实验组获得更好证据而对照组没有。
5. 目标约束最小模型也并非空白：早期目标/CQ 方法、Ontogenia 的冗余分析和 CQ4OE 的 CQ 相关子本体都必须讨论。可将“最小充分”定义为任务损失约束下的优化目标，而不是声称首次精简本体。

## 可检验研究问题（研究设计建议，不是已发表结论）
RQ1：在证据缺失程度固定且模型调用预算相当时，目标约束的增量流程是否降低无依据的“验收已完成”判断？
RQ2：目标限制、证据准入、人工确认分别贡献多少？是否只是分批读取降低上下文长度的收益？
RQ3：新证据到达、旧证据撤回或冲突时，方法能否正确修订状态并保持无关历史判断稳定？
RQ4：在相同审核任务覆盖率/判断损失下，是否减少无关类、关系、公理及人工修订分钟数？
RQ5：为支持“缺失”判断，明确的检查范围/完整性声明是否比把图中无记录直接解释为不存在更可靠？

建议业务语义边界：
- 验收事件未发生、验收凭证未提供、提供但无法验证、凭证已过期/冲突，必须分开。
- “已检索材料中未见”不是现实世界“未验收”。模型应能输出待证，不虚构验收结果。
- 本体层定义概念及约束，实例层保存交易和附件事实，决策层保存审核规则/状态。不能把每份新单据都算新增本体概念。
- 候选建模建议与经过人工接受的版本分开。规范性要求允许源自制度/规则，不能要求每条 TBox 公理都从交易凭证提取。
- 实验使用合成或获授权脱敏材料；本文不触及真实客户数据。

## 最低强对照设计
B0：专家在固定预算内手工建模，仅在能组织真实专家实验时加入。
B1：全部当前可见材料+同一业务目标，一次性生成；给予合理系统提示、相同输出格式和确定性校验。
B2：全部当前可见材料+同样 CQ，一次性生成。这将目标/CQ 信息优势与增量机制拆开。
B3：Ontogenia / Memoryless CQbyCQ 思路的复现；标明改动，不能直接挂原系统名而不复现。
B4：NeOn 风格分阶段+校验修复。与实验组匹配工具能力。
T：目标约束、证据来源、显式待证状态、增量变更与必要人工确认。
消融：去目标筛选；去证据准入；去人工确认；随机批次/单纯分块；无增量而每轮全量重建。
注意：“全材料”只指当时可见全部材料，不能让基线提前得到未来证据。可另设最终全证据 oracle 上界，但不能混为公平实时对照。

## 数据与测量建议
- 分层合成 60–120 个案例作为试点规模建议，不是功效分析结论。覆盖部分验收、晚到验收单、签字缺失、错误采购单关联、扫描不可读、重复凭证、矛盾撤回、制度例外。
- 至少三批证据；同一案例所有方法收到相同证据批次。随机顺序或配对顺序试验，防止顺序收益。
- 盲评金标准：业务问题答案、证据充足状态、证据跨度、关键模型元素、允许的建模等价方案。开发集与测试集按模板/事件模式拆分，防止同模版泄漏。
- 主指标：有证据支持的审核状态准确率；错误判为证据充分率。预注册成本权重时再报告加权业务损失，不随结果调整权重。
- 次指标：CQ 的可执行问答正确率、证据引用正确率、无依据断言率、关键模型元素召回、冗余率、修订回归错误率、人工分钟、token/API 成本。
- 三类覆盖分别报告：模式可表达、给定事实可回答、业务证据足够作判断。
- 用同案例配对比较并给置信区间；模型版本、提示、采样、调用次数、人工预算、校验器版本均固定记录。
- 不宣称生产付款安全或财务合规，只评估审核辅助草案和证据状态。

## 开源采用与边界
优先检查 CQ4OE 的评价脚本/标注结构和 Onto-Generation 的提示/基准；OntoChat 可参考需求交互；NeOn-GPT extended 可参考多步验证。仓库真实存在不等于当前可安装、可复现或允许任意再发布。本轮未安装、未运行、未锁定 commit，也未完整审查全部许可证。CQ4OE 页面显示 Apache-2.0；OntoChat 原文说明 MIT，其余许可证仍需实际采用前检查。后续应本地记录 commit、环境、数据许可和最小冒烟测试。

## 检索覆盖与限制
检索了经典 CQ/本体工程、goal modeling/Tropos、LLM ontology learning、OntoChat、Ontogenia、NeOn-GPT、stage-wise HITL、CQ4OE。优先打开作者/大学、arXiv、CEUR、出版社与作者仓库。NeOn 2012 大学存档返回403，因此改用合法可见的2015出版社摘要，未绕过限制。
本次未系统覆盖主动学习、信念修订、truth maintenance、知识图谱 provenance、closed-world completeness、SHACL 和采购审计本体的全部文献。这些是下一轮 novelty 压力测试的必要方向。报告中“缺口”均表示本轮所核查文献没有直接建立所需证据，不表示无人研究。

