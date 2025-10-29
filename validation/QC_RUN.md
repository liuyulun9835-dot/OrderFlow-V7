# QC_RUN (Validation)
- 将各评测任务的原始指标写入 `validation/runs/**/*.json`（格式可扩展，聚合器会合并常用字段）。
- 运行聚合器：
  ```bash
  python -m validation.core.aggregator --runs-dir validation/runs --out-dir validation
  ```

* 输出产物（自动生成，请勿手改）：

  * `validation/metrics_summary.json`（机器可读）
  * `validation/VALIDATION.md`（人可读汇总）
