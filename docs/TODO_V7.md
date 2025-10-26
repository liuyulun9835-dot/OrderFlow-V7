# TODO_V7 — Canonical Task Board

> 最小执行链：`make data.qc → make cluster.fit → make tvtp.fit → make validate → make dryrun → make release`
> 口径：V7 强调“滚动可分性(A/B) + 自适应 TVTP(只学切换) + clarity/abstain + 漂移与校准门控”；收益仅观察，不作为硬门控。

> **来源收敛**：本版本汇总自《order_flow_v_6_todo.md》《docs/OrderFlow V6 — 任务卡片库V1.1.md》以及 2025-10-15 至 2025-10-24 的《docs/工程日志_*》条目，相关原始文档已归档至 `docs/_archive/`。

## Milestones
- **M0 最小闭环**：数据→聚类→TVTP→验证→干跑→发布门检跑通
- **M1 校准&门控完整**：ECE/Brier、abstain、prototype_drift 纳入 CI；方向判断器改为“切换触发”
- **M2 执行联调与成本鲁棒**：仿真接入成本模型；clarity→仓位曲线固化；门控稳态

## Workflows
### [GOV] 治理与契约
- [ ] GOV-01 `SCHEMA_model.json` 增加 `clusterer_config/clarity/abstain/prototype_drift`  
  - TAG: modify | OWNER: core | DUE: ____  
  - ACCEPTANCE: jsonschema 校验通过；CI 阶段读取阈值不报错  
  - OUT: governance/SCHEMA_model.json
- [ ] GOV-02 `SCHEMA_decision.json` 增加 `clarity/abstain/reason`  
  - TAG: modify | OWNER: core | DUE: ____  
  - ACCEPTANCE: schema 校验通过；决策接口验收样例覆盖三态  
  - OUT: governance/SCHEMA_decision.json
- [ ] GOV-03 `RULES_library.yaml` 新增 `transition(A->B, prob>τ)` 与 `low_confidence`  
  - TAG: modify | OWNER: quant | DUE: ____  
  - ACCEPTANCE: 规则编号齐全；CI 门检比对策略映射成功  
  - OUT: governance/RULES_library.yaml
- [ ] GOV-04 `CONTROL_switch_policy.yaml` 纳入 `drift_metrics/ECE/Brier/abstain_rate` 阈值  
  - TAG: modify | OWNER: risk | DUE: ____  
  - ACCEPTANCE: 门控配置与验证脚本联动；阈值缺失时报错  
  - OUT: governance/CONTROL_switch_policy.yaml

### [DATA] 数据接入/对齐/校准
- [ ] DATA-01 保持 AB 双源与校准脚本；输出对齐报告  
  - TAG: inherit | OWNER: data | DUE: ____  
  - ACCEPTANCE: `make data.qc` 生成报告且无 ERROR  
  - OUT: output/calibration_report.md
