# Stage 19：旧 UNKNOWN 复核槽配对回放
从本目录运行，Python 3.12 或 3.13，纯标准库，无网络。所有资料为虚构文本；复核答复预先提供，不调用 LLM。先看 [报告](report.zh.md)、[详细设计](design/03-detail.zh.md) 和 [回写](design-update.zh.md)。

```sh
sha256sum -c design/SHA256SUMS-baseline design/SHA256SUMS-inputs
python -B src/stage19.py run --input corpus.json --arm A > /tmp/s19-a.json
python -B src/stage19.py run --input corpus.json --arm B > /tmp/s19-b.json
python -B src/stage19.py score --observed-a /tmp/s19-a.json --observed-b /tmp/s19-b.json --gold gold.json > /tmp/s19-score.json
cmp /tmp/s19-score.json second-attempt/py312/score.json
python -B -m unittest discover -s tests -v
```

首跑保留在 `first-attempt/`。复跑同时保留两套 Python 的命令、SHA-256 和状态，`second-attempt/` 下的输出为确定性结果而不是业务数据。用 `author_families.py` 可重建摘要锁定的纯合成输入，建议仅在工作副本重建。该原型不会访问真实仓库或批准发布本体。
