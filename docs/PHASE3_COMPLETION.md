# Phase 3 Completion Summary

Phase 3 (Core-Only Minimal Path Consolidation) has been completed with 7 commits:

## Commits

1. `918b7e5` - chore(governance): enforce single threshold source CONTROL_switch_policy.yaml; deprecate validation/thresholds.yaml
2. `7a34659` - refactor(validation): unify metrics aggregation via validation/core/aggregator.py and dedupe helpers
3. `66f002c` - chore(features-core): prune unused feature builders and keep only those consumed by Trainer
4. `4809fcb` - refactor(pipeline): unify single training entry and single publisher entry; remove parallel stubs
5. `d3f428c` - build(ci): lock minimal path (lint/test/validate) and gate release on core metrics only
6. `1b035c9` - docs: dedupe README/TODO and mark validation.md as generated-only
7. `2b36970` - chore(compat): plan wrapper deprecation and enforce no core->adapter imports via linter

## Key Achievements

- ✅ Single source of truth for thresholds: `governance/CONTROL_switch_policy.yaml`
- ✅ Unified validation entry: `validation/core/aggregator.py`
- ✅ Single publisher entry: `publisher/publisher.py`
- ✅ Deduplicated helper functions in `validation/core/utils_metrics.py`
- ✅ Converted features/noise_metrics to thin wrappers
- ✅ Simplified README and documentation
- ✅ Added linter rules to prevent core→adapter imports
- ✅ Documented deprecation timeline in MIGRATION_NOTES.md

## Files Modified

### Created:
- `validation/core/__init__.py`
- `validation/core/thresholds_loader.py`
- `validation/core/aggregator.py`
- `validation/core/utils_metrics.py`
- `publisher/__init__.py`
- `publisher/publisher.py`

### Modified:
- `validation/thresholds.yaml` (deprecated to stub)
- `validation/metrics.py` (uses thresholds_loader)
- `validation/VALIDATION.md` (marked as generated)
- `features/noise_metrics/*.py` (converted to wrappers)
- `Makefile` (simplified release target)
- `README.md` (simplified and deduplicated)
- `pyproject.toml` (added ruff config)
- `docs/MIGRATION_NOTES.md` (added deprecation plan)

## Branch

Branch: `only-model-core`
Target: `main`
PR Title: "V7 core-only: minimal path consolidation and deduplication (phase 3)"
