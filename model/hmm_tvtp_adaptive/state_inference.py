"""State inference utilities for adaptive TVTP."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .train import TrainingArtifacts


@dataclass
class InferenceConfig:
    feature_columns: Sequence[str]
    transition_gate: float = 0.65
    min_clarity: float = 0.4
    artifacts_path: Path = Path("model/hmm_tvtp_adaptive/artifacts/model_params.json")


@dataclass
class InferenceOutput:
    transition_prob: float
    clarity: float
    abstain: bool
    reason: str


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _load_artifacts(path: Path) -> TrainingArtifacts:
    payload = json.loads(path.read_text())
    return TrainingArtifacts(
        coefficients=payload["coefficients"],
        intercept=float(payload["intercept"]),
    )


def _clarity_from_prob(prob: float) -> float:
    entropy = -(
        prob * math.log(prob + 1e-8) + (1.0 - prob) * math.log(1.0 - prob + 1e-8)
    )
    max_entropy = math.log(2.0)
    return 1.0 - entropy / max_entropy


def infer_row(
    features: Mapping[str, float], config: InferenceConfig, artifacts: TrainingArtifacts
) -> InferenceOutput:
    vector = np.array(
        [float(features[col]) for col in config.feature_columns], dtype=float
    )
    weights = np.array(
        [artifacts.coefficients[col] for col in config.feature_columns], dtype=float
    )
    prob = float(_sigmoid(vector @ weights + artifacts.intercept))
    clarity = _clarity_from_prob(prob)
    abstain = prob < config.transition_gate or clarity < config.min_clarity
    if abstain:
        reason = "low_confidence"
    else:
        reason = "transition_prob_above_threshold"
    return InferenceOutput(
        transition_prob=prob, clarity=clarity, abstain=abstain, reason=reason
    )


def run(frame: pd.DataFrame, config: InferenceConfig) -> pd.DataFrame:
    artifacts = _load_artifacts(config.artifacts_path)
    outputs = []
    for _, row in frame.iterrows():
        outputs.append(infer_row(row, config, artifacts))
    result = pd.DataFrame(
        [
            {
                "transition_prob": out.transition_prob,
                "clarity": out.clarity,
                "abstain": out.abstain,
                "reason": out.reason,
            }
            for out in outputs
        ]
    )
    return result


__all__ = ["InferenceConfig", "InferenceOutput", "infer_row", "run"]
