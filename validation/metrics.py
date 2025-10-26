"""Validation metrics summary for V7 pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from model.hmm_tvtp_adaptive.train import _expected_calibration_error as compute_ece
from model.hmm_tvtp_adaptive.train import _brier_score as compute_brier


@dataclass
class MetricConfig:
    transition_gate: float = 0.65
    cluster_artifacts: Path = Path("model/clusterer_dynamic/cluster_artifacts.json")
    metrics_json: Path = Path("validation/metrics_summary.json")
    metrics_markdown: Path = Path("validation/VALIDATION.md")


def _load_cluster_drift(path: Path) -> float:
    if not path.exists():
        return 0.0
    payload = json.loads(path.read_text())
    return float(payload.get("prototype_drift", 0.0))


def _ensure_columns(frame: pd.DataFrame) -> pd.DataFrame:
    expected = {"transition_prob", "actual_transition", "clarity", "abstain"}
    missing = expected.difference(frame.columns)
    if missing:
        for column in missing:
            if column == "actual_transition":
                frame[column] = 0.0
            elif column == "abstain":
                frame[column] = False
            else:
                frame[column] = 0.0
    return frame


def _transition_hit_ratio(frame: pd.DataFrame, gate: float) -> float:
    triggered = frame[frame["transition_prob"] >= gate]
    if triggered.empty:
        return 0.0
    hits = triggered["actual_transition"].mean()
    return float(hits)


def summarise(frame: pd.DataFrame, config: MetricConfig) -> dict:
    frame = _ensure_columns(frame.copy())
    probs = frame["transition_prob"].to_numpy(dtype=float)
    actual = frame["actual_transition"].to_numpy(dtype=float)

    brier = compute_brier(probs, actual)
    ece = compute_ece(probs, actual)
    abstain_rate = float(frame["abstain"].astype(float).mean())
    hit_ratio = _transition_hit_ratio(frame, config.transition_gate)
    prototype_drift = _load_cluster_drift(config.cluster_artifacts)

    metrics = {
        "prototype_drift": prototype_drift,
        "ece": ece,
        "brier": brier,
        "abstain_rate": abstain_rate,
        "transition_hit_ratio": hit_ratio,
        "count": int(frame.shape[0]),
    }
    return metrics


def _write_markdown(metrics: dict, config: MetricConfig) -> None:
    lines = ["# VALIDATION — V7 Metrics", "", "| Metric | Value |", "| --- | --- |"]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |")
    config.metrics_markdown.parent.mkdir(parents=True, exist_ok=True)
    config.metrics_markdown.write_text("\n".join(lines))


def write_reports(frame: pd.DataFrame, config: Optional[MetricConfig] = None) -> dict:
    cfg = config or MetricConfig()
    metrics = summarise(frame, cfg)
    cfg.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    cfg.metrics_json.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    _write_markdown(metrics, cfg)
    return metrics


__all__ = ["MetricConfig", "summarise", "write_reports"]
