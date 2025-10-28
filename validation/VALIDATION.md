# VALIDATION — V7.1 Metrics & Stability Gates

## Core Metrics

| Metric | Value | Gate | Notes |
| --- | --- | --- | --- |
| prototype_drift | N/A | <= 0.15 | Scaled Euclidean drift of cluster centroids |
| ece | N/A | <= 0.08 | Expected calibration error of transition probability |
| brier | N/A | <= 0.18 | Brier score of transition probability |
| abstain_rate | N/A | 0.10–0.25 | Share of observations abstaining |
| transition_hit_ratio | N/A | >= 0.60 | Trigger gate uses transition_prob >= 0.65 |
| count | 0 | - | Sample size |

## V7.1 Stability Gate Metrics

| Metric | Value | Gate | Notes |
| --- | --- | --- | --- |
| stability_index | N/A | >= 0.60 | Overall stability index combining multiple signals |
| noise_energy | N/A | <= 0.30 | Normalized variance-energy in low clarity intervals |
| drift_bandwidth | N/A | warn: 0.08, fail: 0.12 | Bandwidth proxy using first-order differences |
| clarity_spectrum_power | N/A | warn: 0.005, fail: 0.010 | High-frequency power from Welch's method |
| adversarial_gap | N/A | warn: 0.15, fail: 0.25 | Mean squared distance to noisy embeddings |

> Gates sourced from governance/CONTROL_switch_policy.yaml

## Stability Gate Logic

### Noise Energy
Measures the normalized variance of predictions during low clarity periods. High noise energy indicates that the model produces unstable predictions when confidence is low.

**Computation:**
```python
from validation.compute_noise_energy import compute_noise_energy

# clarity: array of clarity scores (0-1)
# predictions: array of prediction values
noise_energy = compute_noise_energy(clarity, predictions, clarity_threshold=0.55)
# Result should be <= 0.30 to pass
```

**Interpretation:**
- `< 0.10`: Excellent stability in low clarity regions
- `0.10 - 0.20`: Good stability
- `0.20 - 0.30`: Acceptable (gate threshold)
- `> 0.30`: **FAIL** - Model is unstable during uncertain periods

### Drift Bandwidth
Computes the rate of change in cluster prototypes using first-order differences. Higher bandwidth indicates faster drift in the feature space.

**Computation:**
```python
from validation.compute_drift_bandwidth import compute_drift_bandwidth

# prototypes: array of shape (n_timepoints, n_features)
bandwidth = compute_drift_bandwidth(prototypes, sampling_rate=1.0)
# Warn if > 0.08, fail if > 0.12
```

**Interpretation:**
- `< 0.05`: Stable prototypes
- `0.05 - 0.08`: Normal drift
- `0.08 - 0.12`: **WARNING** - Elevated drift
- `> 0.12`: **FAIL** - Excessive drift

### Clarity Spectrum Power
Analyzes frequency content of clarity scores to detect high-frequency oscillations that may indicate instability.

**Computation:**
```python
from validation.compute_clarity_spectrum_power import compute_clarity_spectrum_power

# clarity: time series of clarity scores
power = compute_clarity_spectrum_power(clarity, sampling_rate=1.0)
# Warn if > 0.005, fail if > 0.010
```

**Interpretation:**
- `< 0.001`: Baseline (stable clarity)
- `0.001 - 0.005`: Acceptable oscillation
- `0.005 - 0.010`: **WARNING** - Elevated oscillation
- `> 0.010`: **FAIL** - Excessive oscillation

### Adversarial Gap
Measures model robustness by computing the distance between original and noisy embeddings.

**Computation:**
```python
from validation.compute_adversarial_gap import compute_adversarial_gap

# embeddings: array of shape (n_samples, n_features)
gap = compute_adversarial_gap(embeddings, noise_scale=0.1, noise_type="gaussian")
# Warn if > 0.15, fail if > 0.25
```

**Interpretation:**
- `< 0.10`: Excellent robustness
- `0.10 - 0.15`: Good robustness
- `0.15 - 0.25`: **WARNING** - Reduced robustness
- `> 0.25`: **FAIL** - Poor robustness to noise

## Validation Pipeline

1. **Compute Metrics**: Run `make cluster.fit` + `make tvtp.fit` + `make validate`
2. **Evaluate Gates**: Check against thresholds in `governance/CONTROL_switch_policy.yaml`
3. **Generate Report**: Updates this file and `validation/metrics_summary.json`
4. **Release Decision**: Critical failures block release; warnings require review

## Example Validation Run

```bash
# Run full validation pipeline
make data.qc
make cluster.fit
make tvtp.fit
make validate

# Check metrics
cat validation/metrics_summary.json
cat validation/VALIDATION.md

# If all gates pass
make release
```

## Gate Failure Actions

| Severity | Action | Description |
| --- | --- | --- |
| **Critical** | Block Release | Must be fixed before release |
| **Warning** | Require Review | Manual approval needed |
| **Info** | Log Only | Monitor but don't block |

## References

- Threshold definitions: `validation/thresholds.yaml`
- Governance schema: `governance/SCHEMA_validation.json`
- Validation rules: `governance/RULES_validation.yaml`
- Control policy: `governance/CONTROL_switch_policy.yaml`
