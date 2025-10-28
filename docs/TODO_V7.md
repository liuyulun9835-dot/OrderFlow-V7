"""markdown
# TODO_V7.1 — Stability Unified Task Board

> 最小执行链：`make data.qc → make cluster.fit → make tvtp.fit → make validate → make dryrun → make release`  
> 口径：V7.1 在 V7 基础上引入“噪声观测四指标 + stability_index”，仅作为评估/门控/仓位修正项，不新增模型分支。

> 说明：本文件在保留原有 TODO 条目与流程的基础上，追加与 V7.1（稳定性统一修订版）直接相关的任务与验收要求。与原 TODO 中不相关的条目保持原样（若本文件与仓库中原始 TODO 存在差异，请以此文件为 V7.1 的任务板主版本并在 PR 描述中标注变更点）。

## Milestones
- **M0 最小闭环（7.1）**：数据 → 聚类 → TVTP → 验证 → 干跑 → 发布门检通过（含 stability/noise）
- **M1 校准与门控达标**：ECE / Brier / abstain / prototype_drift / noise_energy / stability_index 全量进入 CI，并达成初始阈值覆盖
- **M2 成本与执行**：clarity × stability 仓位修正曲线固化；成本鲁棒性场景化门检（base / +50% / ×2）

## Workflows

### [GOV] 治理与契约（从 v7.0 → v7.1）
- [ ] GOV-01 `SCHEMA_model.json` 升级至 v7.1，新增字段：
      `noise_energy: float`, `stability_index: float`
  - OUT: governance/SCHEMA_model.json
  - ACCEPTANCE: `signatures.schema_version == "v7.1"` 且 jsonschema 校验通过

- [ ] GOV-02 `SCHEMA_decision.json` 增补：
      新增 `stability_index`, `reason` 字段，保留并校验 `clarity` / `abstain`
  - OUT: governance/SCHEMA_decision.json
  - ACCEPTANCE: jsonschema 校验通过，示例 manifest 能写入并读取

- [ ] GOV-03 `RULES_library.yaml` 增加触发与动作：
      新增触发 `on: high_noise`，默认动作建议 `reduce` / `abstain` / `escalate_to_risk`
  - OUT: governance/RULES_library.yaml
  - ACCEPTANCE: 新触发在规则解析器中可识别并在模拟事件中触发正确动作（单元测试）

- [ ] GOV-04 `CONTROL_switch_policy.yaml` 纳入新门控源：
      引用 `validation/noise_metrics.yaml` 中 thresholds，加入 `stability_index` / `noise_energy` 阈值与连续 K 窗口回滚规则
  - OUT: governance/CONTROL_switch_policy.yaml
  - ACCEPTANCE: policy parser 能读取并在连续 K=3 窗口违例时输出回滚指令（模拟测试）

### [FEAT] 特征 / 观测（新增噪声观测四指标）
- [ ] FEAT-01 负清晰度样本采样与 `noise_energy` 计算逻辑（clarity < τ 的方差能量）
  - OUT: features/noise_metrics/compute_noise_energy.py
  - ACCEPTANCE: 脚本提供函数 compute_noise_energy(clarity_series, low_threshold) 并通过简单单元样例

- [ ] FEAT-02 `drift_bandwidth`（原型向量一阶差分范数的标准差）
  - OUT: features/noise_metrics/compute_drift_bandwidth.py
  - ACCEPTANCE: 提供 compute_drift_bandwidth(proto_vectors) 并对示例 proto 序列给出合理数值

- [ ] FEAT-03 `clarity_spectrum_power`（clarity 序列高频功率）
  - OUT: features/noise_metrics/compute_clarity_spectrum.py
  - ACCEPTANCE: 提供 compute_clarity_spectrum_power(clarity_series, hi_band)；若环境含 scipy 使用 Welch，否则回退 FFT

- [ ] FEAT-04 `adversarial_gap`（扰动 vs 原数据嵌入差，MSE 或马氏距离）
  - OUT: features/noise_metrics/compute_adversarial_gap.py
  - ACCEPTANCE: 提供 compute_adversarial_gap(embed_real, embed_noisy) 并支持 (N,D) 或 (D,) 输入

- [ ] FEAT-05 `stability_index` 计算：`clarity × (1 - noise_energy)`（可留校准表）
  - OUT: model/stability_estimator.py 或合并到现有评估模块
  - ACCEPTANCE: 提供稳定性计算例程并在 SCHEMA 示例中有输出字段 stability_index

### [VAL] 验证与门控（新增 7.1 门检）
- [ ] VAL-01 新增 YAML：`validation/noise_metrics.yaml`，含阈值与 gates：
  ```yaml
  thresholds:
    stability_index: 0.60
    noise_energy: 0.30
    drift_bandwidth: auto    # 初始策略：历史 median + 1σ
    clarity_spectrum_power: auto
  gates:
    - "stability_index > thresholds.stability_index"
    - "noise_energy < thresholds.noise_energy"
  reporting:
    markdown: docs/VALIDATION.md
    lookback_days: 14
  ```
  - OUT: validation/noise_metrics.yaml
  - ACCEPTANCE: 文件存在且被 audit 脚本识别并用于门检

- [ ] VAL-02 `VALIDATION.md` 汇总表新增列：
      `noise_energy`, `drift_bandwidth`, `clarity_spectrum_power`, `stability_index`
  - OUT: docs/VALIDATION.md
  - ACCEPTANCE: docs/VALIDATION.md 前 30 行含占位表头及示例行

- [ ] VAL-03 CI 门检对接（失败显示具体指标名与阈值）
  - OUT: .github/workflows/ci.yml, validation/gates.py
  - ACCEPTANCE: CI 运行时可调用 gates.py 并在校验失败时输出 human-readable 报告

### [MODEL] 训练与校准（不改分支，仅评估/修正）
- [ ] MODEL-01 Stability Estimator：将 `stability_index` 作为仓位修正项（不改变触发逻辑，仅影响权重）
  - OUT: decision/engine.py（映射曲线或 lookup 校准表）
  - ACCEPTANCE: dryrun 输出包含 base_position 与 stability_modifier 并能复现预期缩放

- [ ] MODEL-02 校准（ECE / Brier）与 `stability_index` 联动审计
  - OUT: validation/calibration_report.md
  - ACCEPTANCE: 校准报告中列出 ECE/Brier 与 stability_index 的相关性与门检建议

### [EXEC] 执行与成本
- [ ] EXEC-01 仓位 = `position_base(clarity)` × `stability_modifier`（单调递增）
  - OUT: decision/engine.py, governance/CONTROL_switch_policy.yaml
  - ACCEPTANCE: 回测/模拟任务显示仓位随 stability_index 的合理变化曲线

- [ ] EXEC-02 高噪声期强制冷却/降仓策略与日志
  - OUT: execution/* （策略实现）、output/audits/*.md（审计记录）
  - ACCEPTANCE: 高噪声事件写入审计日志（时间戳、阈值、触发原因、处理动作）

### [DOC] 文档与变更记录
- [ ] DOC-01 README 的“最小执行链”与指向更新为 7.1
  - OUT: README.md
- [ ] DOC-02 CHANGELOG 增补 7.1 项
  - OUT: docs/CHANGELOG.md
- [ ] DOC-03 本 TODO 文件抬头标注“V7.1 — Stability Unified”，并附来源（说明书章节锚点）
  - OUT: docs/TODO_V7.md（本文件）

## 验收标准（一页式）
- 有文件：`features/noise_metrics/*`、`validation/noise_metrics.yaml`
- 有字段：`governance/SCHEMA_model.json` 中 `signatures.schema_version == "v7.1"`, 并包含 `noise_energy`, `stability_index`
- 有门检：`docs/VALIDATION.md` 含四指标列；validation 脚本能解释 gates 并能与 CI 联动
- 有日志：输出 `output/audits/v7_1_audit.md` 的体检报告（若无历史数据，用样例跑通）
- 有 PR：覆盖上述改动的分支名与 commit message 符合规范（见下）

## 提交与分支策略（本任务板执行约定）
- 分支：`feat/v7_1-stability-todo-sync`
- commit 示例：`chore(todo): sync TODO to V7.1 stability framework and noise gates`
- PR 标题示例：`chore(v7.1): sync TODO and add stability gating tasks`
- PR 描述应包含：
  - 变更清单（文件级别）与验收脚本输出（或 link 到 output/audits/v7_1_audit.md）
  - 变更的治理影响点（schema 升级、CI gates 增补）

## 附：可执行任务板（按优先级）
P0（必须先完成）
- GOV-01, GOV-04, FEAT-01, FEAT-02, VAL-01, DOC-02

P1（次序并行）
- FEAT-03, FEAT-04, FEAT-05, MODEL-01, VAL-02, EXEC-02

P2（后续）
- MODEL-02, VAL-03 (CI 集成), DOC-01, TODO 的测试覆盖

## 附录：快速检查清单（验收时逐项打勾）
- [ ] 分支已创建：`feat/v7_1-stability-todo-sync`
- [ ] features/noise_metrics/* 四个脚本存在并含 self-test
- [ ] validation/noise_metrics.yaml 存在且格式可读
- [ ] governance/SCHEMA_model.json 包含 `schema_version==v7.1` 且包含 `noise_energy, stability_index`
- [ ] docs/VALIDATION.md 包含四指标列头与占位示例
- [ ] scripts/audit_v7_1.py 可运行并输出 output/audits/v7_1_audit.md
- [ ] PR 已创建并附带审计报告（或运行日志）

---
Commit for this TODO update:
- branch: `feat/v7_1-stability-todo-sync`
- commit message: `chore(todo): sync TODO to V7.1 stability framework and noise gates`
"""