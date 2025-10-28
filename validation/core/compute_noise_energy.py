"""
Compute noise energy metric for stability gate validation.

This metric calculates a normalized variance-energy metric for low clarity intervals,
used to assess stability of model predictions during uncertain states.
"""

import numpy as np


def compute_noise_energy(
    clarity: np.ndarray, predictions: np.ndarray, clarity_threshold: float = 0.55
) -> float:
    """
    Calculate normalized variance-energy metric for low clarity intervals.

    The noise energy metric measures the variance in predictions during periods
    of low clarity (confidence), normalized by the total variance. This helps
    identify when the model is unstable.

    Args:
        clarity: Array of clarity scores (0 to 1 scale)
        predictions: Array of prediction values (e.g., transition probabilities)
        clarity_threshold: Threshold below which clarity is considered low

    Returns:
        Noise energy score (0 to 1), where higher values indicate more noise

    Raises:
        ValueError: If inputs are mismatched or empty
    """
    if len(clarity) != len(predictions):
        raise ValueError("Clarity and predictions must have same length")

    if len(clarity) == 0:
        raise ValueError("Input arrays cannot be empty")

    # Filter low clarity intervals
    low_clarity_mask = clarity < clarity_threshold

    if not np.any(low_clarity_mask):
        # No low clarity intervals, noise energy is zero
        return 0.0

    # Calculate variance in low clarity periods
    low_clarity_predictions = predictions[low_clarity_mask]
    low_clarity_variance = (
        np.var(low_clarity_predictions, ddof=1)
        if len(low_clarity_predictions) > 1
        else 0.0
    )

    # Calculate total variance for normalization
    total_variance = np.var(predictions, ddof=1) if len(predictions) > 1 else 1.0

    # Avoid division by zero
    if total_variance < 1e-10:
        return 0.0

    # Normalized noise energy
    noise_energy = low_clarity_variance / total_variance

    return float(np.clip(noise_energy, 0.0, 1.0))


def _self_test():
    """Minimal self-test for noise energy computation."""
    # Test case 1: Stable predictions with low clarity
    clarity = np.array([0.4, 0.45, 0.5, 0.7, 0.8])
    predictions = np.array([0.5, 0.51, 0.49, 0.6, 0.62])
    energy = compute_noise_energy(clarity, predictions)
    assert 0.0 <= energy <= 1.0, "Noise energy must be in [0, 1]"
    print(f"Test 1 - Stable predictions: noise_energy = {energy:.4f}")

    # Test case 2: Noisy predictions with low clarity
    clarity = np.array([0.3, 0.4, 0.5, 0.9, 0.95])
    predictions = np.array([0.2, 0.8, 0.3, 0.6, 0.61])
    energy = compute_noise_energy(clarity, predictions)
    assert 0.0 <= energy <= 1.0, "Noise energy must be in [0, 1]"
    assert energy > 0.1, "Should detect high noise in low clarity periods"
    print(f"Test 2 - Noisy predictions: noise_energy = {energy:.4f}")

    # Test case 3: All high clarity
    clarity = np.array([0.8, 0.85, 0.9, 0.95, 1.0])
    predictions = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    energy = compute_noise_energy(clarity, predictions)
    assert energy == 0.0, "No low clarity intervals should yield zero noise"
    print(f"Test 3 - High clarity only: noise_energy = {energy:.4f}")

    # Test case 4: Error handling
    try:
        compute_noise_energy(np.array([0.5]), np.array([0.5, 0.6]))
        assert False, "Should raise ValueError for mismatched lengths"
    except ValueError as e:
        print(f"Test 4 - Error handling: {e}")

    print("✓ All self-tests passed")


if __name__ == "__main__":
    _self_test()
