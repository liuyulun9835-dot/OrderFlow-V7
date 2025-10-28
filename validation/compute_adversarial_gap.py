"""
Compute adversarial gap metric for stability gate validation.

This metric measures the mean squared distance between real embeddings and
noisy/perturbed embeddings to assess model robustness to input perturbations.
"""

import numpy as np
from typing import Optional


def compute_adversarial_gap(
    embeddings: np.ndarray,
    noise_scale: float = 0.1,
    noise_type: str = "gaussian",
    seed: Optional[int] = None
) -> float:
    """
    Measure mean squared distance between real and noisy embeddings.
    
    This metric assesses model robustness by adding noise to input embeddings
    and measuring how much the embeddings change. A larger gap indicates
    less robustness to perturbations.
    
    Args:
        embeddings: Array of embedding vectors, shape (n_samples, n_features)
        noise_scale: Scale of noise to add (relative to embedding std)
        noise_type: Type of noise - "gaussian" or "uniform"
        seed: Optional random seed for reproducibility
        
    Returns:
        Mean squared distance between original and noisy embeddings
        
    Raises:
        ValueError: If embeddings array is invalid or noise_type is unknown
    """
    if embeddings.ndim != 2:
        raise ValueError("Embeddings must be 2D array (samples × features)")
    
    n_samples, n_features = embeddings.shape
    
    if n_samples == 0 or n_features == 0:
        raise ValueError("Embeddings cannot be empty")
    
    if noise_scale < 0:
        raise ValueError("Noise scale must be non-negative")
    
    # Set random seed if provided
    if seed is not None:
        np.random.seed(seed)
    
    # Compute embedding standard deviation for scaling
    embedding_std = np.std(embeddings)
    if embedding_std < 1e-10:
        # Constant embeddings, any noise will cause large gap
        embedding_std = 1.0
    
    # Generate noise based on type
    if noise_type == "gaussian":
        noise = np.random.randn(n_samples, n_features) * noise_scale * embedding_std
    elif noise_type == "uniform":
        noise = np.random.uniform(-1, 1, (n_samples, n_features)) * noise_scale * embedding_std
    else:
        raise ValueError(f"Unknown noise_type: {noise_type}. Use 'gaussian' or 'uniform'")
    
    # Create noisy embeddings
    noisy_embeddings = embeddings + noise
    
    # Compute mean squared distance
    squared_distances = np.sum((embeddings - noisy_embeddings) ** 2, axis=1)
    mean_squared_distance = np.mean(squared_distances)
    
    return float(mean_squared_distance)


def _self_test():
    """Minimal self-test for adversarial gap computation."""
    # Test case 1: Small noise on random embeddings
    np.random.seed(42)
    embeddings = np.random.randn(100, 10)
    gap = compute_adversarial_gap(embeddings, noise_scale=0.1, seed=42)
    assert gap > 0, "Gap should be positive with noise"
    print(f"Test 1 - Small noise (0.1): gap = {gap:.6f}")
    
    # Test case 2: Larger noise should produce larger gap
    gap_small = compute_adversarial_gap(embeddings, noise_scale=0.1, seed=42)
    gap_large = compute_adversarial_gap(embeddings, noise_scale=0.5, seed=42)
    assert gap_large > gap_small, "Larger noise should produce larger gap"
    print(f"Test 2 - Noise scaling: small={gap_small:.6f}, large={gap_large:.6f}")
    
    # Test case 3: Uniform noise
    gap_uniform = compute_adversarial_gap(embeddings, noise_scale=0.1, noise_type="uniform", seed=42)
    assert gap_uniform > 0, "Uniform noise should also produce positive gap"
    print(f"Test 3 - Uniform noise: gap = {gap_uniform:.6f}")
    
    # Test case 4: Zero noise scale
    gap_zero = compute_adversarial_gap(embeddings, noise_scale=0.0, seed=42)
    assert gap_zero < 1e-10, "Zero noise should produce zero gap"
    print(f"Test 4 - Zero noise: gap = {gap_zero:.10f}")
    
    # Test case 5: Constant embeddings
    constant_embeddings = np.ones((50, 5)) * 2.0
    gap = compute_adversarial_gap(constant_embeddings, noise_scale=0.1, seed=42)
    assert gap > 0, "Should handle constant embeddings"
    print(f"Test 5 - Constant embeddings: gap = {gap:.6f}")
    
    # Test case 6: Single sample
    single_embedding = np.array([[1.0, 2.0, 3.0]])
    gap = compute_adversarial_gap(single_embedding, noise_scale=0.1, seed=42)
    assert gap >= 0, "Should handle single sample"
    print(f"Test 6 - Single sample: gap = {gap:.6f}")
    
    # Test case 7: Reproducibility with seed
    gap1 = compute_adversarial_gap(embeddings, noise_scale=0.1, seed=123)
    gap2 = compute_adversarial_gap(embeddings, noise_scale=0.1, seed=123)
    assert abs(gap1 - gap2) < 1e-10, "Same seed should produce same results"
    print(f"Test 7 - Reproducibility: gap1={gap1:.6f}, gap2={gap2:.6f}")
    
    # Test case 8: Error handling
    try:
        compute_adversarial_gap(np.array([1, 2, 3]))  # 1D array
        assert False, "Should raise ValueError for 1D array"
    except ValueError as e:
        print(f"Test 8 - Error handling (1D): {e}")
    
    try:
        compute_adversarial_gap(embeddings, noise_scale=0.1, noise_type="invalid")
        assert False, "Should raise ValueError for invalid noise type"
    except ValueError as e:
        print(f"Test 8 - Error handling (noise type): {e}")
    
    print("✓ All self-tests passed")


if __name__ == "__main__":
    _self_test()
