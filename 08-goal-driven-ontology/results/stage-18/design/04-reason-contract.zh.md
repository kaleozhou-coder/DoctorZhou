# 第一轮前的错误码约定

格式无效抛 GateError；逐证据与候选响应顺序（格式→可见源→摘要→登记条款→scope/field→角色→锚点），首次遇到错误 BLOCKED。
源码/版本/rendition 不可访问 `SOURCE_NOT_ADMISSIBLE`，摘要 `EVIDENCE_HASH_MISMATCH`，登记条款不可用 `CLAUSE_NOT_ADMISSIBLE`，scope/field `DIRECT_SCOPE_MISMATCH`（任何角色同样严守范围），角色 `EVIDENCE_ROLE_MISMATCH`，quote/span `QUOTE_SPAN_MISMATCH`。若不影响统一夹具，start/end 可都 null，以唯一定位并绑定登记区间；不能取第一个。重复引用 `DUPLICATE_EVIDENCE`。无授权条目不能返回正文/匹配摘要。
其后：KNOWN 若 required_gap 或候选 gap 非空 BLOCKED `REQUIRED_GAP_MISMATCH`（不假装补件完成）；若有适用且可访问登记 CONFLICT（不依赖候选主动声明）BLOCKED `CONFLICT_PRESENT`；若直接键集不等或 required_direct 为空 BLOCKED `REQUIRED_DIRECT_MISSING`；不同值 BLOCKED `DIRECT_VALUE_MISMATCH`；完整 ELIGIBLE `DIRECT_VERIFIED`。UNKNOWN 含直接证据 BLOCKED `UNKNOWN_WITH_DIRECT`；缺件不精确或缺 CONTEXT 定位 BLOCKED `REQUIRED_GAP_MISMATCH`；精确 PENDING `REQUIRED_GAP_VERIFIED`。无人工批准或发布事务。
