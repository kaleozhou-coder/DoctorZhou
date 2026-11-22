# 重现第 17 阶段的纯文本证据核验
在 stage-17 根目录，用 Python 3.12 或 3.13、无需网络和第三方依赖。实测记录在 observed；重新跑评分是对已保存模型样本的回放，不会新调用模型。若需要新调用，将 frozen/model-prompt.zh.txt 单独传给独立模型，不提供 frozen/gold.json、评分结果或另一模型的答案。
    
    (cd frozen && sha256sum -c design-sha256.txt && sha256sum -c protocol-sha256.txt)
    sha256sum -c frozen/execution-sha256.txt
    python -B -m unittest discover -s reproduction -p 'test*.py' -v
    python -B reproduction/audit.py audit --manifest frozen/manifest.json --gold frozen/gold.json --answers observed/run-1.json
    python -B reproduction/audit.py audit --manifest frozen/manifest.json --gold frozen/gold.json --answers observed/run-2.json
    
只对给定文档快照定位引文；字符偏移针对 NFC/LF 表示。未实现 PDF/OCR 锚点、W3C RDF 导出、线上 ACL 或业务语义的通用自动判断。资料、文档编号、条件和金标均是合成实验材料，非生产合同或经过行业专家签字的合规结论。
