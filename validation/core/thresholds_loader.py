"""Unified loader for governance-managed validation thresholds."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore[import-untyped]

_CONTROL_PATH = Path("governance/CONTROL_switch_policy.yaml")


def _normalise_entry(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, (int, float)):
        return {"gate": float(entry), "warn": None, "fail": None}
    if not isinstance(entry, dict):
        return {"gate": None, "warn": None, "fail": None}

    gate = entry.get("gate")
    if gate is None and "threshold" in entry:
        gate = entry["threshold"]
    if gate is None and {"min", "max"} <= entry.keys():
        gate = (entry["min"], entry["max"])
    elif gate is None and "min" in entry:
        gate = entry["min"]
    elif gate is None and "max" in entry:
        gate = entry["max"]

    return {
        "gate": gate,
        "warn": entry.get("warn"),
        "fail": entry.get("fail"),
    }


def load_thresholds(path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Load validation thresholds from the single governance source."""

    policy_path = path or _CONTROL_PATH
    if not policy_path.exists():
        raise FileNotFoundError(f"Control policy file not found: {policy_path}")

    payload = yaml.safe_load(policy_path.read_text()) or {}
    raw_thresholds = payload.get("thresholds", {})

    return {key: _normalise_entry(value) for key, value in raw_thresholds.items()}


__all__ = ["load_thresholds"]
