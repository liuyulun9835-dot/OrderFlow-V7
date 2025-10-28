"""
V7.1 noise metric — clarity_spectrum_power
定义：clarity 序列在高频带的平均功率，衡量“快速震荡的噪声能量”。

# ADAPTER: planned to migrate to CDK
输入：
    clarity_series: pd.Series[float]
    hi_band: tuple[float,float]，归一频带（0,0.5]，例如 (0.1, 0.5)
输出：
    float ≥ 0
实现要点：
    - 使用 FFT 估功率谱；去均值；仅累计目标频带。
    - 长度不足或异常返回 0。
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def compute_clarity_spectrum_power(
    clarity_series: pd.Series, hi_band: Tuple[float, float] = (0.1, 0.5)
) -> float:
    """
    Compute average PSD in given normalized high-frequency band using FFT.

    Args:
        clarity_series: pd.Series or array-like
        hi_band: tuple (lo, hi) in normalized frequency [0, 0.5] assuming fs=1

    Returns:
        float: average power in band (>=0), 0 if insufficient data
    """
    if clarity_series is None:
        return 0.0
    x = pd.Series(clarity_series).dropna().astype(float).values
    n = x.size
    if n < 8:
        return 0.0
    x = x - np.mean(x)
    # real FFT PSD estimate (normalized sampling freq = 1)
    X = np.fft.rfft(x)
    psd = (np.abs(X) ** 2) / (n + 1e-8)
    freqs = np.fft.rfftfreq(n, d=1.0)
    lo, hi = hi_band
    lo = max(0.0, float(lo))
    hi = min(0.5, float(hi))
    band_mask = (freqs >= lo) & (freqs <= hi)
    if not np.any(band_mask):
        return 0.0
    band_power = float(np.mean(psd[band_mask]))
    return max(0.0, band_power)


if __name__ == "__main__":
    import pandas as pd

    # synth low+high freq mixture
    n = 256
    t = np.arange(n)
    low = 0.3 * np.sin(2 * np.pi * t / n * 4)
    high = 0.1 * np.sin(2 * np.pi * t / n * 40)
    noise = 0.05 * np.random.randn(n)
    series = pd.Series(low + high + noise + 0.5)
    print("clarity_spectrum_power:", compute_clarity_spectrum_power(series, (0.1, 0.5)))
