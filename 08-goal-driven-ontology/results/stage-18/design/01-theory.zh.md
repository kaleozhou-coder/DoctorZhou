# 第18阶段 01 理论依据：原文定位不是业务证据

冻结目的：先验证受控政策下的证据门禁是否拒绝“数值正确但依据不成立”，为后续等预算模型 A/B 提供共同验收。不是本体自动发现或效果证明。

- 能力问题（CQ）先确定项目、标段、字段，再明确支持它的事实和证据；[Grüninger/Fox](https://eil.mie.utoronto.ca/wp-content/uploads/enterprise-modelling/papers/gruninger-ijcai95.pdf) 提供方法论，[CQ4OE预印本](https://arxiv.org/abs/2609.26029) 把 CQ 所需术语/公理区别评估，不验证分批材料、权威版本或真实付款。
- [ContractNLI](https://aclanthology.org/2021.findings-emnlp.164/) 区别结论及原文 spans；本原型额外固定文档身份、版本、文本提取版本、范围、证据角色和补件定位。其 NotMentioned 不等于缺件 or 不适用。
- [W3C Web Annotation](https://www.w3.org/TR/annotation-model/#text-position-selector) 类似用代码点位置与半开区间；我们额外采用 NFC+LF、原始及规范化摘要、位置和逐字引用双核。通用标注可有多目标，这不是业务证据权限。
- 不在本阶段宣称 OWL、SHACL 或国标合规；国标状态与适用范围沿既有设计分列。本阶段实现的是人工登记证据政策下的确定性校验。
