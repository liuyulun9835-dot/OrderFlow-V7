from __future__ import annotations

import json
import os
from pathlib import Path


def cdk_root() -> Path:
    return Path(os.getenv("CDK_DATA_ROOT", "/mnt/cdk"))


def resolve_paths(symbol: str, date: str) -> dict:
    base = cdk_root() / "snapshots" / symbol / date
    return {
        "manifest": base / "manifest.json",
        "x_train": base / "X_train.parquet",
        "y_train": base / "y_train.parquet",
    }


def load_manifest(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))
