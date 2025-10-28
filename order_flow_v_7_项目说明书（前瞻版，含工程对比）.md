# OrderFlow V7 项目说明书（前瞻版，含工程对比）

> 版本：7.1 – 稳定性统一修订版\
> 日期：2025-10-26\
> 作者：OrderFlow 研究组\
> 适用标的：BTC/USDT、ETH/USDT（主实验）\
> 依托版本：OrderFlow-V6 主分支（2025-10-18）
>
> 本文件已更新至 **V7.1 修订版**（2025-10-30），增加对噪声观测的统一描述（stability = clarity × (1 - noise_energy)）。

---

## 0. 为什么需要 V7（思维哲学 / 策略逻辑 / 思想本质）

### 0.1 V7 的世界观（哲学）

- **非稳态假设**：我们不再认为“市场状态”——即 V6 中定义的**平衡状态（市场买卖力量大致对称、价格波动围绕公允价震荡）**——是长期不变的。市场是持续演化的实体。
  用更直白的比喻：市场就像一条不断流动、形状随时在变的河流——你无法两次踏入同一条河。

- **动态市场结构稳定性原则**：动态稳定性指模型在任意滚动窗口内，能量化并维持对市场结构健康度（stability）的评估；当下的“可辨清晰”与噪声水平共同决定系统是否可安全介入。

- **元认知谦逊**：承认模型对**长期语义**的无知。这里的“长期语义”指市场状态在多年或跨周期中具体代表的经济含义（例如“趋势=机构增仓”）。

- **双层约束**：双层约束体系由“慢约束”和“快约束”组成，目的是**在市场连续漂移中保持系统稳定与反应灵敏之间的平衡**。慢约束是“河床”（宏观锚），快约束是“水流”（短期订单流）。

- **信任即风险**：在 V6 中，模型的核心输出是**状态标签**（balance 或 trend）——交易系统依据标签来选择策略模式。而在 V7.1 中，交易的核心输入是“稳定性估计（stability）”，由信息清晰度（clarity）与噪声能量（noise_energy）共同构成。

> 比喻：在 V6，我们问的是“这条河现在是左岸还是右岸”；在 V7.1，我们问的是“这条河的两岸是否还清晰可辨、够不够安全去渡河”。

---
## 0.1：策略哲学下的收益与风险解释（精简版）

### D.1 核心逻辑

V7.1 不再以预测市场为目标，而以维持并量化市场结构稳定性（stability）为核心。收益与风险均源自模型对结构健康度的感知质量。

> 只有当市场结构具有足够稳定性时，系统才具备收益可能；否则盈亏仅是系统性风险 × 风险敞口。

### D.2 收益的本质

收益源于结构清晰期的正确行动，可表示为：

\[ E[R_t] = \alpha + \beta_1 Clarity_t + \beta_2 TransitionProb_{t-1,t} + \beta_3 MacroAnchor_t + \epsilon_t \]

> 收益是结构清晰与稳定期的反应速度，而非价格预测精度。

### D.3 风险的本质

风险是结构失效或噪声占优的概率，可表示为：

\[ Risk_t = \gamma_0 + \gamma_1 PrototypeDrift_t - \gamma_2 AbstainRate_t + \eta_t \]

> 风险来自系统在失真或噪声占比上升时不自知，而非市场振幅本身。

### D.4 一行总结方程

\[ R_t = \beta_1 Clarity_t - \beta_2 Drift_t + \epsilon_t \]

当结构清晰（高 Clarity，低 Drift）且噪声能量受控时有正期望；结构模糊或噪声占优时收益坍缩为系统暴露。

> V7.1 的核心收益机制：**在市场结构稳定时赚，在结构漂移或噪声占优时停。**


## 1. 版本沿革与“生态位迁移史”（V4 → V7.1）

| 版本     | 核心假设             | 方法论                            | 研究目标       | 市场生态位  |
| ------ | ---------------- | ------------------------------ | ---------- | ------ |
| **V4** | 市场具可观测的拍卖结构      | 指标/规则树 + 基础回测                  | 证明订单流可用    | 原型验证者  |
| **V5** | 结构可标准化与验证        | 因子模块化 + Validator              | 科学化显著性与鲁棒性 | 规则工程师  |
| **V6** | 两态（平衡/失衡）可被建模并预测 | 2-state TVTP-HMM + 方向判断器 + 宏观锚 | 可预测转移并执行   | 结构建模者  |
| **V7.1** | 市场无稳态，状态仅为临时聚类   | 滚动聚类 + 自适应 TVTP + 置信度映射        | 维持市场结构稳定性与自校准  | 自适应感知者 |

> **生态位迁移**：从“捕猎信号”（V4/5），到“构建结构”（V6），到“维护可信度”（V7.1）。

---

## **2. 策略哲学与研究逻辑**

### **2.1 策略哲学**

