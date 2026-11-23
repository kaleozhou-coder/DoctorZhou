# 课题 8 · 第 18 阶段：证据资格门禁

试验使用六个或以上手工合成的材料家族、其可信登记和独立判分。门禁只接收登记和候选；测试记录可复现此处结果，不应用于生产审批。无依赖、无需网络、无需模型。

```sh
cd 08-goal-driven-ontology/results/stage-18
(cd design && sha256sum -c SHA256SUMS)
python -B -m unittest discover -s tests -v
python -B run_acceptance.py fixtures.json /tmp/stage18-new.json
cmp /tmp/stage18-new.json results/acceptance.json
```

若输出文件已存在，请换新路径。先阅读 [理论](design/01-theory.zh.md)、[概要](design/02-overview.zh.md)、[详细设计](design/03-detail.zh.md) 和 [报告](report.zh.md)；改动及限制见 [回写](design-update.zh.md)。
