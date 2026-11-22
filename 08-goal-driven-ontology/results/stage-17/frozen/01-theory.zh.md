# 第 17 阶段 · 理论与验证边界
问题：第 16 阶段已经给模型编过字段。本阶段先回答更低一级的可行性问题：不给字段值，只给普通中文条款，AI 候选能否逐条定位到原文？定位正确能否避免语义或版本错误？
理论：由能力问题（CQ）限定候选，不让模型自由生成任意本体；来源锚点借鉴 W3C Web Annotation 文本引用与位置选择器。锚点回答“这段字在哪里”，独立人工金标回答“它是否足以支持这次结论”，二者不能替代。PROV-O 的引用/派生链只描述来源，不赋予事实权威。覆盖证据不足是 UNKNOWN，不是猜值或否定事实。
参考：Grüninger & Fox, https://eil.mie.utoronto.ca/wp-content/uploads/enterprise-modelling/papers/gruninger-ijcai95.pdf ；W3C https://www.w3.org/TR/annotation-model/#text-quote-selector 、https://www.w3.org/TR/prov-o/#wasQuotedFrom 。
局限：合成文本，不验证 PDF/OCR、生产身份、覆盖率、发布、OWL/SHACL 推理器，不宣称国标符合性。这里验证的是事实/约束候选的一段输入链，不是全自动生成通用行业本体。
