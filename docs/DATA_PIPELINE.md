# DATA_PIPELINE — V7 Draft

## 数据来源
- **AB 双源**：
  - A：ATAS 导出 1m 订单流（`market_data_YYYYMMDD.json` + `latest.json` manifest）。
  - B：交易所 1m K 线（Binance/OKX），落盘 `data/exchange/{symbol}/kline_1m.parquet`。
- **Manifest 签名**：初始包/增量包需写入 `schema_version`, `exporter_version`, `checksum`，并保存在 `data/calibration/manifest/`。

## 校准流程
1. 对齐：以 UTC 分钟索引合并 ATAS/Exchange，检查缺失率 ≤0.1%。
2. 校准：输出 `output/calibration_report.md`，记录字段完整率、时间对齐误差、重放水位。
3. 成本：维护 `output/cost_profiles.json`（base/+50%/×2）。

## 特征口径
- **微观**：
  - `bar_vpo_imbalance`, `bar_vpo_absorption`: 以窗口内累积主动买卖差计算。
  - `cvd_rolling`: Cumulative Volume Delta，窗口对齐于聚类 `window_size`。
  - `volprofile_skew`: 体积分布偏度，用于漂移监控。
- **宏观**：
  - `macro_regime`: 平滑趋势指标（如 MA200/价格动量）。
  - `volatility_slope`: 波动率斜率，作为 TVTP 外生驱动。
- 所有特征需在 `clusterer_config.features` 与 `TrainingConfig.feature_columns` 中声明。

## 输出产物
| 步骤 | 路径 | 描述 |
| --- | --- | --- |
| data.qc | `output/calibration_report.md` | 对齐/校准占位报告 |
| cluster.fit | `output/clusterer_dynamic/labels_wt.parquet`、`model/clusterer_dynamic/cluster_artifacts.json` | 聚类标签 + prototype_drift |
| tvtp.fit | `output/tvtp/transition_prob.parquet`、`output/tvtp/calibration_report.json` | 切换概率 + 校准指标 |
| validate | `validation/metrics_summary.json`、`validation/VALIDATION.md` | 门控指标汇总 |
| release | `output/signatures.json` | 产物哈希签名 |

## 注意事项
- 若缺少 Parquet 依赖，脚本会回退写入 CSV（同名 `.csv` 文件）；请在正式环境安装 `pyarrow` 或 `fastparquet`。
- 校准报告/成本配置需与业务系统对齐，避免回测与实盘口径不一致。
- 滚动训练时请保留 `output/cluster_alignment.log`，用于审核标签交换次数。
