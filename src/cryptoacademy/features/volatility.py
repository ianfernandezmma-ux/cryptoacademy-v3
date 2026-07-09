"""Volatility estimators (daily bars, 24/7 market).

Per Kristoufek (2025): range-based estimators beat GARCH for crypto. We use
Parkinson + Garman-Klass on daily OHLC plus realized vol from intraday (1h)
returns, and EWMA for label/position vol-scaling. All values are in daily
return units (not annualized) so barriers and targets share the scale.
Every rolling window ends at the CURRENT bar; the global anti-lookahead shift
to decision time happens once, at matrix assembly (features/matrix.py).
"""

from __future__ import annotations

import math

import polars as pl

LN2 = math.log(2.0)


def parkinson(window: int = 21) -> pl.Expr:
    """Rolling Parkinson vol from high/low range."""
    hl2 = (pl.col("high") / pl.col("low")).log().pow(2)
    return (hl2.rolling_mean(window) / (4 * LN2)).sqrt().alias(f"vol_parkinson_{window}d")


def garman_klass(window: int = 21) -> pl.Expr:
    """Rolling Garman-Klass vol from OHLC."""
    hl2 = (pl.col("high") / pl.col("low")).log().pow(2)
    co2 = (pl.col("close") / pl.col("open")).log().pow(2)
    per_bar = 0.5 * hl2 - (2 * LN2 - 1) * co2
    return per_bar.rolling_mean(window).clip(lower_bound=0).sqrt().alias(f"vol_gk_{window}d")


def realized_from_intraday(df_1h: pl.DataFrame) -> pl.DataFrame:
    """Daily realized vol = sqrt(sum of squared 1h log returns) per UTC day.

    The highest-quality daily vol measure available to us (24 obs/day).
    """
    return (
        df_1h.sort("open_time")
        .with_columns(pl.col("close").log().diff().alias("r1h"))
        .group_by_dynamic("open_time", every="1d")
        .agg((pl.col("r1h").pow(2).sum()).sqrt().alias("vol_realized_1d"))
        .rename({"open_time": "date"})
    )


def ewma_vol(half_life_days: int = 21) -> pl.Expr:
    """EWMA vol of daily log returns — the canonical sigma for vol-scaled
    labels, barriers and position sizing."""
    r = pl.col("close").log().diff()
    return (
        r.pow(2)
        .ewm_mean(half_life=float(half_life_days))
        .sqrt()
        .alias(f"vol_ewma_{half_life_days}d")
    )
