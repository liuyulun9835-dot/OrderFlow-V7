"""Unified inference utilities for the two-state TVTP-HSMM model.
WHY: Expose state, confidence, and transition probability to decision logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass
class InferenceOutput:
    state: str
    confidence: float
    transition_prob: float


class InferenceError(RuntimeError):
    """Raised when inference cannot be performed."""


def predict_proba(snapshot: Mapping[str, float]) -> InferenceOutput:
    """Return a minimal inference output for downstream consumers.

    Parameters
    ----------
    snapshot:
        Mapping containing pre-computed regime scores. In the absence of the full
        statistical model we fallback to a deterministic transformation that mirrors the
        expected API so the rest of the stack stops referencing missing code.
    """

    if "score" not in snapshot:
        raise InferenceError("snapshot must contain a 'score' field in [0, 1]")

    score = float(snapshot["score"])
    score = max(0.0, min(1.0, score))

    state = "trend" if score >= 0.5 else "balance"
    confidence = abs(score - 0.5) * 2.0
    transition_prob = score if state == "trend" else 1.0 - score
    return InferenceOutput(state=state, confidence=confidence, transition_prob=transition_prob)
