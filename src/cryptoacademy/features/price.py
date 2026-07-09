"""Price/volume feature block on daily bars.

Every expression is causal (rolling windows end at the current bar). The
matrix assembler applies the single global shift to decision time — feature
code never shifts, so the discipline lives in exactly one place.
"""

from __future__ import annotations

import polars as pl

from cryptoacademy.features.volatility import ewma_vol, garman_klass, parkinson

MOM_HORIZONS = [1, 2, 5, 10, 21, 63, 126, 252]


def _logret(h: int) -> pl.Expr:
    return (pl.col("close") / pl.col("close").shift(h)).log()


def price_features() -> list[pl.Expr]:
    """~40 causal expressions over a daily OHLCV frame (single asset, sorted)."""
    sigma = pl.col("vol_ewma_21d")
    exprs: list[pl.Expr] = []

    # momentum, raw and vol-adjusted (the strongest documented family)
    for h in MOM_HORIZONS:
        exprs.append(_logret(h).alias(f"ret_{h}d"))
        exprs.append((_logret(h) / (sigma * (h**0.5))).alias(f"mom_voladj_{h}d"))

    # RSI (Wilder) at three speeds
    r1 = pl.col("close").diff()
    for n in (7, 14, 30):
        gain = r1.clip(lower_bound=0).ewm_mean(alpha=1 / n)
        loss = (-r1).clip(lower_bound=0).ewm_mean(alpha=1 / n)
        exprs.append((100 - 100 / (1 + gain / (loss + 1e-12))).alias(f"rsi_{n}"))

    # MACD histogram, price-normalized
    ema12 = pl.col("close").ewm_mean(span=12)
    ema26 = pl.col("close").ewm_mean(span=26)
    macd = ema12 - ema26
    exprs.append(((macd - macd.ewm_mean(span=9)) / pl.col("close")).alias("macd_hist_norm"))

    # Bollinger %B and bandwidth (20d, 2 sigma)
    ma20 = pl.col("close").rolling_mean(20)
    sd20 = pl.col("close").rolling_std(20)
    exprs.append(((pl.col("close") - (ma20 - 2 * sd20)) / (4 * sd20 + 1e-12)).alias("bb_pctb"))
    exprs.append((4 * sd20 / (ma20 + 1e-12)).alias("bb_bandwidth"))

    # trend/level context (ratios, never raw levels)
    for w in (50, 200):
        exprs.append((pl.col("close") / pl.col("close").rolling_mean(w) - 1).alias(f"px_vs_ma{w}"))
    roll_max = pl.col("close").rolling_max(252)
    exprs.append((pl.col("close") / roll_max - 1).alias("drawdown_252d"))

    # range structure
    exprs.append(
        ((pl.col("close") - pl.col("low")) / (pl.col("high") - pl.col("low") + 1e-12)).alias(
            "close_in_range"
        )
    )
    exprs.append(((pl.col("high") / pl.col("low")).log()).alias("range_1d"))

    # volatility family + regime ratios
    exprs.append(parkinson(21))
    exprs.append(garman_klass(21))
    exprs.append(ewma_vol(5))
    exprs.append((ewma_vol(5) / (ewma_vol(63) + 1e-12)).alias("vol_ratio_5_63"))
    exprs.append(pl.col("vol_ewma_21d").rolling_std(21).alias("vol_of_vol_21d"))
    # vol regime as z vs trailing year (a full-history rank would be lookahead)
    v = pl.col("vol_ewma_21d")
    exprs.append(
        ((v - v.rolling_mean(252)) / (v.rolling_std(252) + 1e-12)).alias("vol_z_252d")
    )

    # volume / order flow
    vz_mean = pl.col("volume").rolling_mean(21)
    vz_std = pl.col("volume").rolling_std(21)
    exprs.append(((pl.col("volume") - vz_mean) / (vz_std + 1e-12)).alias("volume_z_21d"))
    taker_imb = (2 * pl.col("taker_buy_base") - pl.col("volume")) / (pl.col("volume") + 1e-12)
    exprs.append(taker_imb.alias("taker_imbalance"))
    exprs.append(taker_imb.rolling_mean(5).alias("taker_imbalance_5d"))
    amihud = _logret(1).abs() / (pl.col("quote_volume") + 1.0)
    exprs.append((amihud.rolling_mean(21) * 1e9).alias("amihud_21d"))

    return exprs


def add_price_features(daily: pl.DataFrame) -> pl.DataFrame:
    """daily: sorted single-asset daily bars. Adds vol_ewma_21d first because
    other expressions reference it as a column."""
    if "asset" in daily.columns and daily["asset"].n_unique() > 1:
        raise ValueError(
            "add_price_features is single-asset: rolling windows would cross "
            "asset boundaries on a multi-asset frame"
        )
    out = daily.sort("date").with_columns(ewma_vol(21))
    return out.with_columns(price_features())
