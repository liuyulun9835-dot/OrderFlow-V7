# V7 Model-Layer Interface Whitelist

## Inputs (Read-Only, from CentralDataKitchen)
- Env `CDK_DATA_ROOT` 作为根路径
- 允许文件（示例）：
  - snapshots/{SYMBOL}/{YYYY-MM-DD}/manifest.json
  - snapshots/{SYMBOL}/{YYYY-MM-DD}/X_train.parquet
  - snapshots/{SYMBOL}/{YYYY-MM-DD}/y_train.parquet

## Outputs (To Decision layer)
- models/<MODEL_NAME>/**
- models/<MODEL_NAME>/signature.json
- validation/VALIDATION.md, validation/metrics_summary.json
- status/model_core.json

## Governance
- governance/CONTROL_switch_policy.yaml
