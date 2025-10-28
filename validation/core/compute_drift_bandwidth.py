"""
Compute drift bandwidth metric for stability gate validation.

This metric computes a bandwidth proxy using first-order differences of prototype vectors,
measuring the rate of change in cluster centroids over time.
"""

from typing import Optional

import numpy as np


def compute_drift_bandwidth(
    prototypes: np.ndarray, sampling_rate: Optional[float] = None
) -> float:
    """
    Compute bandwidth proxy using first-order differences of prototype vectors.

    This metric measures the rate of change in cluster prototypes (centroids)
    by computing the RMS of first-order differences across time. Higher bandwidth
    indicates faster drift in the feature space.

    Args:
        prototypes: Array of prototype vectors, shape (n_timepoints, n_features)
                   Each row is a prototype at a given time
        sampling_rate: Optional sampling rate for scaling (default: 1.0)

    Returns:
        Drift bandwidth score (non-negative), higher values indicate faster drift

    Raises:
        ValueError: If prototypes array is invalid
    """
    if prototypes.ndim != 2:
        raise ValueError("Prototypes must be 2D array (timepoints × features)")

    n_timepoints, n_features = prototypes.shape

    if n_timepoints < 2:
        raise ValueError("Need at least 2 timepoints to compute drift")

    if n_features == 0:
        raise ValueError("Prototypes must have at least one feature")

    # Compute first-order differences along time axis
    diffs = np.diff(prototypes, axis=0)

    # Compute RMS of differences (Euclidean norm per timepoint)
    norms = np.linalg.norm(diffs, axis=1)

    # Average RMS across time
    bandwidth = np.sqrt(np.mean(norms**2))

    # Scale by sampling rate if provided
    if sampling_rate is not None and sampling_rate > 0:
        bandwidth *= sampling_rate

    return float(bandwidth)


def _self_test():
    """Minimal self-test for drift bandwidth computation."""
    # Test case 1: Stable prototypes (no drift)
    prototypes = np.array([[1.0, 2.0], [1.0, 2.0], [1.0, 2.0], [1.0, 2.0]])
    bandwidth = compute_drift_bandwidth(prototypes)
    assert bandwidth < 1e-10, "Stable prototypes should have near-zero bandwidth"
    print(f"Test 1 - Stable prototypes: bandwidth = {bandwidth:.6f}")

    # Test case 2: Linear drift
    prototypes = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    bandwidth = compute_drift_bandwidth(prototypes)
    assert bandwidth > 0, "Drifting prototypes should have positive bandwidth"
    expected = np.sqrt(2)  # sqrt(1^2 + 1^2)
    assert abs(bandwidth - expected) < 0.01, f"Expected ~{expected}, got {bandwidth}"
    print(f"Test 2 - Linear drift: bandwidth = {bandwidth:.6f}")

    # Test case 3: With sampling rate
    prototypes = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    bandwidth_1x = compute_drift_bandwidth(prototypes, sampling_rate=1.0)
    bandwidth_2x = compute_drift_bandwidth(prototypes, sampling_rate=2.0)
    assert (
        abs(bandwidth_2x - 2 * bandwidth_1x) < 1e-6
    ), "Sampling rate should scale linearly"
    print(
        f"Test 3 - Sampling rate scaling: 1x={bandwidth_1x:.6f}, 2x={bandwidth_2x:.6f}"
    )

    # Test case 4: High-dimensional prototypes
    np.random.seed(42)
    prototypes = np.cumsum(np.random.randn(10, 5), axis=0)  # Random walk
    bandwidth = compute_drift_bandwidth(prototypes)
    assert bandwidth > 0, "Random walk should have positive bandwidth"
    print(f"Test 4 - High-dimensional drift: bandwidth = {bandwidth:.6f}")

    # Test case 5: Error handling
    try:
        compute_drift_bandwidth(np.array([1, 2, 3]))  # 1D array
        assert False, "Should raise ValueError for 1D array"
    except ValueError as e:
        print(f"Test 5 - Error handling (1D): {e}")

    try:
        compute_drift_bandwidth(np.array([[1, 2]]))  # Only 1 timepoint
        assert False, "Should raise ValueError for single timepoint"
    except ValueError as e:
        print(f"Test 5 - Error handling (single): {e}")

    print("✓ All self-tests passed")


if __name__ == "__main__":
    _self_test()
