#!/usr/bin/env python3
"""Fetch minute-level OHLCV data using CCXT and store it as parquet."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import ccxt  # type: ignore
import pandas as pd


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch 1m kline data and store as parquet")
    parser.add_argument("symbol", nargs="?", help="Trading pair symbol, e.g. BTC/USDT")
    parser.add_argument("start_date", nargs="?", help="Start date (YYYY-MM-DD)")
    parser.add_argument("end_date", nargs="?", help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", dest="symbol_opt", help="Trading pair symbol, e.g. BTC/USDT")
    parser.add_argument("--since", dest="since_opt", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--until", dest="until_opt", help="End date inclusive (YYYY-MM-DD)")
    parser.add_argument("--exchange", default="binance", help="CCXT exchange id (default: binance)")
    args = parser.parse_args()

    symbol = args.symbol_opt or args.symbol
    since = args.since_opt or args.start_date
    until = args.until_opt or args.end_date

    missing = [name for name, value in {"symbol": symbol, "since": since, "until": until}.items() if not value]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")

    args.symbol = symbol
    args.since = since
    args.until = until
    return args


def _sanitise_symbol(symbol: str) -> str:
    return "".join(ch for ch in symbol if ch.isalnum())


def to_milliseconds(date_string: str) -> int:
    dt = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def to_milliseconds_end(date_string: str) -> int:
    dt = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt = dt + timedelta(days=1) - timedelta(minutes=1)
    return int(dt.timestamp() * 1000)


def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str, since: int, until: int) -> List[List[float]]:
    timeframe = "1m"
    limit = 1000
    all_candles: List[List[float]] = []
    fetch_since = since

    while fetch_since <= until:
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=fetch_since, limit=limit)
        if not candles:
            break

        all_candles.extend(candles)
        last_timestamp = candles[-1][0]
        if last_timestamp >= until:
            break

        # Move forward by one millisecond to avoid duplicates
        fetch_since = last_timestamp + 1

    return all_candles


def prepare_dataframe(candles: List[List[float]]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)

    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp")
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    if not df.empty:
        full_index = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
        df = df.reindex(full_index)
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].ffill()

    return df


def save_parquet(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, engine="pyarrow")


def main() -> None:
    args = parse_arguments()
    start_ms = to_milliseconds(args.since)
    end_ms = to_milliseconds_end(args.until)

    exchange_class = getattr(ccxt, args.exchange)
    exchange = exchange_class({"enableRateLimit": True})

    candles = fetch_ohlcv(exchange, args.symbol, start_ms, end_ms)
    df = prepare_dataframe(candles)

    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "data" / "exchange" / _sanitise_symbol(args.symbol)
    output_path = output_dir / "kline_1m.parquet"

    save_parquet(df, output_path)


if __name__ == "__main__":
    main()
