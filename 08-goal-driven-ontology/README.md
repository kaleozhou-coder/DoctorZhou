# Goal-Driven Ontology Research / 业务目标驱动的本体建模

课题8。研究成果导向，限定采购应付“验收证据缺失异常”的 AI 辅助本体建模。

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
- `results/artifact-manifest.json` 和 `results/stage-02/artifact-manifest.json` 是原阶段快照的历史清单。保留它们作为执行证据，不能把它们当成当前 GitHub 目录的完整清单。当前发布文件见 `publication/SHA256SUMS`，发布前复核见 `publication/verification.json`。
- 冻结基准的 `benchmark/v1/FILE_SHA256.json` 及其19个受校验文件保持原字节；发布整理不修改实验数据、标签、评分器或已有结果。
- 研究标签和评价案例也在公开仓库中。未来建模者只应获得单独导出的政策输入包，不能读取整个仓库；公开存档不构成隔离访问控制，也不保证训练数据污染隔离。
- 公共 XML 内的姓名、联系信息、账户示例等来自已列明许可的官方标准示例，不是用户、客户或真实业务资料；原始来源字节及权利声明均保留。
