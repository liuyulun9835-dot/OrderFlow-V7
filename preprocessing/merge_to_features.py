#!/usr/bin/env python3
"""Merge ATAS order-flow data with exchange klines to build a feature set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


_ATAS_COLUMN_ALIASES = {
    "msi": "MSI",
    "mfi": "MFI",
    "kli": "KLI",
    "poc": "POC",
    "point_of_control": "POC",
    "vah": "VAH",
    "value_area_high": "VAH",
    "val": "VAL",
    "value_area_low": "VAL",
    "cvd": "CVD",
    "cumulative_volume_delta": "CVD",
    "absorption": "Absorption",
}


def _canonical_atas_column(name: str) -> str | None:
    key = name.strip().lower().replace(" ", "_")
    return _ATAS_COLUMN_ALIASES.get(key)


DEFAULT_ATAS_DIR = Path("data/atas")
DEFAULT_KLINE_PATH = Path("data/exchange/kline_1m.parquet")
DEFAULT_OUTPUT_PATH = Path("data/processed/features.parquet")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge ATAS and exchange data into features.parquet")
    parser.add_argument("--symbol", help="Symbol identifier for logging/metadata", default=None)
    parser.add_argument("--atas-dir", type=Path, default=DEFAULT_ATAS_DIR, help="Directory containing ATAS json/jsonl exports")
    parser.add_argument("--kline", type=Path, default=DEFAULT_KLINE_PATH, help="Path to 1m kline parquet file")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Path to output parquet file")
    return parser.parse_args()


def _detect_timestamp_column(columns: Iterable[str]) -> str:
    for candidate in ("timestamp", "time", "datetime", "ts"):
        if candidate in columns:
            return candidate
    raise ValueError("No timestamp column found in ATAS file")


def _frame_from_data(data: object) -> pd.DataFrame:
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            df = pd.DataFrame(data["data"])
        else:
            df = pd.DataFrame([data])
    else:
        df = pd.DataFrame(data)
    return df


def _normalise_atas_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    ts_col = _detect_timestamp_column(df.columns)
    df = df.copy()
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
    df = df.dropna(subset=[ts_col])
    df.rename(columns={ts_col: "timestamp"}, inplace=True)
    df["timestamp"] = df["timestamp"].dt.floor("min")
    rename_map = {}
    for column in df.columns:
        if column == "timestamp":
            continue
        canonical = _canonical_atas_column(column)
        if canonical is not None:
            rename_map[column] = canonical
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
    desired = []
    for column in df.columns:
        if column == "timestamp" or column in _ATAS_COLUMN_ALIASES.values():
            if column not in desired:
                desired.append(column)
    return df[desired]


def _load_single_json(path: Path) -> pd.DataFrame:
    raw = path.read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        df = pd.read_json(path, lines=True)
        return _normalise_atas_frame(df)

    df = _frame_from_data(data)
    return _normalise_atas_frame(df)


def _load_single_jsonl(path: Path) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse line in {path}: {exc}") from exc
            frames.append(_frame_from_data(data))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return _normalise_atas_frame(df)


def _iter_atas_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"ATAS directory not found: {directory}")
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    )
    if not files:
        raise ValueError(f"未在 {directory} 发现 json/jsonl")
    return files


def _load_atas(directory: Path) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for path in _iter_atas_files(directory):
        if path.suffix.lower() == ".jsonl":
            df = _load_single_jsonl(path)
        else:
            df = _load_single_json(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        raise ValueError(f"未在 {directory} 发现 json/jsonl")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    merged.set_index("timestamp", inplace=True)
    return merged


def _load_kline(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Kline parquet not found: {path}")
    df = pd.read_parquet(path)
    if "timestamp" not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            index_name = df.index.name or "index"
            df = df.reset_index().rename(columns={index_name: "timestamp"})
        elif "ts" in df.columns:
            df = df.rename(columns={"ts": "timestamp"})
        else:
            raise ValueError("Kline parquet must contain a 'timestamp' column or datetime index/column 'ts'")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.floor("min")
    for column in ["open", "high", "low", "close", "volume"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["timestamp"]).drop_duplicates(subset="timestamp", keep="last")
    df = df.sort_values("timestamp").set_index("timestamp")
    if df["close"].isna().any():
        raise ValueError("Found missing close prices in kline data")
    return df


def _build_features(kline: pd.DataFrame, atas: pd.DataFrame) -> pd.DataFrame:
    merged = kline.join(atas, how="inner")
    merged.sort_index(inplace=True)

    atas_lowercase_map = {
        column: column.lower()
        for column in ["POC", "VAH", "VAL", "CVD", "Absorption"]
        if column in merged.columns
    }
    if atas_lowercase_map:
        merged.rename(columns=atas_lowercase_map, inplace=True)

    metrics_cols = [
        c
        for c in ["MSI", "MFI", "KLI", "poc", "vah", "val", "cvd", "absorption"]
        if c in merged.columns
    ]
    if metrics_cols:
        numeric_metrics = [c for c in ["poc", "vah", "val", "cvd", "absorption"] if c in metrics_cols]
        for column in numeric_metrics:
            merged.loc[:, column] = pd.to_numeric(merged[column], errors="coerce")

    if "close" not in merged.columns:
        raise ValueError("Kline data must contain a 'close' column to compute returns")

    if merged["close"].isna().any():
        raise ValueError("Missing close prices detected after merge")

    safe_close = merged["close"].replace(0, np.nan)
    merged["return_1m"] = merged["close"].pct_change().fillna(0.0)
    merged["log_return_1m"] = np.log(safe_close).diff().replace([np.inf, -np.inf], 0.0).fillna(0.0)

    if "volume" in merged.columns:
        merged["volume_volatility_30m"] = (
            merged["volume"].rolling(window=30, min_periods=1).std().fillna(0.0)
        )
        merged["volume_mean_30m"] = merged["volume"].rolling(window=30, min_periods=1).mean().fillna(0.0)
    else:
        merged["volume_volatility_30m"] = 0.0
        merged["volume_mean_30m"] = 0.0

    if {"MSI", "MFI"}.issubset(merged.columns):
        merged["order_imbalance"] = (merged["MSI"] - merged["MFI"]).fillna(0.0)
    else:
        merged["order_imbalance"] = 0.0

    numeric_cols = merged.select_dtypes(include=["number"]).columns
    metric_columns = {"poc", "vah", "val", "cvd", "absorption", "msi", "mfi", "kli"}
    fill_cols = [col for col in numeric_cols if col.lower() not in metric_columns]
    if fill_cols:
        merged[fill_cols] = merged[fill_cols].fillna(0.0)

    merged.reset_index(inplace=True)
    merged.rename(columns={"index": "timestamp"}, inplace=True)
    return merged


def main() -> None:
    args = _parse_args()

    atas_df = _load_atas(args.atas_dir)
    kline_df = _load_kline(args.kline)
    features = _build_features(kline_df, atas_df)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(features)
    pq.write_table(table, args.output)


if __name__ == "__main__":
    main()
