# 迁出项

## 决策与执行层模块
迁出日期：2025-10-28

- `decision/*` → 迁往 Decision Repo（占位链接）
- `execution/*` → 迁往 Execution Repo（占位链接）

## V6 一体化遗留（Legacy OrderFlow V6）
迁出日期：2025-10-28

**说明**：ATAS 指标源码将在 ATAS-Exporter 专库维护

### orderflow_v_6/ 目录结构（供后续迁移接收）
```
orderflow_v_6/
├── cli/
│   └── scripts/
│       ├── batch_replay.bat
│       ├── batch_replay.sh
│       ├── build_exporter.ps1
│       ├── canary_switch_dryrun.py
│       ├── init_data_tree.ps1
│       ├── init_data_tree.py
│       ├── make_data_pipeline.ps1
│       └── update_pipeline.ps1
├── compat/
├── core/
│   └── seeding.py
├── integrations/
│   └── atas/
│       ├── Directory.Build.props
│       ├── data_bridge/
│       └── indicators/
│           ├── .vs/ (IDE缓存)
│           ├── ATAS_EXPORTER_README.md
│           ├── SimplifiedDataExporter.cs
│           ├── SimplifiedDataExporter.csproj
│           └── TickTapeExporter.cs
├── tests/
│   ├── test_calibration_stratified.py
│   ├── test_fetch_kline_io.py
│   ├── test_merge_offset_tolerance.py
│   ├── test_minute_boundary_right_closed.py
│   ├── test_precheck_costs_gate.py
│   └── test_validate_json_dual_schema.py
├── utils/
│   └── seed.py
└── validation/
    ├── configs/
    ├── out/
    ├── schemas/
    └── src/
```

## 《数据侧迁移到 CDK》
迁出日期：2025-10-28

**说明**：数据清洗、对齐、校准均统一迁往 Central Data Kitchen，V7 仅保留 Data Loader 契约示例。迁出条目如下：

| 模块 | 去向 | 迁移成本 |
| --- | --- | --- |
| `data/preprocessing/**` | CDK preprocessing service | M |
| `data/calibration/**` | CDK calibration pipeline | M |
| `data/alignment/**` | CDK feature alignment orchestrator | L |

保留内容：`data/meta/`、`data/raw/.gitkeep` 作为契约示例。

## 《Adapter 外移清单》
迁出日期：2025-10-28

**说明**：Adapter 层承担跨窗口、重计算逻辑，需迁往 CDK/Decision/Ops 后再纳入治理。

| 模块 | 去向 | 迁移成本 |
| --- | --- | --- |
| `features/adapter/**` | CDK feature derivation modules | M |
| `validation/adapter/**` | Ops validation toolkit | S |
| `scripts/audit*.py` | Decision/Ops audit automation | S |

