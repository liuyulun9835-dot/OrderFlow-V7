"""Decision layer for V7 adaptive switching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from decision.directional_classifier import DirectionalOutput, infer as infer_direction
from model.hmm_tvtp_adaptive.state_inference import InferenceOutput


@dataclass
class DecisionConfig:
    transition_gate: float = 0.65
    clarity_breakpoints: Sequence[float] = (0.0, 0.5, 0.7, 0.85, 1.0)
    position_scale: Sequence[float] = (0.0, 0.2, 0.5, 0.8, 1.0)


@dataclass
class DecisionResult:
    label: str
    position_size: float
    abstain: bool
    reason: str
    transition_prob: float
    clarity: float
    directional: DirectionalOutput | None


def _map_clarity_to_position(clarity: float, breakpoints: Sequence[float], scale: Sequence[float]) -> float:
    if len(breakpoints) != len(scale):
        raise ValueError("clarity breakpoints and scale must match in length")
    for idx, boundary in enumerate(breakpoints):
        if clarity <= boundary:
            return float(scale[idx])
    return float(scale[-1])


def evaluate(features: Mapping[str, float], inference: InferenceOutput, config: DecisionConfig | None = None) -> DecisionResult:
    cfg = config or DecisionConfig()
    if inference.abstain or inference.transition_prob < cfg.transition_gate:
        return DecisionResult(
            label="neutral",
            position_size=0.0,
            abstain=True,
            reason=inference.reason if inference.abstain else "transition_prob_below_gate",
            transition_prob=inference.transition_prob,
            clarity=inference.clarity,
            directional=None,
        )

    directional = infer_direction(features)
    position_size = _map_clarity_to_position(inference.clarity, cfg.clarity_breakpoints, cfg.position_scale)
    return DecisionResult(
        label=directional.label,
        position_size=position_size,
        abstain=False,
        reason="transition_prob_above_threshold",
        transition_prob=inference.transition_prob,
        clarity=inference.clarity,
        directional=directional,
    )


__all__ = ["DecisionConfig", "DecisionResult", "evaluate"]
