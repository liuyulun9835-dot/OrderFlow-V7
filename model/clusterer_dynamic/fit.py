"""Minimal online clustering pipeline for V7 dynamic clusterer."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass
class ClustererConfig:
    """Configuration contract for the online clusterer."""

    feature_columns: Sequence[str]
    window_size: int = 240
    k: int = 2
    online_decay: float = 0.97
    alignment_log: Path = Path("output/cluster_alignment.log")
    artifacts_path: Path = Path("model/clusterer_dynamic/cluster_artifacts.json")
    labels_output: Path = Path("output/clusterer_dynamic/labels_wt.parquet")
    alignment_report: Path = Path("output/clusterer_dynamic/label_alignment_report.md")


def _load_window(dataset: pd.DataFrame, feature_columns: Sequence[str], window_size: int) -> pd.DataFrame:
    if dataset.empty:
        raise ValueError("Feature dataset is empty; cannot fit clusterer")

    missing = [col for col in feature_columns if col not in dataset.columns]
    if missing:
        raise KeyError(f"Missing required feature columns: {missing}")

    return dataset.tail(window_size).reset_index(drop=True)


def _initialise_centroids(data: np.ndarray, k: int) -> np.ndarray:
    if data.shape[0] < k:
        raise ValueError("Not enough samples to initialise centroids")

    indices = np.linspace(0, data.shape[0] - 1, k).astype(int)
    return data[indices]


def _online_update(data: np.ndarray, centroids: np.ndarray, decay: float) -> np.ndarray:
    updated = centroids.copy()
    for row in data:
        distances = np.linalg.norm(updated - row, axis=1)
        winner = int(np.argmin(distances))
        updated[winner] = decay * updated[winner] + (1.0 - decay) * row
    return updated


def _assign_labels(data: np.ndarray, centroids: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    distances = np.linalg.norm(data[:, None, :] - centroids[None, :, :], axis=2)
    labels = np.argmin(distances, axis=1)
    min_dist = distances[np.arange(distances.shape[0]), labels]
    weights = np.exp(-min_dist)
    return labels, weights


def _load_previous_artifacts(path: Path) -> Dict[str, List[float]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _compute_alignment(previous: Dict[str, List[float]], centroids: np.ndarray) -> Tuple[np.ndarray, bool]:
    if not previous:
        return centroids, False

    previous_centroids = np.array(previous.get("centroids", centroids))
    if previous_centroids.shape != centroids.shape:
        return centroids, False

    permutations = [np.arange(centroids.shape[0]), np.arange(centroids.shape[0])[::-1]]
    best_perm = permutations[0]
    best_score = float("inf")
    for perm in permutations:
        score = float(np.linalg.norm(previous_centroids - centroids[perm], axis=1).sum())
        if score < best_score:
            best_score = score
            best_perm = perm
    swapped = not np.array_equal(best_perm, permutations[0])
    return centroids[best_perm], swapped


def _prototype_drift(previous: Dict[str, List[float]], centroids: np.ndarray) -> float:
    if not previous:
        return 0.0
    old = np.array(previous.get("centroids", centroids))
    if old.shape != centroids.shape:
        return float(np.linalg.norm(centroids))
    return float(np.linalg.norm(old - centroids)) / max(float(np.linalg.norm(old)) + 1e-6, 1e-6)


def _write_alignment_log(path: Path, swapped: bool, drift: float, window_size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    message = f"window={window_size}, label_switch={int(swapped)}, prototype_drift={drift:.4f}\n"
    path.write_text(path.read_text() + message if path.exists() else message)


def _resolve_window_id(window: pd.DataFrame) -> str:
    if "window_id" in window.columns and window["window_id"].notna().any():
        return str(window["window_id"].iloc[-1])
    if "minute_close" in window.columns and window["minute_close"].notna().any():
        return str(window["minute_close"].iloc[-1])
    return f"tail_{len(window)}"


def _write_alignment_report(path: Path, window_id: str, swapped: bool, drift: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stability = max(0.0, 1.0 - drift)
    swap_count = int(swapped)
    ari = 0.0
    ami = 0.0
    hamming = float(swap_count)
    lines = [
        "# Clusterer Dynamic — Label Alignment Report",
        "",
        "| window_id | swap_count | stability | ARI | AMI | hamming_distance |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {window_id} | {swap_count} | {stability:.4f} | {ari:.4f} | {ami:.4f} | {hamming:.4f} |",
        "",
        "> ARI/AMI/Hamming placeholders will be replaced once historical alignment tracking is wired in.",
    ]
    path.write_text("\n".join(lines))


def _export_labels(dataset: pd.DataFrame, labels: np.ndarray, weights: np.ndarray, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched = dataset.copy()
    enriched["label"] = labels
    enriched["weight"] = weights
    try:
        enriched.to_parquet(output_path, index=False)
    except Exception as exc:  # pragma: no cover - fallback path
        fallback = output_path.with_suffix(".csv")
        enriched.to_csv(fallback, index=False)
        LOGGER.warning("parquet export failed (%s); wrote CSV fallback to %s", exc, fallback)


def _save_artifacts(centroids: np.ndarray, drift: float, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "centroids": centroids.tolist(),
        "prototype_drift": drift,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def run(dataset: pd.DataFrame, config: ClustererConfig) -> Dict[str, float]:
    """Fit the online clusterer and persist artifacts."""

    window = _load_window(dataset, config.feature_columns, config.window_size)
    data = window[config.feature_columns].to_numpy(dtype=float)

    centroids = _initialise_centroids(data, config.k)
    centroids = _online_update(data, centroids, config.online_decay)

    previous = _load_previous_artifacts(config.artifacts_path)
    centroids_aligned, swapped = _compute_alignment(previous, centroids)
    drift_value = _prototype_drift(previous, centroids_aligned)

    labels, weights = _assign_labels(data, centroids_aligned)

    _export_labels(window.assign(timestamp=window.index), labels, weights, config.labels_output)
    _save_artifacts(centroids_aligned, drift_value, config.artifacts_path)
    _write_alignment_log(config.alignment_log, swapped, drift_value, config.window_size)
    window_identifier = _resolve_window_id(window)
    _write_alignment_report(config.alignment_report, window_identifier, swapped, drift_value)

    LOGGER.info("clusterer_dynamic fit complete: drift=%.4f swapped=%s", drift_value, swapped)
    return {"prototype_drift": drift_value, "label_switch": swapped}


def load_default_config(feature_columns: Iterable[str]) -> ClustererConfig:
    return ClustererConfig(feature_columns=list(feature_columns))


__all__ = ["ClustererConfig", "load_default_config", "run"]
