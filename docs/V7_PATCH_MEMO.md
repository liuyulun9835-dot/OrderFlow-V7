---
# V7 Patch Memo (branch: qianyi)

## 1. What changed (files)
- governance/SCHEMA_data.json — NEW
- governance/SCHEMA_features.json — NEW
- governance/SCHEMA_execution.json — NEW
- governance/SCHEMA_model.json — UPDATED (add label_map, confirm v7.0)
- governance/label_map.yaml — NEW (A→balance, B→trend)
- governance/CONTROL_switch_policy.yaml — UPDATED (default thresholds+curve)
- validation/costs.yaml — NEW (Binance VIP0 defaults)
- .github/workflows/ci.yml — UPDATED (compliance path, minimal V7 pipeline)
- model/z_legacy/... — MOVED legacy hsmm modules
- output/clusterer_dynamic/label_alignment_report.md — NEW (artifact path)
- validation/VALIDATION.md & validation/metrics_summary.json — UPDATED

## 2. Placeholders vs Defaults
- Placeholders:
  - governance/SCHEMA_features.json → "macro_features": [] (optional at V7-M0)
  - output/clusterer_dynamic/label_alignment_report.md → content format fixed; values filled by run
- Defaults:
  - governance/CONTROL_switch_policy.yaml → thresholds, position_curve, abstain/trigger
  - validation/costs.yaml → maker/taker bps, slippage, maker_ratio
  - governance/SCHEMA_model.json → label_map: {A: balance, B: trend}

## 3. How to modify later (steps)
- Update thresholds/curve based on validation:
  1) Edit governance/CONTROL_switch_policy.yaml
  2) Run: make validate && make release
  3) Check VALIDATION.md and Gate results in CI
- Change label semantics:
  1) Edit governance/label_map.yaml and governance/SCHEMA_model.json.label_map
  2) Re-run cluster.fit → tvtp.fit → validate
- Add macro slow factors:
  1) Append names in governance/SCHEMA_features.json.macro_features
  2) Provide aligned columns in data preprocessing
  3) Re-train tvtp.fit and re-validate

## 4. Logic & Sources
- Data & feature schemas are aligned to:
  - Binance 1m (columns: open_time_ms, open, high, low, close, volume, timestamp, minute_open, minute_close) — UTC
  - ATAS v6.3 JSONL (bar_vpo_*, cvd, absorption_*)
- Execution contract encodes abstain and clarity→position mapping to ensure "low clarity, low exposure".
- CI runs the minimal V7 pipeline; gates read CONTROL thresholds.

---
