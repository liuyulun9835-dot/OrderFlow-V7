"""
V7.1 noise metric — adversarial_gap
定义：真实样本嵌入 vs 扰动样本嵌入的差距（gap），可用 MSE 或马氏距离。
输入：
    embed_real: np.ndarray (N, D)
    embed_noisy: np.ndarray (N, D)  — 与真实一一对齐
输出：
    float ≥ 0
说明：
    - 缺省使用均方差（稳健简单）；若样本足够可切换到马氏距离。
"""
from __future__ import annotations
import numpy as np
from typing import Literal

def compute_adversarial_gap(
    embed_real: np.ndarray,
    embed_noisy: np.ndarray,
    method: Literal["mse", "mahalanobis"] = "mse",
) -> float:
    """
    Compute adversarial gap between embeddings.

    Args:
        embed_real: (N,D) or (D,)
        embed_noisy: same shape as embed_real
        method: 'mse' (default) or 'mahalanobis'

    Returns:
        float: mean gap (>=0)
    """
    A = np.asarray(embed_real, dtype=float)
    B = np.asarray(embed_noisy, dtype=float)
    if A.shape != B.shape or A.size == 0:
        return 0.0
    if method == "mse":
        return float(np.mean((A - B) ** 2))
    elif method == "mahalanobis":
        # build covariance from combined data and regularize
        X = np.vstack([A.reshape(-1, A.shape[-1]), B.reshape(-1, B.shape[-1])])
        cov = np.cov(X.T) + 1e-6 * np.eye(X.shape[1])
        try:
            inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(cov)
        diff = (A - B).reshape(-1, A.shape[-1])
        m2 = np.einsum("ni,ij,nj->n", diff, inv, diff)
        return float(np.mean(m2))
    else:
        return float(np.mean((A - B) ** 2))


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    A = rng.normal(0, 1, (128, 16))
    B = A + rng.normal(0, 0.1, (128, 16))
    print("adversarial_gap[mse]:", compute_adversarial_gap(A, B, "mse"))
