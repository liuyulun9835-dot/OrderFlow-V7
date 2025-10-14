#!/usr/bin/env python3
"""Merge ATAS order-flow data with exchange klines to build a feature set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from zoneinfo import ZoneInfo

TIMESTAMP_CANDIDATES = ("timestamp", "time", "datetime", "dt", "bar_time")
DEFAULT_ATAS_DIR = Path("data/atas")
DEFAULT_KLINE_PATH = Path("data/exchange/kline_1m.parquet")
DEFAULT_OUTPUT_PATH = Path("data/processed/features.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge ATAS and exchange data into features.parquet")
    parser.add_argument("--symbol", help="Symbol identifier for logging", default=None)
    parser.add_argument("--atas-dir", type=Path, default=DEFAULT_ATAS_DIR, help="Directory containing ATAS exports")
    parser.add_argument("--kline", type=Path, default=DEFAULT_KLINE_PATH, help="Path to 1m kline parquet file")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Path to output parquet file")
    parser.add_argument("--atas-tz", default="Europe/Moscow", help="Timezone for naive ATAS timestamps")
    parser.add_argument("--tolerance-seconds", type=int, default=45, help="Nearest-neighbour tolerance in seconds")
    parser.add_argument("--offset-minutes", type=int, help="Override ATAS timestamp offset in minutes")
    return parser.parse_args()


def detect_timestamp_column(columns: Iterable[str]) -> str:
    for candidate in TIMESTAMP_CANDIDATES:
        if candidate in columns:
            return candidate
    raise ValueError("No timestamp column found in ATAS file")


def frame_from_payload(payload: Any) -> pd.DataFrame:
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            return pd.DataFrame(payload["data"])
        return pd.DataFrame([payload])
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    return pd.DataFrame()


def load_json_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return pd.read_json(path, lines=True)
    return frame_from_payload(data)


def load_jsonl_file(path: Path) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            frame = frame_from_payload(data)
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def normalise_atas_frame(df: pd.DataFrame, tz_name: str) -> pd.DataFrame:
    if df.empty:
        return df
    ts_column = detect_timestamp_column(df.columns)
    df = df.copy()
    df.columns = [col.strip() for col in df.columns]
    df = df.dropna(how="all")
    df[ts_column] = pd.to_datetime(df[ts_column], utc=False, errors="coerce")
    df = df.dropna(subset=[ts_column])
    timestamps = df[ts_column]
    if getattr(timestamps.dt, "tz", None) is None:
        timestamps = timestamps.dt.tz_localize(ZoneInfo(tz_name))
    timestamps = timestamps.dt.tz_convert("UTC")
    df["timestamp_raw"] = timestamps
    if ts_column != "timestamp":
        df.drop(columns=[ts_column], inplace=True)
    df["timestamp"] = df["timestamp_raw"].dt.floor("min")
    df.sort_values("timestamp_raw", inplace=True)
    return df


def iter_atas_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"ATAS directory not found: {directory}")
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    )
    if not files:
        raise ValueError(f"No json/jsonl files found in {directory}")
    return files


def load_atas(directory: Path, tz_name: str) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for path in iter_atas_files(directory):
        if path.suffix.lower() == ".jsonl":
            raw = load_jsonl_file(path)
        else:
            raw = load_json_file(path)
        normalised = normalise_atas_frame(raw, tz_name)
        if not normalised.empty:
            frames.append(normalised)
    if not frames:
        raise ValueError(f"No ATAS data parsed from {directory}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("timestamp_raw")
    merged = merged.groupby("timestamp", as_index=False).last()
    merged.drop(columns=["timestamp_raw"], inplace=True)
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged


def load_kline(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Kline parquet not found: {path}")
    df = pd.read_parquet(path)
    if "timestamp" not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={df.index.name or "index": "timestamp"})
        elif "ts" in df.columns:
            df = df.rename(columns={"ts": "timestamp"})
        else:
            raise ValueError("Kline parquet must contain a 'timestamp' column or datetime index/column 'ts'")
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.floor("min")
    df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)
    return df


def estimate_offset_minutes(atas: pd.DataFrame, kline: pd.DataFrame) -> Tuple[int, bool]:
    if atas.empty or kline.empty:
        return 0, False
    sample = atas.head(2000).copy()
    sample = sample.sort_values("timestamp")
    kline_subset = kline[["timestamp"]].copy().rename(columns={"timestamp": "kline_timestamp"})
    merged = pd.merge_asof(
        sample[["timestamp"]],
        kline_subset,
        left_on="timestamp",
        right_on="kline_timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=300),
    )
    merged.dropna(subset=["kline_timestamp"], inplace=True)
    if merged.empty:
        return 0, False
    delta_minutes = (
        (merged["kline_timestamp"] - merged["timestamp"]).dt.total_seconds() / 60.0
    )
    median_offset = float(delta_minutes.median())
    rounded = int(round(median_offset))
    if abs(median_offset - rounded) <= 0.4:
        return rounded, True
    return 0, False


def apply_offset(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes == 0:
        return df
    shifted = df.copy()
    shifted["timestamp"] = shifted["timestamp"] + pd.Timedelta(minutes=minutes)
    shifted["timestamp"] = shifted["timestamp"].dt.floor("min")
    shifted = shifted.groupby("timestamp", as_index=False).last()
    return shifted.sort_values("timestamp").reset_index(drop=True)


def flatten_absorption(df: pd.DataFrame) -> pd.DataFrame:
    detected = df.get("absorption_detected", pd.Series(index=df.index, dtype="object"))
    strength = df.get("absorption_strength", pd.Series(index=df.index, dtype="float64"))
    side = df.get("absorption_side", pd.Series(index=df.index, dtype="object"))

    if "absorption" in df.columns:
        extracted_detected = []
        extracted_strength = []
        extracted_side = []
        for value in df["absorption"]:
            if isinstance(value, dict):
                extracted_detected.append(value.get("detected"))
                extracted_strength.append(value.get("strength") or value.get("volume"))
                extracted_side.append(value.get("side") or value.get("direction"))
            else:
                extracted_detected.append(None)
                extracted_strength.append(None)
                extracted_side.append(None)
        detected = detected.combine_first(pd.Series(extracted_detected, index=df.index))
        strength = strength.combine_first(pd.Series(extracted_strength, index=df.index))
        side = side.combine_first(pd.Series(extracted_side, index=df.index))
        df = df.drop(columns=["absorption"])

    df["absorption_detected"] = detected.replace({"": np.nan})
    df["absorption_strength"] = pd.to_numeric(strength, errors="coerce")
    df["absorption_side"] = side.replace({" ": np.nan, "": np.nan})
    return df


def merge_streams(kline: pd.DataFrame, atas: pd.DataFrame, tolerance_seconds: int) -> pd.DataFrame:
    merged = pd.merge_asof(
        kline.sort_values("timestamp"),
        atas.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=tolerance_seconds),
    )
    merged = flatten_absorption(merged)
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged


def order_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [col for col in df.columns if col != "timestamp"]
    ordered = ["timestamp"] + sorted(columns, key=lambda x: x.lower())
    return df[ordered]


def print_coverage(df: pd.DataFrame) -> None:
    print("Column coverage (non-null ratio):")
    for column in df.columns:
        if column == "timestamp":
            continue
        series = df[column]
        coverage = series.replace({"": np.nan}).notna().mean()
        print(f"  {column}: {coverage:.2%}")


def main() -> None:
    args = parse_args()
    atas_df = load_atas(args.atas_dir, args.atas_tz)
    kline_df = load_kline(args.kline)

    if args.offset_minutes is not None:
        offset = args.offset_minutes
    else:
        offset, _ = estimate_offset_minutes(atas_df, kline_df)
    if offset != 0:
        atas_df = apply_offset(atas_df, offset)
    print(f"ATAS offset applied: {offset} minute(s) ({'auto' if args.offset_minutes is None else 'manual'})")

    merged = merge_streams(kline_df, atas_df, args.tolerance_seconds)
    merged = order_columns(merged)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(merged, preserve_index=False)
    pq.write_table(table, args.output)

    print(f"Merged rows: {len(merged)}")
    if not merged.empty:
        print(f"Time range: {merged['timestamp'].min()} → {merged['timestamp'].max()}")
    print_coverage(merged)


if __name__ == "__main__":
    main()
