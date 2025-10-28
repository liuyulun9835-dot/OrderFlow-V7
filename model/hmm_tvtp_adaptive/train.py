"""Adaptive TVTP training focused on transition probabilities."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

import numpy as np
import pandas as pd

from model.clusterer_dynamic.fit import ClustererConfig
from model.clusterer_dynamic.fit import load_default_config as load_cluster_config
from model.clusterer_dynamic.fit import run as run_clusterer

LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    feature_columns: Sequence[str]
    label_column: str = "state"
    state_a: str = "A"
    state_b: str = "B"
    regularisation: float = 1e-2
    max_iter: int = 500
    learning_rate: float = 0.05
    artifacts_dir: Path = Path("model/hmm_tvtp_adaptive/artifacts")
    transition_output: Path = Path("output/tvtp/transition_prob.parquet")
    calibration_output: Path = Path("output/tvtp/calibration_report.json")


@dataclass
class TrainingArtifacts:
    coefficients: Dict[str, float]
    intercept: float


def _prepare_dataset(frame: pd.DataFrame, config: TrainingConfig) -> pd.DataFrame:
    missing = [
        col
        for col in list(config.feature_columns) + [config.label_column]
        if col not in frame.columns
    ]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    shifted = frame[[config.label_column] + list(config.feature_columns)].copy()
    shifted["next_state"] = shifted[config.label_column].shift(-1)
    shifted = shifted.dropna().reset_index(drop=True)
    return shifted


def _encode_states(values: Iterable[str], state_a: str, state_b: str) -> np.ndarray:
    mapping = {state_a: 0, state_b: 1}
    return np.array([mapping.get(v, 0) for v in values], dtype=float)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _fit_logistic(
    features: np.ndarray, targets: np.ndarray, config: TrainingConfig
) -> Tuple[np.ndarray, float]:
    weights = np.zeros(features.shape[1], dtype=float)
    bias = 0.0
    for _ in range(config.max_iter):
        logits = features @ weights + bias
        probs = _sigmoid(logits)
        errors = probs - targets
        grad_w = (
            features.T @ errors / features.shape[0] + config.regularisation * weights
        )
        grad_b = errors.mean()
        weights -= config.learning_rate * grad_w
        bias -= config.learning_rate * grad_b
    return weights, bias


def _predict_transition(
    features: np.ndarray, weights: np.ndarray, bias: float
) -> np.ndarray:
    logits = features @ weights + bias
    return _sigmoid(logits)


def _brier_score(probs: np.ndarray, targets: np.ndarray) -> float:
    return float(np.mean((probs - targets) ** 2))


def _expected_calibration_error(
    probs: np.ndarray, targets: np.ndarray, bins: int = 10
) -> float:
    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lower, upper in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (probs >= lower) & (probs < upper)
        if not np.any(mask):
            continue
        bucket_conf = probs[mask].mean()
        bucket_acc = targets[mask].mean()
        ece += probs[mask].size / probs.size * abs(bucket_conf - bucket_acc)
    return float(ece)


def _save_artifacts(artifacts: TrainingArtifacts, config: TrainingConfig) -> None:
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "coefficients": artifacts.coefficients,
        "intercept": artifacts.intercept,
        "state_a": config.state_a,
        "state_b": config.state_b,
        "feature_columns": list(config.feature_columns),
    }
    (config.artifacts_dir / "model_params.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )


def _write_outputs(
    frame: pd.DataFrame,
    probs: np.ndarray,
    config: TrainingConfig,
    ece: float,
    brier: float,
) -> None:
    config.transition_output.parent.mkdir(parents=True, exist_ok=True)
    enriched = frame.copy()
    enriched["transition_prob"] = probs
    try:
        enriched.to_parquet(config.transition_output, index=False)
    except Exception as exc:  # pragma: no cover - fallback path
        fallback = config.transition_output.with_suffix(".csv")
        enriched.to_csv(fallback, index=False)
        LOGGER.warning(
            "parquet export failed (%s); wrote CSV fallback to %s", exc, fallback
        )

    report = {
        "ece": ece,
        "brier": brier,
        "count": int(frame.shape[0]),
    }
    config.calibration_output.parent.mkdir(parents=True, exist_ok=True)
    config.calibration_output.write_text(json.dumps(report, indent=2, sort_keys=True))


def train(frame: pd.DataFrame, config: TrainingConfig) -> TrainingArtifacts:
    dataset = _prepare_dataset(frame, config)
    features = dataset[list(config.feature_columns)].to_numpy(dtype=float)
    states = _encode_states(
        dataset[config.label_column], config.state_a, config.state_b
    )
    next_states = _encode_states(dataset["next_state"], config.state_a, config.state_b)

    transition_mask = states == 0  # focus on A->B switches
    features_subset = features[transition_mask]
    targets_subset = next_states[transition_mask]

    weights, bias = _fit_logistic(features_subset, targets_subset, config)
    probs = _predict_transition(features_subset, weights, bias)
    ece = _expected_calibration_error(probs, targets_subset)
    brier = _brier_score(probs, targets_subset)

    _write_outputs(
        dataset.loc[transition_mask, list(config.feature_columns)],
        probs,
        config,
        ece,
        brier,
    )

    artifacts = TrainingArtifacts(
        coefficients={col: float(w) for col, w in zip(config.feature_columns, weights)},
        intercept=float(bias),
    )
    _save_artifacts(artifacts, config)
    LOGGER.info("TVTP training complete: ece=%.4f brier=%.4f", ece, brier)
    return artifacts


def _default_cluster_frame(rows: int = 512) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    columns = [
        "bar_vpo_imbalance",
        "bar_vpo_absorption",
        "cvd_rolling",
        "volprofile_skew",
    ]
    data = rng.normal(0.0, 1.0, size=(rows, len(columns)))
    return pd.DataFrame(data, columns=columns)


def _default_tvtp_frame(rows: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    states = rng.choice(["A", "B"], size=rows)
    frame = pd.DataFrame(
        {
            "state": states,
            "macro_regime": rng.normal(0.0, 1.0, size=rows),
            "volatility_slope": rng.normal(0.0, 1.0, size=rows),
        }
    )
    return frame


def run_training_pipeline(
    cluster_frame: pd.DataFrame | None = None,
    tvtp_frame: pd.DataFrame | None = None,
    cluster_config: ClustererConfig | None = None,
    tvtp_config: TrainingConfig | None = None,
) -> Dict[str, Dict[str, float]]:
    """Run the unified training pipeline covering clusterer and TVTP stages."""

    cluster_data = (
        cluster_frame.copy() if cluster_frame is not None else _default_cluster_frame()
    )
    cluster_cfg = cluster_config or load_cluster_config(cluster_data.columns)
    LOGGER.info("Running clusterer stage via unified training entry")
    cluster_summary = run_clusterer(cluster_data, cluster_cfg)

    tvtp_data = tvtp_frame.copy() if tvtp_frame is not None else _default_tvtp_frame()
    tvtp_cfg = tvtp_config or TrainingConfig(
        feature_columns=["macro_regime", "volatility_slope"]
    )
    LOGGER.info("Running TVTP stage via unified training entry")
    tvtp_artifacts = train(tvtp_data, tvtp_cfg)

    return {
        "cluster": cluster_summary,
        "tvtp": asdict(tvtp_artifacts),
    }


def main() -> None:
    run_training_pipeline()


__all__ = [
    "TrainingConfig",
    "TrainingArtifacts",
    "train",
    "run_training_pipeline",
    "main",
]
