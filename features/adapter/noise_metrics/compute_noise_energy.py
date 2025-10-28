"""compute_noise_energy.py

# ADAPTER: planned to migrate to CDK

Minimal implementation for noise_energy metric.

Functions
---------
compute_noise_energy(clarity_series: pd.Series, low_threshold: float) -> float
    Select intervals where clarity < low_threshold, compute a robust normalized
    variance-energy metric: var / (mean + eps). Returns float in [0, +inf).

Notes
-----
- clarity_series: pandas Series indexed by time (dtype float).
- low_threshold: threshold τ for selecting 'low-clarity' windows.
- Returns 0.0 if no samples below threshold.
"""
import numpy as np
import pandas as pd


def compute_noise_energy(
    clarity_series: pd.Series, low_threshold: float, eps: float = 1e-8
) -> float:
    # select samples below threshold
    low_vals = clarity_series[clarity_series < low_threshold].dropna().values
    if low_vals.size == 0:
        return 0.0
    # robust mean and variance (median / mad-like)
    mean = np.mean(low_vals)
    var = np.var(low_vals, ddof=1) if low_vals.size > 1 else 0.0
    # normalized energy: var / (abs(mean) + eps) — if mean near 0, denominator eps prevents div0
    energy = var / (abs(mean) + eps)
    # optionally clamp to [0, +inf); user can later clip to [0,1] by calibration
    return float(energy)


if __name__ == "__main__":
    # simple self-test
    import pandas as pd

    np.random.seed(0)
    clarity = pd.Series(
        np.concatenate([np.linspace(0.9, 0.7, 10), 0.2 + 0.05 * np.random.randn(40)])
    )
    val = compute_noise_energy(clarity, low_threshold=0.5)
    print(f"self-test noise_energy: {val:.6f}")
