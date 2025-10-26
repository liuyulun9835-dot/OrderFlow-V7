# MIGRATION_V6_TO_V7

本文件记录从 OrderFlow V6（Revision 2.0）迁移至 V7 草案的关键差异、映射关系与执行步骤。

## 概览
- **定位**：V7 聚焦滚动可分性、只学习切换概率的 TVTP、clarity/abstain 信号与漂移/校准门控。
- **治理**：schema 与 CONTROL 阈值已更新；旧 TODO/日志归档至 `docs/_archive/`。
- **代码骨架**：新增在线聚类与自适应 TVTP 模块；决策层与验证层同步改造。

## 继承
- 数据采集/对齐流程沿用 V6（ATAS + Exchange 双源 + manifest 签名）。
- 治理契约基础（RULES/CONTROL）继续使用 V6 模板，新增字段保持向后兼容。
- CI 基座仍执行 lint/test/compliance/cost/signature 校验。

## 修改
| 模块 | V6 路径 | V7 路径 | 说明 |
| --- | --- | --- | --- |
| 聚类 | `model/hmm_tvtp_hsmm/*` 中的标签生成脚本 | `model/clusterer_dynamic/fit.py` | 改为在线聚类 + prototype_drift 指标 |
| TVTP | `model/hmm_tvtp_hsmm/train_tvtp.py` | `model/hmm_tvtp_adaptive/train.py` | 仅使用 A/B 标签与宏观因子学习切换概率 |
| 决策 | `decision/engine/*` | `decision/engine.py` | transition 触发 + clarity→position + abstain |
| 验证 | `validation/src/*` | `validation/metrics.py` | 汇总核心指标并输出 `VALIDATION.md` |
| CI | `make lint/test` + legacy gates | + `make data.qc/cluster.fit/tvtp.fit/validate/release` | 跑通最小链路并依据 CONTROL 门检 |

## 废弃/归档
- `order_flow_v_6_todo.md` 及 `docs/工程日志_*` 移动至 `docs/_archive/`（保留历史参考）。
- 旧版 `model/hmm_tvtp_hsmm` 仍在仓库中供比对，但 V7 首选 `model/hmm_tvtp_adaptive`。

## 执行步骤
1. **同步治理契约**：按需在项目管理系统更新 schema 版本号与 CONTROL 阈值。
2. **数据侧检查**：确认 `make data.qc` 报告无 ERROR，补齐 manifest 签名。
3. **模型训练**：使用新骨架跑通 `make cluster.fit` 与 `make tvtp.fit`，检视产出的 `cluster_artifacts.json` 与 `transition_prob.parquet`。
4. **验证门控**：执行 `make validate` 与 `make release`，确保指标满足 `governance/CONTROL_switch_policy.yaml`。
5. **文档对齐**：更新 README/ARCHITECTURE/DATA_PIPELINE，并在 PR 模板中粘贴指标与签名。

## 相关链接
- [docs/TODO_V7.md](TODO_V7.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/DATA_PIPELINE.md](DATA_PIPELINE.md)
