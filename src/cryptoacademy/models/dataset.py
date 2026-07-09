"""Training frame: labels (event rows) joined to the PIT feature matrix.

Alignment rule: an event at t0 (hourly) uses the feature row of the LAST
decision day at or before t0. Features at decision D are built from data
through D-1, so an event occurring during day D sees only information that
was knowable at D 00:00 UTC — strictly before the event.

Pooled across assets (asset_id categorical) to double the effective sample.
"""

from __future__ import annotations

import logging

import polars as pl

from cryptoacademy import config

log = logging.getLogger(__name__)

# raw daily-bar columns are NOT features (levels, unshifted magnitudes)
NON_FEATURE_COLS = {
    "date", "decision_day", "asset", "open", "high", "low", "close",
    "volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote",
    "n_bars", "incomplete_day",
    # label/bookkeeping columns after the join
    "t0_idx", "t1_idx", "label", "ret", "trgt", "touch", "t0_time", "t1_time",
    "uniqueness", "w_attrib", "w_decay", "sample_weight", "asset_id",
}


def build_training_frame(horizon: str) -> tuple[pl.DataFrame, list[str]]:
    """Returns (frame, feature_names). Frame columns: features + label, ret,
    sample_weight, t0_time, t1_time, asset, asset_id."""
    frames = []
    for i, asset in enumerate(config.load_assets()):
        labels = pl.read_parquet(config.DATA_DIR / "labels" / f"labels_{asset}_{horizon}.parquet")
        matrix = pl.read_parquet(config.DATA_DIR / "features" / f"matrix_{asset}.parquet")
        joined = (
            labels.sort("t0_time")
            .join_asof(
                matrix.sort("decision_day"),
                left_on="t0_time",
                right_on="decision_day",
                strategy="backward",
            )
            .with_columns(pl.lit(i).alias("asset_id"), pl.lit(asset).alias("asset"))
        )
        # PIT guard: the matched decision day must never be after the event
        bad = joined.filter(pl.col("decision_day") > pl.col("t0_time"))
        if len(bad):
            raise RuntimeError(f"asof join produced future decision days for {asset}")
        frames.append(joined)
    df = pl.concat(frames, how="diagonal_relaxed")  # column order differs per asset
    feature_names = sorted(
        c for c in df.columns
        if c not in NON_FEATURE_COLS and df[c].dtype in (pl.Float64, pl.Float32, pl.Int64,
                                                          pl.Int32, pl.Boolean, pl.UInt32)
    )
    n_null = {c: df[c].null_count() for c in feature_names}
    all_null = [c for c, n in n_null.items() if n == len(df)]
    if all_null:
        log.warning("dropping all-null feature columns: %s", all_null)
        feature_names = [c for c in feature_names if c not in all_null]
    log.info(
        "%s training frame: %d events, %d features, assets=%s",
        horizon, len(df), len(feature_names), df["asset"].unique().to_list(),
    )
    return df, feature_names
