# ARCHITECTURE — V7 Draft

```
Data → Clusterer Dynamic → Adaptive TVTP → State Inference → Decision Engine → Validation → Release
```

## 层级结构
1. **数据层**
   - AB 双源（ATAS/Exchange）按 manifest 管理。
   - `make data.qc` 生成 `output/calibration_report.md`（含缺失率/对齐结果）。
2. **聚类层 (`model/clusterer_dynamic`)**
   - 输入：最近窗口微观特征（`bar_vpo_*`, `cvd`, `volprofile`）。
   - 过程：在线 K=2 聚类 + 标签对齐（Hungarian 简化）+ prototype_drift 计算。
   - 输出：`output/clusterer_dynamic/labels_wt.parquet`（或 CSV fallback）、`model/clusterer_dynamic/cluster_artifacts.json`、`output/cluster_alignment.log`。
3. **TVTP 层 (`model/hmm_tvtp_adaptive`)**
   - 输入：A/B 标签 + 宏观慢变量。
   - 训练：仅学习 A→B 切换概率，使用简化 Logistic SGD。
   - 输出：`output/tvtp/transition_prob.parquet`（或 CSV）、`output/tvtp/calibration_report.json`、`model/hmm_tvtp_adaptive/artifacts/model_params.json`。
4. **状态推断 (`model/hmm_tvtp_adaptive/state_inference.py`)**
   - 根据保存的系数输出 `transition_prob`、clarity（熵归一化）与 `abstain`。
5. **决策层 (`decision/engine.py`)**
   - 逻辑：`transition_prob > τ` 才调用方向判断器，clarity→position 映射表来自 `CONTROL_switch_policy.yaml`。
   - `abstain=True` 时仓位强制 0，并写入 reason。
6. **验证层 (`validation/metrics.py`)**
   - 聚合 `prototype_drift`（读取聚类 artifacts）、`ECE/Brier/abstain_rate/transition_hit_ratio`。
   - 输出：`validation/metrics_summary.json`、`validation/VALIDATION.md`。
7. **发布门控**
   - `make release` 读取 `CONTROL_switch_policy.yaml` 的阈值，对验证指标执行硬门控并写入 `output/signatures.json`。

## I/O 契约摘要
| 模块 | 输入 | 输出 | 备注 |
| --- | --- | --- | --- |
| clusterer_dynamic | `DataFrame[features]` | `labels_wt.parquet`, `cluster_artifacts.json`, `cluster_alignment.log` | 支持 CSV fallback |
| hmm_tvtp_adaptive.train | `DataFrame[state + macros]` | `transition_prob.parquet`, `calibration_report.json`, `model_params.json` | A→B 切换数据子集 |
| hmm_tvtp_adaptive.state_inference | `DataFrame[features]` | `DataFrame[transition_prob, clarity, abstain, reason]` | clarity 基于熵 |
| decision.engine | direction features + inference 输出 | `DecisionResult`（label, position_size, abstain, reason, transition_prob, clarity） | position_size 来自 clarity breakpoints |
| validation.metrics | `DataFrame[transition_prob, actual_transition, clarity, abstain]` | `metrics_summary.json`, `VALIDATION.md` | 自动补全缺失列 |

## 门控/阈值
- `governance/CONTROL_switch_policy.yaml`
  - `drift_metrics.prototype_drift.{warn,fail}`
  - `calibration.{ece.fail, brier.fail}`
  - `abstain_rate.{min,max}`
  - `transition_hit_ratio.min`
  - `clarity_mapping.{breakpoints,position_scale}`
- CI 在 `make release` 阶段执行门控；指标超阈值将触发失败。

## 与 V6 差异
- 聚类/TVTP 拆分为独立模块，便于滚动更新与漂移监控。
- 决策层明确 clarity→position 映射与 `abstain` 分支，避免低置信度误触发。
- 验证指标集中在单一入口 `validation/metrics.py`，输出结构化 JSON + Markdown。
- CI 新增治理 schema 校验、最小链路跑通与产物签名步骤。
