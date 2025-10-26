# MIGRATION_CHECKLIST — V7 Draft

- [x] docs/TODO_V7.md 已合并旧任务并完成标签
- [x] clusterer_dynamic 最小实现可运行且产出 I/O（labels_wt + cluster_artifacts + drift）
- [x] hmm_tvtp_adaptive 仅学习切换概率并产出校准指标
- [x] 决策层只在切换触发；abstain 分支与 clarity→position 生效
- [x] validation 新指标产出并被 CI 门检（validation/metrics.py + make release）
- [x] README/迁移/架构/数据流水线文档到位
- [x] PR/Issue 模板到位；Make 最小链路能跑

参考：`validation/VALIDATION.md`、`validation/metrics_summary.json`（执行 `make validate` 后生成）。
