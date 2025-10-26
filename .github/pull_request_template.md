## Summary
- [ ] Governance updated (SCHEMA/RULES/CONTROL)
- [ ] Data/Feature updates
- [ ] Model/Decision changes
- [ ] Validation/CI adjustments

## Schema Change Checklist
- [ ] `governance/SCHEMA_model.json`
- [ ] `governance/SCHEMA_decision.json`
- [ ] `governance/RULES_library.yaml`
- [ ] `governance/CONTROL_switch_policy.yaml`
- [ ] Sample artifacts regenerated (cluster/tvtp)

## Metrics & Gates
| Metric | Value | CONTROL Threshold | Pass? |
| --- | --- | --- | --- |
| prototype_drift |  | warn/fail:  |  |
| ece |  | fail:  |  |
| brier |  | fail:  |  |
| abstain_rate |  | min/max:  |  |
| transition_hit_ratio |  | min:  |  |

- Attach `validation/VALIDATION.md`
- Attach `output/signatures.json`

## Deployment
- [ ] `make data.qc`
- [ ] `make cluster.fit`
- [ ] `make tvtp.fit`
- [ ] `make validate`
- [ ] `make dryrun`
- [ ] `make release`

## Notes
<!-- Provide migration notes, blockers, or follow-ups -->
