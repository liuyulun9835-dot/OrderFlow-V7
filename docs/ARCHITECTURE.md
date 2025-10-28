# ARCHITECTURE — V7.1 with Stability Gates

> **本仓仅模型层（Model Core）。数据清洗/对齐/导出统一在 CentralDataKitchen（CDK）仓执行。**

- 数据侧详见 CentralDataKitchen 文档；本仓仅消费 [接口白名单](INTERFACE_WHITELIST.md) 中约定的输入契约。
- 模型发布后仅暴露模型产物、签名与验证结果给决策层。

## Version History
- **V7.0** (2025-10-26): Initial release with adaptive TVTP, clarity/abstain, and basic validation
- **V7.1** (2025-10-28): Added stability gate metrics for enhanced operational validation

## 层级结构（模型域）
1. **聚类层 (`model/clusterer_dynamic`)**
   - 输入：来自 CDK 的窗口化特征。
   - 输出：`model/clusterer_dynamic/cluster_artifacts.json` 等模型工件，用于状态推断。
2. **TVTP 层 (`model/hmm_tvtp_adaptive`)**
   - 输入：聚类标签 + 慢变量。
   - 输出：`model/hmm_tvtp_adaptive/artifacts/model_params.json` 与过渡概率表。
3. **状态推断 (`model/hmm_tvtp_adaptive/state_inference.py`)**
   - 生成 `transition_prob`、`clarity`、`abstain` 等信号供决策层读取。
4. **验证层 (`validation/`)**
   - 聚合 `prototype_drift`、`ECE/Brier/abstain_rate/transition_hit_ratio` 等指标。
   - 输出：`validation/metrics_summary.json`、`validation/VALIDATION.md`。
5. **稳定性门控层 (V7.1)**
   - 计算 `noise_energy`、`drift_bandwidth`、`clarity_spectrum_power`、`adversarial_gap`。
   - 阈值来自 `governance/CONTROL_switch_policy.yaml`，由 `validation/core/thresholds_loader.py` 加载。
6. **发布门控**
   - `make release` 聚合验证指标与治理阈值，生成 `models/<MODEL_NAME>/` 产物与 `status/model_core.json`。

## 治理要点
- 唯一阈值来源：`governance/CONTROL_switch_policy.yaml`。
- 发布签名：`models/<MODEL_NAME>/signature.json`。
- 验证报告：`validation/VALIDATION.md`（自动生成）。
- 产物与指标需满足 [接口白名单](INTERFACE_WHITELIST.md) 约束后才能发布。

## 与 V6 差异
- 聚类/TVTP 拆分为独立模块，便于滚动更新与漂移监控。
- 稳定性指标统一纳入验证层，自动门控关键阈值。
- 治理文件集中在 `governance/`，减少发布耦合。
