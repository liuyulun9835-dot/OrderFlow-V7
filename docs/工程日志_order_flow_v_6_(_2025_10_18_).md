# **工程日志 — OrderFlow V6（2025-10-18）**

> 日期：2025‑10‑18\
> 基准文档：`OrderFlow‑V6项目说明书_修订_2.md` / `README.md` / `order_flow_v_6_todo.md`\
> 评估口径：不仅看“文件是否存在”，更关注**功能可用性、与上游/下游的耦合程度、可测试性与产物可追溯性**。

---

## 0. 结论快照（TL;DR）

- **总体功能完工度（加权）**：**58%**
- **核心短板**：`data/` 基座与 `features/microflow/` 未完，使得模型/验证只能处于**占位或半功能**状态。
- **优先顺序建议**：
  1. **先补 Data & Microflow 基建（最高优先级）**；
  2. 完成 TVTP‑HMM 真训练与制品落地（而非占位）；
  3. 训练化 `directional_classifier` + 概率校准，并接入规则/执行日志；
  4. 将 Validator 报告产出流水化，接入发布门禁（CI）。

---

## 1. 分层功能性评估（按修订 2.0 架构）

> 评分刻度：0 未启动 / 1 占位（能 import，不能用）/ 2 半功能（toy 可跑）/ 3 可用（端到端可跑，缺监控）/ 4 稳定可发布（含测试、指标、回滚）。

### 1.1 治理层（governance/\*）— **等级：3/4（完成度 75%）**

- **现状**：`SCHEMA_model.json`、`SCHEMA_decision.json`、`RULES_library.yaml` 已补齐关键字段与 `transition(...)` 触发。
- **缺口**：
  - Schema 校验脚本/CI gate **尚未实际绑定**到 PR（需要 actions 或 make 任务中添加 schema 校验步骤）。
  - `CONTROL_switch_policy.yaml` 在 release 校验条款里需强制检查近 7/30 天 `switch_audit`。
- **建议**：
  - 增加 `tools/validate_schema.py` + GH Actions 步骤；
  - 在 `output/report/release.yml` 中新增 **硬门禁**：缺 `VALIDATION.md` 的方向分层摘要 → 直接 fail。

### 1.2 数据层（data/\*）— **等级：0/4（完成度 0%）**

- **现状**：未见 `data/ingestion/` 与 `data/manifests/`；无水位与哈希清单。
- **风险**：所有下游（微观特征、TVTP 驱动、验证）均无法形成**可追溯**的训练/评估集。
- **建议（必做）**：
  - 建 `ingestion/`：`binance_ohlcv.py`（2017‑now, 1m）与 `atas_tick_to_1m.py`（近窗聚合）；
  - 建 `manifests/`：`manifest.jsonl` 写入 {source, sym, start, end, rows, file\_hash}；
  - 建 `watermark/`：记录最晚可用时间戳与拉取策略。

### 1.3 特征层（features/\*）— **等级：1.5/4（完成度 38%）**

- **现状**：
  - `features/macro_factor/macro_factor.py` 已有（MA200\_ratio 占位）；
  - `features/microflow/` 未落地（MFI/CVD/Imbalance 等缺实现与单测）。
- **建议（必做）**：
  - 建指标库：`mfi.py`、`cvd.py`、`imbalance.py`、`vpin.py(可后置)`；
  - 统一特征签名（列名/频率/对齐规则），产出 `featureset.parquet`；
  - 单测：对齐边界条件（缺失/跳时/零成交）。

### 1.4 模型层（model/hmm\_tvtp\_hsmm/\*）— **等级：1.5/4（完成度 38%）**

- **现状**：
  - `train_tvtp.py` 与 `state_inference.py` 存在，但**训练为占位逻辑**，`state_inference` 依赖手工 `score`；
  - 未见 `artifacts/` 持久化产物（四键签名、驱动列表、AIC/BIC 等）。
- **技术缺口**：
  - **TVTP 训练算法**（EM with logistic transitions）未实现；
  - **前向‑后向**推断需支持**时变转移矩阵**；
  - 多起点稳健化与交叉验证缺失。
- **建议（必做）**：
  - 先以**简化版**实现：
    1. 观测为高斯 / t 分布（任选），
    2. 转移 `P(S_t|S_{t-1}, X_t)` 用 **Logit(β·X)**；
    3. EM：E 步（FB with TVTP）、M 步（β 用 IRLS/牛顿法）
  - 产出 `artifacts/model_artifact.json`：states/tvtp/drivers/macro\_factor\_used/四键签名/AIC/BIC/多起点散点。

### 1.5 决策层（decision/\*）— **等级：2/4（完成度 50%）**

- **现状**：
  - `directional_classifier.py` 有占位打分；
  - `rules/transition_examples.yaml` 在位；
  - 与推断输出/执行日志的**耦合未打通**。
