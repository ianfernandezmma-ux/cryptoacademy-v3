"""Derivatives feature block: funding, open interest, positioning, taker flow,
implied vol. Empirically the strongest crypto-specific predictors.

Inputs (data/raw): funding (8h), metrics (5-min OI + long/short + taker since
2020-09; ETH only since 2021-12 -> native NaN + missingness indicator),
options DVOL (daily since 2021-03).

All series are aggregated to daily UTC and joined as-of at assembly. Rolling
stats are causal; the global decision-time shift happens at assembly.
"""

from __future__ import annotations

import polars as pl


def funding_daily(funding: pl.DataFrame) -> pl.DataFrame:
    """8h funding -> daily aggregates + regime stats."""
    daily = (
        funding.sort("funding_time")
        .group_by_dynamic("funding_time", every="1d")
        .agg(
            pl.col("funding_rate").sum().alias("funding_1d"),
            pl.col("funding_rate").last().alias("funding_last"),
        )
        .rename({"funding_time": "date"})
        .sort("date")
    )
    f = pl.col("funding_1d")
    return daily.with_columns(
        ((f - f.rolling_mean(30)) / (f.rolling_std(30) + 1e-12)).alias("funding_z_30d"),
        ((f - f.rolling_mean(90)) / (f.rolling_std(90) + 1e-12)).alias("funding_z_90d"),
        f.rolling_sum(7).alias("funding_7d_cum"),
        (f - f.shift(7)).alias("funding_mom_7d"),
    )


def metrics_daily(metrics: pl.DataFrame) -> pl.DataFrame:
    """5-min positioning metrics -> daily features."""
    daily = (
        metrics.sort("create_time")
        .group_by_dynamic("create_time", every="1d")
        .agg(
            pl.col("sum_open_interest").last().alias("oi"),
            pl.col("sum_open_interest_value").last().alias("oi_usd"),
            pl.col("sum_toptrader_long_short_ratio").mean().alias("top_ls_pos_ratio"),
            pl.col("count_toptrader_long_short_ratio").mean().alias("top_ls_acct_ratio"),
            pl.col("count_long_short_ratio").mean().alias("global_ls_ratio"),
            pl.col("sum_taker_long_short_vol_ratio").mean().alias("taker_ls_ratio"),
        )
        .rename({"create_time": "date"})
        .sort("date")
    )
    oi = pl.col("oi_usd")
    return daily.with_columns(
        (oi / oi.shift(1) - 1).alias("oi_chg_1d"),
        (oi / oi.shift(7) - 1).alias("oi_chg_7d"),
        ((oi - oi.rolling_mean(90)) / (oi.rolling_std(90) + 1e-12)).alias("oi_z_90d"),
        _z("top_ls_pos_ratio", 90),
        _z("global_ls_ratio", 90),
        _z("taker_ls_ratio", 30),
        # positioning data existence flag (ETH starts 2021-12; MNAR is signal)
        pl.col("top_ls_pos_ratio").is_null().alias("positioning_missing"),
    )


def dvol_daily(dvol: pl.DataFrame) -> pl.DataFrame:
    """Deribit DVOL (annualized implied vol, 0-250 scale) -> IV features.
    The variance risk premium (IV - realized) is joined at assembly where
    realized vol lives."""
    d = dvol.sort("time").rename({"time": "date"})
    iv = pl.col("dvol_close")
    return d.select(
        pl.col("date"),
        (iv / 100.0).alias("iv_30d"),  # to decimal annualized
        ((iv - iv.shift(5)) / (iv.shift(5) + 1e-12)).alias("iv_chg_5d"),
        ((iv - iv.rolling_mean(90)) / (iv.rolling_std(90) + 1e-12)).alias("iv_z_90d"),
        ((pl.col("dvol_high") - pl.col("dvol_low")) / (iv + 1e-12)).alias("iv_intraday_range"),
    )


def _z(col: str, window: int) -> pl.Expr:
    c = pl.col(col)
    return ((c - c.rolling_mean(window)) / (c.rolling_std(window) + 1e-12)).alias(
        f"{col}_z_{window}d"
    )
