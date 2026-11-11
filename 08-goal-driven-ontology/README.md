# Goal-Driven Ontology Research / 业务目标驱动的本体建模

课题8。研究成果导向，限定采购应付“验收证据缺失异常”的 AI 辅助本体建模。

最新进展：[第六阶段报告（2026-11-11）](results/stage-06/report.zh.md)。枚举绕过及复核发现的 null/重复集合问题已修复；统一文本送审堵住已知漏检，但旧正例关闭召回降为 0/20。新探针保留无文本控制6/6，同时良性文本7/7也送审。338项工程测试通过，真实模型 A/B 仍为0。

**当前不是已完成的 AI 对照实验。** 本项目包含研究协议、文献/公开素材核验、合成语义测试与真实执行的变异测试。未使用客户数据、未进行人工审阅研究、未调用付费模型 API，不能从这些自检推断真实业务准确率或节省人工时间。

## 文件

- `protocol/research-design.zh.md`：研究设计、强对照、消融、指标与停止条件。
- `protocol/annotation-guide.zh.md`：独立标注及真人时间测量方案。
- `protocol/candidate-schema.json`：候选、来源、假设及审批状态契约。
- `research/`：核实后的文献与材料调查（每项标注证据范围）。
- `data/public/`：许可允许的公开标准样例，绝非真实业务凭证。
- `data/synthetic/`：明确标记的合成工程测试。
- `ontology/reference_model.json`：AI 编写的演示概念/规则模型，未人审；不是金标准或通用财务政策。
- `prompts/`：尚未运行的主对照提示模板。
- `src/pilot.py`：纯 Python 标准库语义变异测试。
- `results/`：实际运行输出和限制。

## 重现工程自检

要求 Python 3.10+，无额外依赖，无网络。

```sh
python -m unittest discover -s tests -v
python src/pilot.py
python src/audit_public_xml.py
```

如需重新生成同一合成夹具，运行 `python src/build_fixtures.py`。主实验必须另建独立保留测试集，不能把这里与实现共同设计的28条夹具当作泛化证据。

## 关键边界

发运、收到通知、收货、验收和付款授权不同。来源定位完整不等于来源支持结论。没有证据不等于事实为假。接收/验收政策必须来自授权业务材料，不得凭常识发明。所有研究样例仅在本地运行，不操作真实采购或财务系统。

## 第二阶段新增（2026-11-07）

- `benchmark/v1/`：6个合成政策家族、60条前瞻案例，开发/验证/测试按20/10/30家族级切分，模型输入与评价案例/标签分离。AI作者和独立AI一致性复核均不等于真人金标准。
- `src/benchmark_eval.py`：冻结校验、严格预测解析、全分母/漏答敏感性及来源定位检查。
- `src/export_model_inputs.py`：只导出政策材料，禁止把标签、案例和生成脚本混入建模包。
- `src/run_evaluator_probes.py`：15次故意使用标签的评分器工程探针，不是LLM输出。
- `experiments/v1/`：强A/B对照运行契约和准备缺口；模型后端及可执行表示尚未冻结，真实模型运行仍为0。
- `results/stage-02/report.zh.md`：今日完整结果、限制及复现说明。

```sh
python -m unittest discover -s tests -v
python src/benchmark_eval.py --benchmark benchmark/v1 --verify-only
python src/export_model_inputs.py --benchmark benchmark/v1 --output results/stage-02/model-inputs-only.zip
python src/run_evaluator_probes.py --benchmark benchmark/v1 --output results/stage-02/probes
```

不要把“全送审”的零错误关闭、只提交容易案例的高分、答案回放的100%或43项工程测试通过当成模型效果。测试材料的政策可见，交易组合隐藏；不是未知政策迁移实验。


## GitHub 归档与复现说明（2026-11-07）

- 本课题归档于 DoctorZhou 仓库的 `08-goal-driven-ontology/`，请先进入该目录再运行上述命令。
- 不提交缓存、密钥、本地私人资料及可由源码重建的重复 ZIP。`results/stage-02/model-inputs-only.zip` 可通过上述导出命令生成；校验摘要保留在 `results/stage-02/export-verification.json`。
- `results/artifact-manifest.json` 和 `results/stage-02/artifact-manifest.json` 是原阶段快照的历史清单。保留它们作为执行证据，不能把它们当成当前 GitHub 目录的完整清单。首次发布文件见 `publication/SHA256SUMS`，首次发布前复核见 `publication/verification.json`；第三阶段另有 `publication/stage03-SHA256SUMS` 和 `publication/stage03-verification.json`。
- 冻结基准的 `benchmark/v1/FILE_SHA256.json` 及其19个受校验文件保持原字节；发布整理不修改实验数据、标签、评分器或已有结果。
- 研究标签和评价案例也在公开仓库中。未来建模者只应获得单独导出的政策输入包，不能读取整个仓库；公开存档不构成隔离访问控制，也不保证训练数据污染隔离。
- 公共 XML 内的姓名、联系信息、账户示例等来自已列明许可的官方标准示例，不是用户、客户或真实业务资料；原始来源字节及权利声明均保留。