1. **非稳态假设**：\
   市场状态的特征分布随流动性与参与者结构漂移。任何长期固定描述皆不可持续。
2. **动态市场结构稳定性原则**：\
   模型在滚动窗口上量化并维护市场结构稳定性（stability）的估计，\
   不执着语义，仅保证“当下结构是否足够稳定以供决策”。
3. **元认知谦逊**：\
   模型持续承认自身的“未知”，\
   当置信度或稳定性衰减即自动降低参与度——\
   交易信号不是预测，而是**对信任程度的表达**。
4. **双层约束结构**：
   - **慢约束（河床）**：宏观流动性、波动率、趋势周期（MA200、Vol Regime）。
   - **快约束（水流）**：滚动窗口内的订单流动态聚类（A/B 二元分类）。
5. **风险-置信映射**：\
   置信度/稳定性 → 仓位；\
   模糊度/噪声上升 → 降仓或观望；\
   漂移 → 重新学习。

---

### **2.2 策略逻辑（V6 → V7.1 演化）**

| 层次V6 逻辑V7.1 逻辑 |                                  |                                                  |
| ------------ | -------------------------------- | ------------------------------------------------ |
| **观测层**      | 采样 ATAS 订单流 + Binance OHLCV 双轨合并 | 保留双轨并加入窗口聚类标签与漂移度量                               |
| **特征层**      | AMT 因子（POC/VAL/VAH/CVD） + 宏观锚    | 同上 + 动态聚类生成的 A/B 标签与置信区                          |
| **模型层**      | 2-state TVTP HMM 预测状态转移          | 动态聚类（online GMM） → A/B 标签序列 → Adaptive TVTP 预测切换 |
| **方向层**      | 独立方向判断器长期运行                      | 仅在切换事件触发时启用 （低频高信噪）                              |
| **决策层**      | 状态=交易模式                          | 市场结构稳定性（stability）=风险许可度，方向=触发信号                                |
| **执行层**      | 信号→仓位                            | 置信度→仓位 ； 漂移→停手                                   |
| **验证层**      | 收益/显著性                           | 稳定性/漂移健康/校准度                                  |

---

### **2.3 信号与噪声的统一框架**

为了在最小工程路径上兼容现有 V7 架构，V7.1 将噪声观测纳入同一评估管线（不新增模型分支、不改变决策流程），并在验证/发布层级引入对噪声的门控。

核心思想：把“信息（clarity）”与“噪声（noise_energy 等）”统一为单一的稳定性度量：

stability = clarity × (1 - noise_energy)

其中：
- clarity 衡量信息域的可辨识度（正向指标）；
- noise_energy（以及 drift_bandwidth、clarity_spectrum_power、adversarial_gap）衡量边界与扰动（负向指标）。

模型与工程要点：
- 模型层输出扩展为四类观测：clarity、drift、noise_energy、stability_index（stability_index 可由上式或校准表得到）；前两者为正向，后两者为负向（越大表示越不利）；统一入模的组件称为 Stability Estimator。
- 特征层在现有 pipeline 中并行计算 noise_features/（仅用于评估与监控，不直接作为交易决策因子）。这四个指标在 Validation 阶段汇总用于发布门控。
- 验证层新增 validation/noise_metrics.yaml：监控 noise_energy、drift_bandwidth、clarity_recovery_rate，监测结果汇入 VALIDATION.md；发布门控从“clarity>τ₁”扩展为“stability_index>τ₁ 且 noise_energy<τ₂”。
- 工程上只增量添加：features/noise_metrics/ 下的四个计算脚本（compute_noise_energy.py 等）与 validation/noise_metrics.yaml；不引入新模型权重或在线推理分支。

新增 SCHEMA 举例（v7.1）与最小路径文件：

SCHEMA_model.json (v7.1)

{
  "clarity": 0.78,
  "drift": 0.12,
  "noise_energy": 0.19,
  "stability_index": 0.63,
  "signatures": {
    "schema_version": "v7.1",
    "build_id": "...",
    "data_manifest_hash": "...",
    "calibration_hash": "..."
  }
}


SCHEMA_validation.json

{
  "metrics": {
    "clarity": 0.78,
    "drift": 0.12,
    "noise_energy": 0.19,
    "abstain_rate": 0.17,
    "stability_index": 0.63
  },
  "gate_rules": {
    "stability_index": "> 0.6",
    "noise_energy": "< 0.3"
  }
}

最小新增文件路径（工程注释）

features/
  └── noise_metrics/
       ├── compute_noise_energy.py
       ├── compute_drift_bandwidth.py
       ├── compute_clarity_spectrum.py
       └── compute_adversarial_gap.py

validation/
  └── noise_metrics.yaml

