# OrderFlow V7 — Model Core

V7 提供“滚动可分性 + 自适应 TVTP + 稳定性门控”(Rolling separability + adaptive TVTP + stability gates) 的最小模型闭环。数据清洗、决策与执行均已外移，仓库专注于模型训练、校验与发布。

## 最小执行链
```text
data.qc → cluster.fit → tvtp.fit → validate → release
```
1. `make data.qc`（可选外部实现）准备输入契约所需的 schema/manifest 占位。
2. `make cluster.fit` 由 `model.hmm_tvtp_adaptive.train.run_training_pipeline` 触发在线聚类阶段。
3. `make tvtp.fit` 同一入口继续训练 TVTP，输出权重与校准报告。
4. `make validate` 调用 `validation.core.aggregator` 汇总噪声/漂移稳定性指标。
5. `make release` 读取 `validation/metrics_summary.json` 与 `governance/CONTROL_switch_policy.yaml` 判门后交由 `publisher.publish` 打包产物。

## 关键链接
- [接口白名单](docs/INTERFACE_WHITELIST.md)
- [阈值治理策略](governance/CONTROL_switch_policy.yaml)
- [验证报告（自动生成）](validation/VALIDATION.md)

> `validation/VALIDATION.md` 由 `validation.core.aggregator` 生成，请勿手工修改。

## 范围说明
- V7 仅维护模型与验证层；数据侧清洗与复杂特征见 Central Data Kitchen（CDK）。
- Adapter 命名空间（features/adapter、validation/adapter、scripts/audit\*.py）标记为外移候选，后续将迁往 CDK/Decision/Ops。
