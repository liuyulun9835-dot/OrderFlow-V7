# OrderFlow V7 — Model Core

> **本仓仅模型层（Model Core）。数据清洗/对齐/导出统一在 CentralDataKitchen（CDK）仓执行。**

V7 提供“滚动可分性 + 自适应 TVTP + 稳定性门控”(Rolling separability + adaptive TVTP + stability gates) 的最小模型闭环。数据清洗、决策与执行均已外移，仓库专注于模型训练、校验与发布。

## 最小执行链
```text
install → lint → test → validate → release
```
1. `make install` 安装开发依赖。
2. `make lint` 运行代码静态检查（ruff + mypy）。
3. `make test` 执行单元与集成测试。
4. `make validate` 调用 `validation.core.aggregator` 汇总指标并生成 `validation/VALIDATION.md`、`validation/metrics_summary.json`。
5. `make release` 基于校验结果与 `governance/CONTROL_switch_policy.yaml` 打包模型产物。

## 关键链接
- [接口白名单](docs/INTERFACE_WHITELIST.md)
- [阈值治理策略](governance/CONTROL_switch_policy.yaml)
- [验证报告（自动生成）](validation/VALIDATION.md)

> `validation/VALIDATION.md` 由 `validation.core.aggregator` 生成，请勿手工修改。

## 范围说明
- V7 仅维护模型与验证层；详细数据流程、特征加工与导出请参见 Central Data Kitchen（CDK）。
- Adapter 命名空间（features/adapter、validation/adapter 等）标记为外移候选，后续将迁往 CDK/Decision/Ops。

## 模型侧自检脚本
- `python scripts/check_model_release.py`：检查模型产物目录、签名文件、验证输出与治理状态文件是否齐备，用于模型发布前的最终自检。