对照总结：
- 数据/特征：+4 指标（噪声观测），在现有聚类窗口中计算，不引入新数据源。
- 模型/决策：无新增分支，保持 V7 架构闭环。
- 验证/发布：门控条件扩展，新增 noise_energy 检查，防止结构过度模糊仍放权。
- 文档/语义："可分性" → "稳定性"，概念升级为对称框架。

✅ 修订哲学一句话

V7.1 = V7 + 会聆听噪声的耳朵。
系统仍然追求清晰，但懂得模糊的轮廓也是结构的一部分。

---

## **3. 架构总览（与 V6 保持同构）**

```
/
├── governance/
├── data/
├── features/
├── model/
│   ├── clusterer_dynamic/        ← 新增
│   └── hmm_tvtp_adaptive/        ← 改造
├── decision/
│   ├── rules/                    ← 更新
│   └── engine/
├── execution/
├── validation/
└── output/

```

---

## **4. 治理层（governance）**

- **SCHEMA_model.json (v7.1)**\
  新增字段：`noise_energy`、`stability_index`（由 clarity 与 noise_energy 组合或单独校准得到）、`clusterer_config`、`label_map`、`prototype_drift`、`drift_health`。\
  作用：记录聚类窗口配置、噪声估计与标签对齐状态。
- **SCHEMA_decision.json (v7.1)**\
  新增字段：`clarity`（结构清晰度）、`abstain`、`reason`、`stability_index`。
- **RULES_library.yaml (v7)**\
  增加规则触发类型：`on: transition(A->B, prob>τ)`、`on: low_confidence`。
- **CONTROL_switch_policy.yaml (v7.1)**\
  引入 `drift_metrics`、`noise_metrics` 与 `abstain_rate` 门控，用于发布审计。

---

## **5. 数据与特征层（data/, features/）**

**继承 V6 AB 双轨**（ATAS 短期高频 + Binance 长历史低频），并引入：

- `cluster_artifacts.json`：保存每个窗口的聚类结果、原型向量、漂移指标；
- `macro_factor_slowanchor.parquet`：记录宏观锚定变量；
- 在预处理阶段插入 `rolling_cluster_labeler` 节点；
- 在同一 pipeline 中并行计算 `features/noise_metrics/` 的四项噪声观测（仅用于验证与监控）。

**修改原因**：支持“滚动再编码”与语义漂移及噪声监控。

---

## **6. 模型层（model/）**

### **6.1 新增：clusterer_dynamic/**

- **算法**：在线 GMM / Online-EM （K=2，带遗忘因子 λ ≈ 0.97）。
- **输出**：A/B 标签、原型向量、标签映射、漂移统计。
- **设计理由**：解决 V6 中发射分布长期固定导致的语义老化。

### **6.2 改造：hmm_tvtp_adaptive/**

- **输入**：聚类标签序列 + 宏观慢变量 + Stability Estimator 输出。
- **目标**：学习“切换概率”而非“状态定义”；保留时序记忆。
- **特性**：
  - 滚动再训练（窗口滑动）；
  - label-switch 对齐；
  - 漂移触发软重置。

### **6.3 方向判断器（direction_classifier）**

- 启动条件：`P(A->B) > τ_tr`。
- 特征：MFI、CVD、聪明钱 proxy、价量趋势。
- 输出：方向 {bull,bear,none} + 置信度。

---

## **7. 决策层（decision/）**

### **7.1 决策哲学**

- **信号即信任**：模型不是预测价格，而是输出“我有多确定”。
- **交易是置信度管理**：置信高 → 放权；置信低 → 缩手。

### **7.2 简化逻辑**

1. **门控阶段**：\
   漂移 warn/fail 或 stability_index 低 → 停止； 置信度 < 阈 → 观望。
2. **触发阶段**：\
   当 `transition_prob > 0.75` 且方向置信 > 0.7 → 发出 long/short。
3. **仓位阶段**：\
   仓位 ≈ clarity¹·⁵ × macro_anchor cap；\
   clarity 由 state_posterior 与 boundary_distance 联合计算。
4. **退出阶段**：\
   状态模糊或 stability_index 下降 → 减仓； 方向翻转 → 平仓。
5. **拒绝机制**：\
   任何阶段 abstain 都计入 `abstain_rate` 并在 validation 记录。

### **7.3 修改原因**

- 减少模型与决策间的语义错位；
- 以置信度与稳定性为风险杠杆，更好适应非稳态市场；
- 发布门控扩展为：stability_index>τ₁，clarity>τ₂，noise_energy<τ₃。

---

## **8. 执行层（execution/）**

- 支持动作：`open_long`, `open_short`, `reduce`, `close_all`, `abstain`。
- 冷却控制：触发后 900 秒内不反向开仓。
- 资金分配：按 clarity 与 stability_index 映射风险预算，结合 ATR 做止盈止损。
- 日志：记录 clarity、stability_index、slow_anchor、abstain 原因，供 Validator 复盘。