- **建议**：
  - 将 `predict_proba()` 与 `infer()` 合流为 `decision/engine/bridge.py`，落日志：`trigger`、`classifier_confidence`、输入快照；
  - 方向分类器用**可训练模型**（LogReg/XGB）+ **概率校准**（Isotonic/Platt），并做样本外 ROC/AUC。

### 1.6 执行层（execution/\*）— **等级：2.5/4（完成度 63%）**

- **现状**：`switch_policy.yaml` 在位；实盘路由未触及（合理）。
- **建议**：
  - 增加**观测面板**：方向误判率、翻转率、滞后分布；
  - 灰度策略：基于 `switch_policy` 的 canary 配额与回滚脚本。

### 1.7 验证层（validation/\*）— **等级：2/4（完成度 50%）**

- **现状**：`directional_breakdown()` 为占位；`validator_v2.yaml` 存在。
- **建议**：
  - 单变量：事件触发 → 方向分层收益/稳定性 → FDR 控制；
  - 多变量：Logit/Probit with TVTP 状态作为协变量 → 稳健 SE；
  - 成本鲁棒：滑点/费率网格与显著性热图；
  - 自动写入 `output/publish_docs/VALIDATION.md`。

### 1.8 输出/文档层（output/\*, README/todo）— **等级：3/4（完成度 75%）**

- **现状**：README/todo 对齐；报告模板在位；
- **建议**：将审计与验证产出由脚本**自动注入**文档，减少手工同步。

---

## 2. 与工程卡片的对照（关键卡片）

| 卡片                      | 期望                                | 现状评估          | 说明/动作                               |
| ----------------------- | --------------------------------- | ------------- | ----------------------------------- |
| **207 宏观慢变量**           | 构建 MA200 等慢变量，入 TVTP 驱动           | **进行中**（占位函数） | 需纳入流水线并做前视泄露检查                      |
| **303 TVTP‑HMM（含宏观驱动）** | TVTP 训练、显著性与样本外对比                 | **未完成**       | 实现 EM + FB(TVTP) + 多起点；落地 artifacts |
| **305 状态推断接口**          | `predict_proba → state, P(Si→Sj)` | **占位**        | 改为加载真实制品；提供批量/流式接口                  |
| **607 AB 热切换**          | PSI/KS/ECE 门控 + 发布绑定              | **规则在位**      | 增加 switch 审计与回放脚本                   |
| **607‑B 方向性判断器**        | 训练化分类器 + 置信校准                     | **占位**        | 采样/特征集/校准/阈值学习；对接日志                 |
| **401 单变量 / 406 汇总**    | 方向分层 + 宏观对比                       | **占位**        | 指标化产出 + FDR；写入 VALIDATION.md        |
| **865 RULES/SCHEMA 扩展** | 触发/字段齐备 + CI 校验                   | **部分完成**      | 加 CI gate + schema 校验脚本             |

---

## 3. 后续 2–4 周落地计划（优先级从高到低）

### P0（基础代价最低、拉动最大）

1. **Data 基建**（3–5 天）
   - `data/ingestion/binance_ohlcv.py`、`data/ingestion/atas_tick_to_1m.py`；
   - `data/manifests/manifest.jsonl` 与 `watermark/`；
   - 单测 + 小规模样本回归。
2. **Microflow 库**（3–4 天）
   - `mfi.py`、`cvd.py`、`imbalance.py`，统一签名与对齐规则；
   - 产出 `featureset.parquet`。

### P1（模型可用化）

3. **TVTP‑HMM 训练（简化版）**（5–7 天）
   - EM(FB with TVTP) + drivers=[MFI,CVD,MA200\_ratio]；
   - 多起点 + 样本外稳定性；
   - `artifacts/model_artifact.json` 落地。
4. **Directional 训练化 + 校准**（3–4 天）
   - LogReg/XGB + Isotonic/Platt；
   - 指标：AUC、精确‑召回、翻转率。

### P2（验证/门禁/执行观测）

5. **Validator 流水化**（3 天）
   - 单变量/多变量输出方向分层 + 宏观对比 → 写入 `VALIDATION.md`；
6. **CI 门禁与执行观测**（2 天）
   - schema 校验 + audit 通过才允 PR；
   - 方向误判率面板与 `switch_audit` 检查。

---

## 4. 风险与缓解

- **数据漂移**：加入 PSI/KS/ECE 日志与门控，启用 `switch_policy` 回滚；
- **过拟合**：TVTP 驱动做降维/正则；多起点 + 时间切片交叉验证；
- **执行一致性**：统一特征/模型签名与版本；打包四键签名并在决策日志中存证。

---

## 5. 关于 `tools/` 的定位

- **长期保留**：这是**治理审计工具链**，应保留为根目录一等公民；
- **不并入 governance/**：治理层放“契约”，`tools/` 放“执行脚本”，分层职责明确；
- **可镜像门槛**：在 `governance/CONTROL_audit.yaml` 镜像最小通过标准，CI 调用 `tools/` 执行审计。