- [ ] DATA-02 ATAS/交易所分钟数据 schema 迭代至 V7，补 manifest 签名  
  - TAG: modify | OWNER: data | DUE: ____  
  - ACCEPTANCE: manifest 含 `schema_version=v7` 与导出批次元数据；QC 缺失率≤0.1%  
  - OUT: data/raw/**, docs/DATA_PIPELINE.md
- [ ] DATA-03 成本字典三档更新并联通仿真  
  - TAG: inherit | OWNER: data | DUE: ____  
  - ACCEPTANCE: 成本配置落入 `output/cost_profiles.json`，仿真读取成功  
  - OUT: output/cost_profiles.json

### [FEAT] 特征（微观/宏观）
- [ ] FEAT-01 微观特征口径统一（含 `bar_vpo_*`、cvd、volprofile）  
  - TAG: modify | OWNER: feat | DUE: ____  
  - ACCEPTANCE: `clusterer_config.features` 可复现实验列名；qc 报告无缺列  
  - OUT: model/clusterer_dynamic/clusterer_config.yaml
- [ ] FEAT-02 宏观慢因子沿用并声明为约束  
  - TAG: inherit | OWNER: feat | DUE: ____  
  - ACCEPTANCE: 因子列表与 `model/hmm_tvtp_adaptive/README.md` 对齐；滑窗再训脚本引用一致  
  - OUT: model/hmm_tvtp_adaptive/config.yaml

### [CLST] clusterer_dynamic
- [ ] CLST-01 在线聚类（GMM 或 IncPCA+kmeans；K=2；λ≈0.97）  
  - TAG: new | OWNER: ml | DUE: ____  
  - ACCEPTANCE: 产出 `labels_wt.parquet` 与 `cluster_artifacts.json`  
  - OUT: model/clusterer_dynamic/
- [ ] CLST-02 滚动窗口与标签对齐（Hungarian；label-switch 审计）  
  - TAG: new | OWNER: ml | DUE: ____  
  - ACCEPTANCE: 审计日志包含交换次数与一致性评分  
  - OUT: output/cluster_alignment.log
- [ ] CLST-03 `prototype_drift` 指标产出并接门控  
  - TAG: new | OWNER: ml | DUE: ____  
  - ACCEPTANCE: `validation/metrics_summary.json` 含 drift 指标；CONTROL 阈值读写正常  
  - OUT: validation/metrics_summary.json

### [TVTP] hmm_tvtp_adaptive
- [ ] TVTP-01 用 A/B 标签 + 宏观因子训练，仅学习切换概率  
  - TAG: modify | OWNER: ml | DUE: ____  
  - ACCEPTANCE: `transition_prob.parquet` 产出且校准可运行  
  - OUT: model/hmm_tvtp_adaptive/transition_prob.parquet
- [ ] TVTP-02 校准指标（ECE/Brier）  
  - TAG: new | OWNER: ml | DUE: ____  
  - ACCEPTANCE: 指标小于 CONTROL 阈值  
  - OUT: validation/metrics_summary.json
- [ ] TVTP-03 推断输出 `transition_prob/clarity/abstain`  
  - TAG: modify | OWNER: ml | DUE: ____  
  - ACCEPTANCE: 推断接口返回三字段；低置信度触发 abstain  
  - OUT: model/hmm_tvtp_adaptive/state_inference.py

### [DEC] 决策与执行
- [ ] DEC-01 仅在 `transition_prob>τ` 时触发方向判断器；低置信度走 `abstain`  
  - TAG: modify | OWNER: exec | DUE: ____  
  - ACCEPTANCE: `dryrun` 日志显示触发逻辑  
  - OUT: decision/engine.py
- [ ] DEC-02 `clarity → position_size` 映射  
  - TAG: new | OWNER: exec | DUE: ____  
  - ACCEPTANCE: 映射曲线写入配置并被执行层引用  
  - OUT: decision/engine.py, governance/CONTROL_switch_policy.yaml

### [VAL] 验证与门控
- [ ] VAL-01 新增 `prototype_drift/ECE/Brier/abstain_rate/transition_hit_ratio`  
  - TAG: new | OWNER: qa | DUE: ____  
  - ACCEPTANCE: `VALIDATION.md` 汇总表含以上列  
  - OUT: validation/VALIDATION.md
- [ ] VAL-02 发布门检以“健康指标”为主  
  - TAG: modify | OWNER: qa | DUE: ____  
  - ACCEPTANCE: `make release` 读取 CONTROL 阈值并判定  
  - OUT: validation/gates.py

### [CI] CI/发布
- [ ] CI-01 CI 增加 schema 校验与指标门控  
  - TAG: modify | OWNER: ops | DUE: ____  
  - ACCEPTANCE: Actions 全绿；失败时输出具体指标名  
  - OUT: .github/workflows/ci.yml
- [ ] CI-02 四键签名流程沿用（产物哈希记录）  
  - TAG: inherit | OWNER: ops | DUE: ____  
  - ACCEPTANCE: 发布清单含哈希签名；审计追溯可重算  
  - OUT: scripts/signing/

### [DOC] 文档与迁移
- [ ] DOC-01 收敛旧 TODO/ROADMAP 到本文件；旧文档入 `docs/_archive/`  
  - TAG: modify | OWNER: docs | DUE: ____  
  - ACCEPTANCE: 顶部列出来源与归档链接  
  - OUT: docs/TODO_V7.md
- [ ] DOC-02 更新 README 的“最小执行链”段落与指向  
  - TAG: modify | OWNER: docs | DUE: ____  
  - ACCEPTANCE: README 提及 V7 链路并链接 TODO  
  - OUT: README.md

## Backlog
- [ ] 三态相关图表历史存档注记（不再投产）  
  - TAG: backlog | OWNER: docs | DUE: ____

## Parking Lot
- [ ] HSMM 方案研究（在 TVTP 稳定后再立项）  
  - TAG: parking | OWNER: research | DUE: ____
