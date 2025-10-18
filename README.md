# OrderFlow V6（对齐《OrderFlow-V6项目说明书_修订_2.md》）
<!-- WHY: 标题显式指向修订 2.0，方便版本识别。 -->

OrderFlow V6 是一个围绕“数据 → 指标 → 状态 → 验证 → 决策 → 执行”分层构建的订单流策略研究与发布平台，当前基线已同步至《OrderFlow-V6项目说明书_修订_2.md》与《OrderFlow V6 策略诊断与改进报告.txt》的要求，强化状态可解释性、方向性治理与上线闭环。

## 核心设计（Revision 2.0）
- **两态 TVTP-HMM**：`balance / trend`，以时变转移概率替代显式“过渡态”，通过多起点拟合与 AIC/BIC 稳健性验证提升辨识度。<!-- WHY: 说明移除三态建模的原因。 -->
- **方向性判断器**：`transition(Si->Sj, prob>τ)` 触发后，利用 MFI/CVD/InformedFlow 等特征推断 bull/bear 与置信度，实现“进入趋势”与“做多/做空”解耦。<!-- WHY: 强调方向性层独立，支撑风险治理。 -->
- **宏观慢变量驱动**：在 TVTP 转移与方向判别中注入平滑宏观因子（如 MA200、资金费率），降低短窗噪声与过拟合敏感度。<!-- WHY: 体现引入 features/macro_factor/* 的目的。 -->
- **AB 双源热切换治理化**：`execution/switch_policy.yaml` 固化观察期/准入/回滚阈值，发布流水线绑定 PSI/KS/ECE 校验，确保带病回滚可追溯。<!-- WHY: 强调治理契约与发布绑定。 -->

## 文档与契约
- 《OrderFlow-V6项目说明书_修订_2.md》：架构与任务卡片主干。
- 《OrderFlow V6 策略诊断与改进报告.txt》：状态建模/方向性/治理改进建议。
- 契约文件：`governance/RULES_library.yaml`、`governance/SCHEMA_model.json`、`governance/SCHEMA_decision.json`（均已扩展支持 TVTP 两态与方向判断器字段）。
- 发布与验证产物：`output/publish_docs/VALIDATION.md`、`output/report/release.yml`、`execution/switch_policy.yaml`。

## 体系概览
1. **数据与特征**：ATAS/Binance 数据通过 manifest 与 `data/alignment/index.parquet` 对齐，新增 `features/macro_factor/*` 输出宏观慢变量，为 TVTP 转移与方向层提供稳态驱动。
2. **模型层**：`model/hmm_tvtp_hsmm/train_tvtp.py` 训练两态 TVTP-HMM，`model/hmm_tvtp_hsmm/state_inference.py` 暴露统一 `predict_proba` 接口，含转移概率与置信度。
3. **决策层**：`decision/directional_classifier.py` 计算方向判别，`decision/engine` 依据规则与评分融合状态/方向信息。
4. **验证与发布**：Validator 报告新增 bull/bear 分层与 TVTP 宏观对比摘要；`execution/switch_policy.yaml` 在发布流水线中校验绑定。

## 目录结构（新增模块已归类）
<!-- REPO_STRUCTURE_START -->

```
/                                # 根目录：治理 / 控制 / 契约 层
├── governance/
│   ├── CONTROL_switch_policy.yaml
│   ├── RULES_library.yaml                  # 新增 transition 触发字段【2.0】
│   ├── SCHEMA_model.json                   # 两态 TVTP + 宏观字段【2.0】
│   └── SCHEMA_decision.json                # 触发/方向置信字段【2.0】
├── features/
│   ├── microflow/*
│   └── macro_factor/*                      # 宏观慢变量特征【2.0】
├── model/
│   └── hmm_tvtp_hsmm/
│       ├── train_tvtp.py                   # 2-State TVTP 训练【2.0】
│       └── state_inference.py              # 状态/转移推断接口【2.0】
├── decision/
│   ├── directional_classifier.py           # 方向性判断器【2.0】
│   └── engine/*
├── execution/
│   ├── switch/
│   └── switch_policy.yaml                  # 发布绑定的 AB 热切换契约【2.0】
├── validation/
│   └── reports/*                           # Validator 分层与 TVTP 摘要【2.0】
├── output/
│   ├── publish_docs/{VALIDATION.md, ARCHITECTURE.md, release.yml}
│   └── results/*
├── docs/
│   └── migrations/*
├── data/
│   ├── raw/{exchange,atas/{bar,tick}}
│   ├── preprocessing/{schemas,align}
│   ├── calibration/
│   ├── features/
│   └── processed/
└── orderflow_v_6/*
```

<!-- REPO_STRUCTURE_END -->

## Quickstart（与 2.0 对齐）
1. 安装依赖：`poetry install`
2. 初始化目录：`python orderflow_v_6/cli/scripts/init_data_tree.py`
3. 数据更新：`python orderflow_v_6/cli/scripts/update_pipeline.py --cfg configs/data/pipeline.yaml`
4. 训练 TVTP：`python model/hmm_tvtp_hsmm/train_tvtp.py --cfg configs/model/tvtp.yaml`
5. 状态推断：`python -c "from model.hmm_tvtp_hsmm.state_inference import predict_proba; print(predict_proba(...))"`
6. 方向判别：`python decision/directional_classifier.py --snapshot snapshot.json`
7. 验证报告：`python validation/src/run_validator.py --cfg validation/configs/validator_v2.yaml`
8. 发布校验：`make release`（含 `execution/switch_policy.yaml` 绑定与 VALIDATION 摘要检查）
<!-- WHY: 快速开始步骤覆盖训练/方向/发布流程，降低错配。 -->

## Results & Reports
- `output/publish_docs/VALIDATION.md`：含 bull/bear 分层统计与 TVTP 宏观对比摘要。
- `output/report/release.yml`：记录发布批次与 `execution/switch_policy.yaml` 绑定信息。
- `output/results/merge_and_calibration_report.md`：校准与转移概率驱动分析。
- `output/qa/canary_switch_dryrun.md`：AB 热切换干跑与回滚演练结果。
- `output/results/directional_evaluation.md`：方向性判断器 ROC/AUC 与收益一致性评估。

## 兼容与迁移（2.0）
- 移除“三态”措辞与配置，统一为两态 TVTP-HMM，旧模型需重新训练。
- 新增宏观驱动、方向判别相关字段（如 `macro_factor_used`、`directional_classifier`）均向后兼容，旧产出可缺省。
- 发布流程需在 `make release` 中验证 `execution/switch_policy.yaml` 与最新 Validator 报告一致，避免带病上线。
- Validator/报告需补充 bull/bear 分层统计与宏观对比摘要，以满足治理追溯要求。
