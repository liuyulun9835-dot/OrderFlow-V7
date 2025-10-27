from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import json

import pandas as pd
import yaml

from model.hmm_tvtp_adaptive.train import _expected_calibration_error as compute_ece
from model.hmm_tvtp_adaptive.train import _brier_score as compute_brier


@dataclass
class MetricConfig:
    transition_gate: float = 0.65
    cluster_artifacts: Path = Path("model/clusterer_dynamic/cluster_artifacts.json")
    metrics_json: Path = Path("validation/metrics_summary.json")
    metrics_markdown: Path = Path("validation/VALIDATION.md")
    control_yaml: Path = Path("governance/CONTROL_switch_policy.yaml")


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


def _load_control_thresholds(path: Path) -> Dict[str, Dict[str, float]]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    return raw.get("thresholds", {})


def summarise(frame: pd.DataFrame, config: MetricConfig) -> Dict[str, float]:
    frame = _ensure_columns(frame.copy())
    probs = frame["transition_prob"].to_numpy(dtype=float)
    actual = frame["actual_transition"].to_numpy(dtype=float)

    brier = compute_brier(probs, actual)
    ece = compute_ece(probs, actual)
    abstain_rate = float(frame["abstain"].astype(float).mean())
    hit_ratio = _transition_hit_ratio(frame, config.transition_gate)
    prototype_drift = _load_cluster_drift(config.cluster_artifacts)

    metrics = {
        "prototype_drift": float(prototype_drift),
        "ece": 0.0 if pd.isna(ece) else float(ece),
        "brier": float(brier),
        "abstain_rate": float(abstain_rate),
        "transition_hit_ratio": float(hit_ratio),
        "count": int(frame.shape[0]),
    }
    return metrics


def _format_gate(metric: str, thresholds: Dict[str, Dict[str, float]]) -> str:
    gate = thresholds.get(metric)
    if gate is None:
        return "-"
    if isinstance(gate, dict):
        if {"min", "max"} <= gate.keys():
            return f"{gate['min']:.2f}–{gate['max']:.2f}"
        if "min" in gate:
            return f">= {gate['min']:.2f}"
        if "max" in gate:
            return f"<= {gate['max']:.2f}"
        if "fail" in gate:
            return f"<= {gate['fail']:.2f}"
        if "gate" in gate:
            return f">= {gate['gate']:.2f}"
    if isinstance(gate, (int, float)):
        return f"{gate:.2f}"
    return "-"


def _write_markdown(metrics: Dict[str, float], config: MetricConfig, thresholds: Dict[str, Dict[str, float]]) -> None:
    lines = ["# VALIDATION — V7 Metrics", "", "| Metric | Value | Gate | Notes |", "| --- | --- | --- | --- |"]
    notes = {
        "prototype_drift": "Scaled Euclidean drift of cluster centroids",
        "ece": "Expected calibration error of transition probability",
        "brier": "Brier score of transition probability",
        "abstain_rate": "Share of observations abstaining",
        "transition_hit_ratio": f"Trigger gate uses transition_prob >= {config.transition_gate:.2f}",
        "count": "Sample size"
    }
    for key, value in metrics.items():
        display = f"{value:.4f}" if isinstance(value, float) else str(value)
        lines.append(f"| {key} | {display} | {_format_gate(key, thresholds)} | {notes.get(key, '')} |")
    lines.append("")
    lines.append("> Gates sourced from governance/CONTROL_switch_policy.yaml")
    config.metrics_markdown.parent.mkdir(parents=True, exist_ok=True)
    config.metrics_markdown.write_text("\n".join(lines))


def write_reports(frame: pd.DataFrame, config: Optional[MetricConfig] = None) -> Dict[str, float]:
    cfg = config or MetricConfig()
    metrics = summarise(frame, cfg)
    thresholds = _load_control_thresholds(cfg.control_yaml)
    payload = {"metrics": metrics, "thresholds": thresholds}
    cfg.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    cfg.metrics_json.write_text(json.dumps(payload, indent=2, sort_keys=True))
    _write_markdown(metrics, cfg, thresholds)
    return metrics


__all__ = ["MetricConfig", "summarise", "write_reports"]
