# OrderFlow — V7 Migration Draft (qianyi)

OrderFlow V7 聚焦“滚动可分性(A/B) + 自适应 TVTP(只学切换) + clarity/abstain + 漂移与校准门控”，在保持 V6 治理底座的同时，补齐面向执行的最小闭环。当前分支整合了治理契约、模型骨架、验证与 CI 的首版迁移草案。

## 最小执行链（V7 草案）
> `make data.qc → make cluster.fit → make tvtp.fit → make validate → make dryrun → make release`

- `make data.qc`：生成 AB 数据对齐/校准占位报告。
- `make cluster.fit`：运行 `model/clusterer_dynamic` 在线聚类（K=2，λ≈0.97），产出 `labels_wt.parquet` 与 `cluster_artifacts.json`。
- `make tvtp.fit`：训练自适应 TVTP（仅学习切换概率），同步输出校准指标。
- `make validate`：汇总 `prototype_drift/ECE/Brier/abstain_rate/transition_hit_ratio` 至 `validation/metrics_summary.json` 与 `validation/VALIDATION.md`。
- `make dryrun`：执行层占位干跑，验证 clarity→position 映射。
- `make release`：读取 `governance/CONTROL_switch_policy.yaml` 阈值，对验证指标执行门检并记录签名。

## 关键更新
- **治理契约**：`SCHEMA_model.json`、`SCHEMA_decision.json` 增补 `clusterer_config/clarity/abstain/prototype_drift` 字段；`RULES_library.yaml` 与 `CONTROL_switch_policy.yaml` 引入新门控与低置信度处理。
- **模型骨架**：新增 `model/clusterer_dynamic`（在线聚类 + 标签对齐 + prototype_drift）与 `model/hmm_tvtp_adaptive`（A/B 切换 Logistic + clarity/abstain 推断）。
- **决策层**：`decision/engine.py` 仅在 `transition_prob>τ` 时触发方向判断器，clarity→position，低置信度直接 abstain。
- **验证与 CI**：`validation/metrics.py` 汇总核心指标；CI 流水线增加治理 schema 校验、最小链路跑通、指标门检与产物签名。

## 文档总览
- [docs/TODO_V7.md](docs/TODO_V7.md)：V7 Canonical Task Board（合并自 V6 TODO/日志）。
- [docs/MIGRATION_V6_TO_V7.md](docs/MIGRATION_V6_TO_V7.md)：迁移对照、路径映射与操作步骤。
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：分层结构、I/O 契约与门控。
- [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md)：AB 数据、微观/宏观特征与校准口径。

## 目录结构（V7 草案）
```text
/                                    # 根目录：治理/发布/执行基线
├── docs/
│   ├── TODO_V7.md                   # Canonical Task Board
│   ├── ARCHITECTURE.md              # V7 层级结构
│   ├── DATA_PIPELINE.md             # 数据/校准口径
│   ├── MIGRATION_V6_TO_V7.md        # 迁移对照
│   └── _archive/                    # V6 历史任务/日志
├── governance/
│   ├── CONTROL_switch_policy.yaml   # 漂移/ECE/Brier/abstain 门控
│   ├── RULES_library.yaml           # transition/low_confidence 规则
│   ├── SCHEMA_model.json            # clusterer_config + clarity/abstain
│   └── SCHEMA_decision.json         # clarity/abstain/reason
├── model/
│   ├── clusterer_dynamic/           # 在线聚类骨架
│   └── hmm_tvtp_adaptive/           # 自适应 TVTP 训练/推断
├── decision/
│   ├── directional_classifier.py
│   └── engine.py                    # 触发→方向→仓位映射
├── validation/
│   ├── metrics.py                   # prototype_drift/ECE/Brier/abstain_rate/hit_ratio
│   └── VALIDATION.md (生成)
├── .github/
│   ├── workflows/ci.yml             # Schema 校验 + 最小链路 + 门控
│   └── ISSUE_TEMPLATE/*, pull_request_template.md
├── Makefile                         # `make data.qc` → `make release` 流程
└── output/                          # 校准报告、聚类/TVTP 产物、签名
```

## Quickstart（V7 草案）
1. 安装依赖：`poetry install`
2. 跑通最小链路：`make data.qc && make cluster.fit && make tvtp.fit && make validate`
3. 干跑门检：`make dryrun && make release`
4. 查看指标：`cat validation/VALIDATION.md`
5. 跟踪任务：参阅 [docs/TODO_V7.md](docs/TODO_V7.md)

## 兼容提示
- 仍可参考《OrderFlow-V6项目说明书_修订_2.md》理解旧架构；迁移差异请以 `docs/MIGRATION_V6_TO_V7.md` 为准。
- CI 会对治理 schema 与验证指标执行硬门控；若新增字段/指标，需同时更新 `CONTROL_switch_policy.yaml` 与 `validation/metrics.py`。
- 产物签名记录写入 `output/signatures.json`，请在发布审核中附带。
- 旧版 HSMM 相关代码已迁移至 `model/z_legacy/`，供对比与回溯使用。
