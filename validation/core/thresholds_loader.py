from __future__ import annotations

import yaml
from pathlib import Path

def load_policy(path: str | Path = "governance/CONTROL_switch_policy.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing thresholds policy: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
