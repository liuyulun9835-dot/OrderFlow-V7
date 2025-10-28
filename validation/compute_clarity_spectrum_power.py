"""
Compute clarity spectrum power metric for stability gate validation.

This metric extracts high-frequency power spectrum using Welch's method to detect
rapid oscillations in clarity scores that may indicate model instability.
"""

import numpy as np
from scipy import signal
from typing import Optional


def compute_clarity_spectrum_power(
    clarity: np.ndarray,
    sampling_rate: float = 1.0,
    frequency_band: Optional[tuple[float, float]] = None,
    nperseg: Optional[int] = None
) -> float:
    """
    Extract high-frequency power spectrum using Welch's method.
    
    This metric analyzes the frequency content of clarity scores to detect
    high-frequency oscillations that may indicate instability or rapid changes
    in model confidence.
    
    Args:
        clarity: Array of clarity scores (time series)
        sampling_rate: Sampling rate of the clarity signal (default: 1.0)
        frequency_band: Optional tuple (low_freq, high_freq) to focus on specific band.
                       If None, uses upper half of Nyquist frequency
        nperseg: Length of each segment for Welch's method. If None, uses min(256, len(clarity))
        
    Returns:
        Total power in the high-frequency band (non-negative)
        
    Raises:
        ValueError: If clarity array is too short or invalid
    """
    if len(clarity) < 4:
        raise ValueError("Need at least 4 samples for spectral analysis")
    
    # Set segment length for Welch's method
    if nperseg is None:
        nperseg = min(256, len(clarity))
    
    # Ensure nperseg is valid
    nperseg = max(4, min(nperseg, len(clarity)))
    
    # Compute power spectral density using Welch's method
    frequencies, psd = signal.welch(
        clarity,
        fs=sampling_rate,
        nperseg=nperseg,
        scaling='density'
    )
    
    # Define high-frequency band
    nyquist = sampling_rate / 2.0
    if frequency_band is None:
        # Default: upper half of Nyquist frequency
        low_freq = nyquist / 2.0
        high_freq = nyquist
    else:
        low_freq, high_freq = frequency_band
    
    # Find frequency indices in the band
    freq_mask = (frequencies >= low_freq) & (frequencies <= high_freq)
    
    if not np.any(freq_mask):
        # No frequencies in band
        return 0.0
    
    # Integrate power in the frequency band
    power = np.trapz(psd[freq_mask], frequencies[freq_mask])
    
    return float(power)


def _self_test():
    """Minimal self-test for clarity spectrum power computation."""
    # Test case 1: Constant signal (no high-frequency content)
    clarity = np.ones(100) * 0.7
    power = compute_clarity_spectrum_power(clarity, sampling_rate=1.0)
    assert power < 0.01, "Constant signal should have minimal high-frequency power"
    print(f"Test 1 - Constant signal: power = {power:.6f}")
    
    # Test case 2: Slow oscillation (low frequency)
    t = np.linspace(0, 10, 100)
    clarity = 0.7 + 0.1 * np.sin(2 * np.pi * 0.1 * t)  # 0.1 Hz oscillation
    power = compute_clarity_spectrum_power(clarity, sampling_rate=10.0)
    print(f"Test 2 - Slow oscillation: power = {power:.6f}")
    
    # Test case 3: Fast oscillation (high frequency)
    t = np.linspace(0, 10, 1000)
    clarity = 0.7 + 0.1 * np.sin(2 * np.pi * 35.0 * t)  # 35 Hz oscillation (in upper half)
    power = compute_clarity_spectrum_power(clarity, sampling_rate=100.0)
    assert power > 0.0001, "Fast oscillation should have significant high-frequency power"
    print(f"Test 3 - Fast oscillation: power = {power:.6f}")
    
    # Test case 4: Custom frequency band
    t = np.linspace(0, 10, 1000)
    clarity = 0.7 + 0.1 * np.sin(2 * np.pi * 5.0 * t)  # 5 Hz oscillation
    power = compute_clarity_spectrum_power(
        clarity,
        sampling_rate=100.0,
        frequency_band=(4.0, 6.0)  # Band around 5 Hz
    )
    assert power > 0.001, "Should detect power in custom frequency band"
    print(f"Test 4 - Custom band (4-6 Hz): power = {power:.6f}")
    
    # Test case 5: Noisy signal
    np.random.seed(42)
    clarity = 0.7 + 0.05 * np.random.randn(500)
    power = compute_clarity_spectrum_power(clarity, sampling_rate=10.0)
    assert power > 0, "Noisy signal should have some high-frequency power"
    print(f"Test 5 - Noisy signal: power = {power:.6f}")
    
    # Test case 6: Error handling
    try:
        compute_clarity_spectrum_power(np.array([0.5, 0.6]))  # Too short
        assert False, "Should raise ValueError for short array"
    except ValueError as e:
        print(f"Test 6 - Error handling: {e}")
    
    print("✓ All self-tests passed")


if __name__ == "__main__":
    _self_test()
