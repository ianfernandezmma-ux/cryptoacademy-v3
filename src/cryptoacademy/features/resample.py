"""1h klines -> daily UTC bars, preserving taker order-flow columns."""

from __future__ import annotations

import polars as pl


def to_daily(df_1h: pl.DataFrame) -> pl.DataFrame:
    """Aggregate 1h bars into daily UTC bars [00:00, 24:00).

    The daily bar labeled D covers day D entirely — it is only fully known at
    D+1 00:00. Matrix assembly aligns it to decision times accordingly.
    """
    return (
        df_1h.sort("open_time")
        .group_by_dynamic("open_time", every="1d")
        .agg(
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col("volume").sum(),
            pl.col("quote_volume").sum(),
            pl.col("trades").sum(),
            pl.col("taker_buy_base").sum(),
            pl.col("taker_buy_quote").sum(),
            pl.len().alias("n_bars"),
        )
        .rename({"open_time": "date"})
        .with_columns(
            # days with missing hours (exchange outages) are flagged, not fixed
            (pl.col("n_bars") < 24).alias("incomplete_day")
        )
    )
