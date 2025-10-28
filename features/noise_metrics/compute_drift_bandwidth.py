"""
V7.1 noise metric — drift_bandwidth
定义：原型向量（prototype）序列的一阶差分范数的标准差，衡量结构漂移的“带宽”（扩散范围）。
输入：
    proto_vectors: np.ndarray, 形状 (T, D) 或 (T,)
输出：
    float ≥ 0
说明：
    - 对差分序列 ||p_t - p_{t-1}|| 做 std，T<3 返回 0。
"""
from __future__ import annotations
import numpy as np

def compute_drift_bandwidth(proto_vectors: np.ndarray) -> float:
    """
    Compute drift bandwidth as std of the norm of first-order differences.

    Args:
        proto_vectors: array-like, shape (T, D) or (T,)

    Returns:
        float: standard deviation of step norms; 0.0 if insufficient data.
    """
    if proto_vectors is None:
        return 0.0
    arr = np.asarray(proto_vectors, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.shape[0] < 3:
        return 0.0
    diffs = np.diff(arr, axis=0)
    step_norm = np.linalg.norm(diffs, axis=1)
    return float(np.std(step_norm, ddof=1)) if step_norm.size > 1 else 0.0


if __name__ == "__main__":
    rng = np.random.default_rng(123)
    T, D = 200, 4
    proto = np.cumsum(rng.normal(0, 0.02, size=(T, D)), axis=0)  # slow drift trajectory
    print("drift_bandwidth:", compute_drift_bandwidth(proto))