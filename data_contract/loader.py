from __future__ import annotations
import json, os
from pathlib import Path

def _root(cfg_path="configs/data_source.yaml") -> Path:
    # 简单解析环境变量为主；不做任何数据层处理
    root = os.getenv("CDK_DATA_ROOT", "/mnt/cdk")
    return Path(root)

def resolve_paths(symbol: str, date: str, cfg_path="configs/data_source.yaml") -> dict:
    # 最小实现：拼路径，不做转换/合并
    root = _root(cfg_path)
    base = root / "snapshots" / symbol / date
    return {
        "manifest": base / "manifest.json",
        "x_train": base / "X_train.parquet",
        "y_train": base / "y_train.parquet"
    }

def load_manifest(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))
