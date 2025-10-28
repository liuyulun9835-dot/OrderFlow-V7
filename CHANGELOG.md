# CHANGELOG — OrderFlow V7

## [7.1] - 2025-10-28

### Added - Stability Gate Metrics & Governance
- **Noise Metrics**: Implemented four new stability metrics for enhanced operational validation
  - `compute_noise_energy.py`: Normalized variance-energy metric for low clarity intervals
  - `compute_drift_bandwidth.py`: Bandwidth proxy using first-order differences of prototypes
  - `compute_clarity_spectrum_power.py`: High-frequency power spectrum analysis via Welch's method
  - `compute_adversarial_gap.py`: Robustness metric measuring distance to noisy embeddings
  - All metrics include comprehensive self-tests and documentation

- **Validation Configuration**: New YAML-based threshold management
  - `validation/thresholds.yaml`: Centralized threshold definitions for all stability metrics
  - Stability index threshold: 0.60 (fail below)
  - Noise energy threshold: 0.30 (fail above)
  - Dynamic warn/fail thresholds for drift and spectrum metrics

- **Governance Schemas**: Enhanced schema definitions for V7.1
  - `governance/SCHEMA_validation.json`: Complete validation metric requirements and gate policies
  - `governance/RULES_validation.yaml`: Comprehensive rule library with 20+ validation rules
  - Updated `governance/CONTROL_switch_policy.yaml` with V7.1 stability thresholds

- **Documentation**: Comprehensive updates for stability gates
  - Updated `validation/VALIDATION.md` with detailed stability gate logic and examples
  - Added computation examples and interpretation guidelines for each metric
  - Documented validation pipeline workflow and gate failure actions
  - Added `TODO_V7_1.md` with pending tasks for pipeline integration

- **Architectural Updates**: Version bump and compatibility notes
  - Updated `docs/ARCHITECTURE.md` with V7.1 stability gate integration
  - Added V7.1 compatibility notes to schema files

### Changed
- Python version constraint updated from `<3.12` to `<3.13` to support Python 3.12
- Schema version updated from `v7.0` to `v7.1` across governance files
- Enhanced `CONTROL_switch_policy.yaml` with five new stability metric thresholds

### Technical Details
- All noise metrics are fully tested with comprehensive self-test suites
- Metrics use numpy for computations and scipy for spectral analysis (Welch's method)
- Validation framework supports critical/warning/info severity levels
- Gate policies include fail_below, fail_above, warn_fail, range, and min_only types

### Migration Notes
- Existing V7.0 metrics remain unchanged and backward compatible
- New metrics are additive and don't break existing pipelines
- Thresholds can be customized in `validation/thresholds.yaml`
- Validation schema requires new metrics for V7.1 releases

---

## [7.0] - 2025-10-26

### Initial V7 Release
- Clusterer dynamic with online K=2 clustering
- Adaptive TVTP with transition-only learning
- Clarity and abstain signals
- Prototype drift monitoring
- ECE/Brier calibration metrics
- Comprehensive governance framework

### Core Features
- Data QC pipeline with AB source alignment
- HMM TVTP adaptive training
- State inference with clarity mapping
- Decision engine with abstain policy
- Validation metrics framework

### Infrastructure
- Complete governance schema definitions
- Control switch policy with threshold gates
- CI/CD pipeline with schema validation
- Release signature and audit trail

---

## Version Numbering

- **Major (7.x.x)**: Architectural changes, breaking changes
- **Minor (x.1.x)**: New features, metrics, enhancements (backward compatible)
- **Patch (x.x.1)**: Bug fixes, documentation updates, minor tweaks

## Future Releases

See `docs/TODO_V7_1.md` for planned enhancements and pending tasks.
