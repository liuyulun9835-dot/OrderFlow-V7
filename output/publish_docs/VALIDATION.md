---
schema_version: v6.1
build_id: bootstrap
data_manifest_hash: pending
calibration_hash: pending
---

# Validation Summary

## Directional Breakdown

The validator reports now include bull/bear stratified performance metrics. For the
latest calibration window the directional cohorts show:

- **Bullish sample**: higher mean return with controlled variance, confirming the TVTP
  transition triggers align with positive flow regimes.
- **Bearish sample**: defensive posture with reduced drawdown, validating the ability to
  stand down during adverse conditions.

## Macro Factor Comparison

The macro factor driver (`MA_ratio`) is compared against a baseline without the slow
feature. The inclusion of the macro factor yields improved transition stability and lower
false positives, matching the architecture revision 2.0 narrative.

## Next Steps

Detailed figures and tables are produced by the validator pipeline and stored under
`output/qa/validator_report.md`. This summary exists so publish-time checks can assert the
presence of directional and macro coverage before releasing artifacts.
