# QC_RUN (Validation)
- 将各评测任务的原始指标写入 `validation/runs/**/*.json`（格式不限，后续可在 aggregator 内适配）。
- 运行聚合器：
  ```bash
  python -m validation.core.aggregator --runs-dir validation/runs --out-dir validation
  ```