---

## **9. 验证与发布（validation/, output/）**

| 类别指标说明 |                                               |               |
| ------ | --------------------------------------------- | ------------- |
| 漂移监控   | `prototype_drift`, `PSI/KS`                   | 聚类语义变化率       |
| 校准性    | `ECE`, `Brier`                                | 模型可信度与真实切换一致性 |
| 触发健康   | `transition_hit_ratio`, `direction_flip_rate` | 事件有效性         |
| 风控效率   | `abstain_rate`, `reduce_events`               | 风险响应          |
| 结果度量   | `PnL_per_risk`, `drawdown`                    | 收益仅作观察        |

**发布门控条件（V7.1 建议）**：

- stability_index > 阈； clarity > 阈； noise_energy < 阈； 校准与拒绝率满足历史要求。
- 通过后生成 manifest 签名并部署。

---

## **10. 风险与迁移策略**

### **10.1 迁移步骤**

1. 建立 V6.5 实验分支：加入动态聚类、拒绝机制与 noise_metrics 观测。
2. 回放两周 + paper trading 一周，并监控 noise_metrics 与 stability_index 行为。
3. 校准阈值后合并为 V7.1 主线，冻结 V6。

### **10.2 潜在风险**

| 风险防御    |                 |
| ------- | --------------- |
| 短窗污染    | 慢锚限制 + AB 轨热切换  |
| 标签漂移    | 原型对齐 + 门控发布     |
| 工程复杂度膨胀 | 模块独立、冻结旧逻辑      |
| 数据不连续   | 通过 Binance 轨补历史 |

---

## **11. V6 → V7.1 关键机制对照**

| 模块V6V7.1变更目的 |                          |                          |            |
| ---------- | ------------------------ | ------------------------ | ---------- |
| 状态建模       | 固定语义 (balance/trend) HMM | 滚动聚类 A/B + Adaptive TVTP | 消除稳态假设     |
| 转移学习       | TVTP 预测切换                | 同上，但驱动变量扩展为宏观+漂移+stability_estimator         | 增强适应性      |
| 方向判断       | 持续运行                     | 仅在切换触发时启用                | 降噪降滞后      |
| 风控逻辑       | 状态置信 → 交易模式              | clarity & stability_index → 仓位权重           | 以可信度替代方向置信 |
| 宏观约束       | 参考指标                     | 河床锚（slow anchor）         | 双层约束成型     |
| 验证标准       | 显著性与收益                   | 漂移、校准、稳定性                | 从预测到可解释稳定  |

---

## **12. 结论与前瞻**

V7.1 是 OrderFlow 体系的**稳态语义升级版**：

- 从“解释市场”到“感知市场”；
- 从“预测结果”到“维持可信度与稳定性”；
- 从“模型自信”到“模型自律”。

它让系统在结构漂移与噪声上升的世界中仍能自校准，\
让策略不再依赖固定语义，而依赖动态信任与噪声感知。

> **V7.1 的目标不是赢得所有行情，**\
> **而是永远知道自己何时不该出手。**

### **下一步（V7.1 → V8 蓝图）**

- 加入 Meta-Learning 层自动调整窗口长度与阈值；
- 引入多资产横向共振（跨品种状态一致性检验）；
- 探索自适应学习率与动态遗忘机制，使系统具备“自愈”能力；
- 将 Stability Estimator 从观测提升为可选择的在线校准模块（视工程容量）。

---

## 附录 C：Clusterer Dynamic 输入与门控参数（对齐 ATAS 导出字段）

> 本附录以你提供的 `bar_YYYYMMDD.jsonl`（schema_version=v6.3，exporter_version=6.3.0.0）为准，对 **Clusterer Dynamic** 的输入字段、特征工程与配置进行明确约定，便于工程对接。

### C.1 ATAS 导出字段总表（按样例）
(内容与原稿相同，略)

### C.2 聚类输入特征（从 ATAS 字段映射）
(内容与原稿相同，略)

### C.3 滚动窗口、滑动与遗忘
(内容与原稿相同，略)

### C.4 发布门控阈值（建议）
(内容与原稿相同，略)

### C.5 `clusterer_dynamic/config.yaml` 示例
(内容与原稿相同，略)

### C.6 噪声观测（新增字段定义）

- `noise_energy`：在 clarity < τ 区间中，clarity 序列或相关残差的方差能量（衡量噪声占比）；
- `drift_bandwidth`：原型漂移的标准差或带宽度量（衡量漂移范围）；
- `adversarial_gap`：对抗扰动（或合成扰动）与原数据嵌入之间的差距度量（衡量模型对扰动敏感性）；
- `clarity_spectrum_power`：clarity 序列的功率谱在关键频段上的平均功率（衡量短期周期噪声能量）。

---

(文末保留原稿的配置与附录细节以便工程复制。)