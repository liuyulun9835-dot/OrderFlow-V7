# V7 接口白名单

V7 仅暴露模型训练与验证相关接口；数据落地、决策执行、指标回写均在外部系统完成。

## 输入契约
- `data/manifest.json`（示例）：列出必需的 feature schema、时间范围与采样频率。
- `data/meta/`：存放 schema 与字段说明；仅保留 `.gitkeep` 以指示契约位置。
- 训练入口 `model.hmm_tvtp_adaptive.train.run_training_pipeline` 接受两段 DataFrame：
  - 聚类特征：`[bar_vpo_imbalance, bar_vpo_absorption, cvd_rolling, volprofile_skew]`
  - TVTP 特征：`state` + `[macro_regime, volatility_slope]`

## 输出制品
- `model/hmm_tvtp_adaptive/artifacts/model_params.json`：TVTP 权重、特征列表、状态命名。
- `output/tvtp/transition_prob.parquet`（或 CSV 回退）：最近训练窗口的切换概率。
- `validation/metrics_summary.json` & `validation/VALIDATION.md`：由 `validation.core.aggregator` 生成的稳定性报告。
- `publisher/dist/`：`make release` 调用 `publisher.publish` 打包的制品与 `signature.json`。

## 阈值来源
- 单一真值源：`governance/CONTROL_switch_policy.yaml`
  - `validation/core/thresholds_loader.load_thresholds()` 负责读取与标准化。
  - 任何影子文件（`validation/thresholds.yaml`、`validation/costs.yaml`）仅保留提示注释。

## 健康 / Degradation 策略
- `validation.core.aggregator` 产出的 `statuses` 字段用于 `make release` 门检。
- 若 `overall_status=fail` 或单项 `fail`，发布流程立即停止并记录原因。
- Adapter 命名空间中的额外校验需迁往 CDK/Decision/Ops 后再纳入治理。
