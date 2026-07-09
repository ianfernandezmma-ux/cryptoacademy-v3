"""Feature matrix assembly — the single place where time discipline is applied.

Decision spine: one row per (asset, decision_day D at 00:00 UTC).
Join rules, in order of strictness:
  - Market daily bars: the bar for calendar day D-1 (fully known at D 00:00).
    Joining bar D-1 to decision D IS the global anti-lookahead shift.
  - Derivatives daily aggregates: same D-1 convention.
  - Published sources (on-chain, macro, stablecoins, ETF flows, F&G, wiki):
    as-of BACKWARD join on published_at_utc <= D, with per-source staleness
    caps; a feature's age is emitted alongside it (staleness is signal).
  - News aggregates: already keyed by decision_day with usable_at discipline
    inside features/news.py; joined 1:1.
"""

from __future__ import annotations

import logging

import polars as pl

from cryptoacademy import config
from cryptoacademy.features.derivatives import dvol_daily, funding_daily, metrics_daily
from cryptoacademy.features.news import abnormal_attention, gdelt_era_daily, llm_era_daily
from cryptoacademy.features.price import add_price_features
from cryptoacademy.features.resample import to_daily

log = logging.getLogger(__name__)

STALENESS_CAP_H = {"macro": 24 * 10, "onchain": 48, "stablecoins": 48, "etf": 24 * 5}


def _decision_spine(daily_bars: pl.DataFrame) -> pl.DataFrame:
    """Decision day D uses the completed bar of D-1: spine = bar date + 1d."""
    return daily_bars.with_columns(
        (pl.col("date") + pl.duration(days=1)).alias("decision_day")
    )


def _asof_published(
    spine: pl.DataFrame,
    source: pl.DataFrame,
    value_cols: list[str],
    prefix: str,
    cap_hours: int,
) -> pl.DataFrame:
    """Backward as-of join on published_at_utc with staleness cap + age column."""
    src = (
        source.sort("published_at_utc")
        .select(["published_at_utc", *value_cols])
        .rename({c: f"{prefix}_{c}" for c in value_cols})
    )
    joined = spine.sort("decision_day").join_asof(
        src, left_on="decision_day", right_on="published_at_utc", strategy="backward"
    )
    age = (
        (pl.col("decision_day") - pl.col("published_at_utc")).dt.total_minutes() / 60.0
    ).alias(f"{prefix}_age_h")
    joined = joined.with_columns(age)
    too_old = pl.col(f"{prefix}_age_h") > cap_hours
    return joined.with_columns(
        [
            pl.when(too_old).then(None).otherwise(pl.col(f"{prefix}_{c}")).alias(f"{prefix}_{c}")
            for c in value_cols
        ]
    ).drop("published_at_utc")


def build_matrix(asset: str) -> pl.DataFrame:
    meta = config.load_assets()[asset]
    sym = meta["spot_symbol"]

    bars_1h = pl.read_parquet(
        config.RAW_DIR / "klines" / asset / "spot" / f"{sym}_1h.parquet"
    )
    daily = add_price_features(to_daily(bars_1h))
    spine = _decision_spine(daily)

    # derivatives (perp market)
    funding = funding_daily(
        pl.read_parquet(config.RAW_DIR / "funding" / asset / f"{sym}_funding.parquet")
    ).with_columns((pl.col("date") + pl.duration(days=1)).alias("decision_day"))
    spine = spine.join(funding.drop("date"), on="decision_day", how="left")

    metrics_path = config.RAW_DIR / "metrics" / asset / f"{sym}_metrics.parquet"
    if metrics_path.exists():
        metrics = metrics_daily(pl.read_parquet(metrics_path)).with_columns(
            (pl.col("date") + pl.duration(days=1)).alias("decision_day")
        )
        spine = spine.join(metrics.drop("date"), on="decision_day", how="left")

    dvol_path = config.RAW_DIR / "options" / f"{asset}_dvol.parquet"
    if dvol_path.exists():
        dvol = dvol_daily(pl.read_parquet(dvol_path)).with_columns(
            (pl.col("date") + pl.duration(days=1)).alias("decision_day")
        )
        spine = spine.join(dvol.drop("date"), on="decision_day", how="left")
        # variance risk premium: implied (annualized) vs realized (daily units)
        spine = spine.with_columns(
            (pl.col("iv_30d") / (365**0.5) - pl.col("vol_ewma_21d")).alias("vrp_daily")
        )

    # published sources (as-of on knowledge time)
    onchain = pl.read_parquet(config.RAW_DIR / "onchain" / "coinmetrics.parquet").filter(
        pl.col("asset") == meta["coinmetrics_id"]
    )
    oc_cols = ["AdrActCnt", "TxCnt", "HashRate", "CapMrktCurUSD", "CapMVRVCur"]
    spine = _asof_published(spine, onchain, oc_cols, "oc", STALENESS_CAP_H["onchain"])

    macro = pl.read_parquet(config.RAW_DIR / "macro" / "fred.parquet")
    for series in macro["series"].unique().to_list():
        sub = macro.filter(pl.col("series") == series)
        spine = _asof_published(
            spine, sub, ["value"], f"macro_{series.lower()}", STALENESS_CAP_H["macro"]
        )

    stab = pl.read_parquet(config.RAW_DIR / "stablecoins" / "stablecoins.parquet")
    total = stab.filter(pl.col("series") == "total_usd")
    spine = _asof_published(spine, total, ["value"], "stable_total", STALENESS_CAP_H["stablecoins"])

    etf_path = config.RAW_DIR / "etf_flows" / "farside.parquet"
    if etf_path.exists():
        etf = (
            pl.read_parquet(etf_path)
            .filter(pl.col("asset") == asset)
            .group_by("published_at_utc")
            .agg(pl.col("flow_musd").sum().alias("flow_total_musd"))
        )
        spine = _asof_published(spine, etf, ["flow_total_musd"], "etf", STALENESS_CAP_H["etf"])

    fng = pl.read_parquet(config.RAW_DIR / "sentiment" / "fear_greed.parquet").with_columns(
        # index for day D posts ~00:00 UTC of D; usable next decision (D+1)
        (pl.col("date") + pl.duration(hours=1)).alias("published_at_utc")
    )
    spine = _asof_published(spine, fng, ["fng_value"], "fng", 72)

    # news (both eras), already decision-day keyed
    news_frames = [df for df in (gdelt_era_daily(asset), llm_era_daily(asset)) if not df.is_empty()]
    if news_frames:
        news = pl.concat(news_frames, how="diagonal").sort("decision_day")
        news = abnormal_attention(news)
        spine = spine.join(news.drop("asset"), on="decision_day", how="left")

    spine = spine.with_columns(pl.lit(asset).alias("asset"))
    dest = config.DATA_DIR / "features"
    dest.mkdir(parents=True, exist_ok=True)
    spine.write_parquet(dest / f"matrix_{asset}.parquet")
    log.info(
        "%s matrix: %d rows x %d cols, %s -> %s",
        asset, len(spine), len(spine.columns),
        spine["decision_day"].min(), spine["decision_day"].max(),
    )
    return spine
