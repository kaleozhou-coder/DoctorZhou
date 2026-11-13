# 独立复核脚本发布可复现性补充

脚本已去除历史副本的绝对路径，采用可选参数 `--baseline-root`。默认读取本仓第七阶段历史数据并验证冻结SHA256，不将其表述为跨副本比对。指定另一个历史仓库根目录时，额外逐字节比较两个副本。输出仅打印到标准输出，不再覆盖首次审阅记录。

实际执行：默认命令通过1024项断言；指定原历史副本参数通过1029项断言。结果分别保存为 `independent-review-portable-default.json` 和 `independent-review-portable-baseline.json`。初次实际跨副本核验的事实继续保留于首次报告。

用户克隆仓库后，在课题根目录运行：

```sh
python -B results/stage-08/independent-review.py
```

若另有历史副本，可自行提供其根目录：

```sh
python -B results/stage-08/independent-review.py --baseline-root /path/to/historical-repository
```

以上改动仅涉及独立复核脚本和追加记录，未修改研究实现、历史输入或final-run输出。