## 第三阶段新增（2026-11-08）

- 实际执行的确定性政策基线：`src/policy_baseline.py`。先按六份政策编写并冻结，再处理交易，不读取答案来生成判断。
- 首次运行完成 60/60 个合成案例，三态与主理由均符合既有标签；测试集为 30/30、错误关闭 0/20、可关闭识别 10/10。**不是 LLM 建模对照、专家金标准或真实业务准确率。**
- 72 项工程测试通过，7 个预测/报告 JSON 重跑字节一致。代码与原始证据见 `results/stage-03/`。
- 完整研究结果与边界：[第三阶段报告](results/stage-03/report.zh.md)。结果说明这组结构化合成题可由规则覆盖，不能据此证明目标驱动分批建模有优势。

```sh
python src/run_policy_baseline.py --benchmark benchmark/v1 \
  --implementation-freeze results/stage-03/implementation-freeze.json \
  --output /tmp/ontology-policy-baseline-new-run
```

输出目录必须不存在或为空，以保护首次结果。运行器先做哈希完整性检查，生成全部预测，再解析标签评分。现有家族专用规则尚不是供 A/B 模型共同生成的通用本体表示；真实模型调用仍为 0。

## 第四阶段新增（2026-11-09）

- 共同 JSON 规则解释器与 F05 参考规则。现有 F05 回顾性兼容检查 10/10，其他 50 条不支持、未执行，不能写成六家族覆盖。
- 新 30 条冻结合成压力探针：政策内 22/22，范围外保守拦截 4/8，另 4 条仍建议关闭；两类分母不能混为业务准确率。
- 全套 122 项工程测试通过，4 个新结果 JSON 重跑一致。旧基准、旧规则及历史结果未改。
- 真实模型对照、业务专家标签和真人时间测量仍未开展。[完整结果与复现](results/stage-04/report.zh.md)；[A/B 准入条件](experiments/stage-04/ab-readiness.zh.md)。

## 第五阶段新增（2026-11-10）

- 独立入口契约：旧范围外压力从 4/8 拦截到 8/8，政策内 22/22 保留；旧 60 条降为 57/60，正例关闭召回 17/20，明确记录保守送审的代价。
- 新 24 条挑战：正常控制 9/10、不安全输入不关闭 8/9、良性扩展送审 4/5。E22 仍因来源外层文本未核验而建议关闭，未隐藏或修正首轮失败。
- 共同 IR v2 扩展集合与记录操作，F01/F05 旧案例 20/20，另外 40 条不支持。参考产物手工编写，不是模型输出。
- 228 项测试通过，25 个结果 JSON 复跑相同；发布前另发现 null 枚举可绕过规则结构校验，当前 IR v2 不能接收不可信模型产物。真实模型运行仍为 0，不推断目标驱动建模优越性。
- [完整第五阶段报告](results/stage-05/report.zh.md)、[公平比较协议](experiments/stage-05/fair-comparison.zh.md)。

```sh
python src/run_stage05.py --output /tmp/ontology-stage05-new-run
```


## 第六阶段新增（2026-11-11）

- 保留旧版与原始失败，新增IR v3：枚举必须为完整有类型值，验证必须明确成功后才能执行；另修复UNKNOWN掩盖重复集合成员的问题。
- 入口v2统一声明的文本通道，E22不再关闭，但旧20个正例全部送审；不把保守拒绝宣传为理解文本。
- 新20条合成探针分开报告：无文本正常控制6/6、矛盾文本不关闭5/5、良性文本送审7/7、政策短缺控制2/2。
- 338项工程测试通过，新49个JSON和第五阶段25个JSON复跑字节一致。IR仍只支持F01/F05，新文本探针属于其他家族，不声称IR已执行它们。
- [完整报告](results/stage-06/report.zh.md)、[独立复核与失败证据](results/stage-06/code-review.md)、[公平对照准备](experiments/stage-06/fair-comparison.zh.md)。无密钥使用、无付费模型调用。

```sh
python -B src/run_stage06.py --output /tmp/ontology-stage06-new-run
```
