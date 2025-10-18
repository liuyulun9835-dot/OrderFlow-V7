"""Directional classifier used once the model triggers a state transition.
WHY: README references a directional classifier; this file provides the callable stub.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import math


@dataclass
class DirectionalOutput:
    label: str
    confidence: float


def infer(features: Mapping[str, float]) -> DirectionalOutput:
    """Infer the directional label from lightweight handcrafted features.

    The implementation is intentionally simple but stable: the sign of the CVD feature
    dominates, modulated by a hyperbolic tangent of the money flow index. This mirrors the
    design described in the project documentation without requiring the actual classifier
    weights.
    """

    mfi = float(features.get("MFI", 0.0))
    cvd = float(features.get("CVD", 0.0))

    score = math.tanh(0.5 * mfi + 0.25 * math.copysign(1.0, cvd if cvd != 0 else 1.0))
    label = "bullish" if score >= 0 else "bearish"
    confidence = abs(score)
    return DirectionalOutput(label=label, confidence=confidence)
