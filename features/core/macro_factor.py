"""Macro slow factor construction (e.g., price/MA200) for TVTP drivers.
WHY: Provide stable drivers for TVTP, aligning code with README claims.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MacroFactorConfig:
    """Configuration for macro factor construction."""

    window: int = 200
    column: str = "close"
    min_periods: int | None = None


def build(df: pd.DataFrame, cfg: MacroFactorConfig | None = None) -> pd.DataFrame:
    """Construct macro factor features required by TVTP models.

    Parameters
    ----------
    df:
        Input dataframe containing OHLCV style columns.
    cfg:
        Optional configuration. Defaults to :class:`MacroFactorConfig`.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the macro factor columns used by the model.

    Raises
    ------
    KeyError
        If the configured column does not exist in the input frame.
    """

    cfg = cfg or MacroFactorConfig()
    if cfg.column not in df.columns:
        raise KeyError(f"Required column '{cfg.column}' not found in dataframe")

    min_periods = cfg.min_periods or max(1, cfg.window // 2)
    rolling_mean = df[cfg.column].rolling(cfg.window, min_periods=min_periods).mean()

    out = pd.DataFrame(index=df.index)
    out["MA_ratio"] = df[cfg.column] / rolling_mean
    out["macro_factor_used"] = True
    return out
