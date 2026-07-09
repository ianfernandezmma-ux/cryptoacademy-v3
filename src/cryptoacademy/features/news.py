"""News -> daily features, dual-era (GDELT tone 2020-2026, LLM scores 2026+).

Design follows the evidence brief (docs/research): multi-half-life decayed
sentiment {1d,3d,7d}, same-weekday attention baseline (Da-Engelberg-Gao),
negative share, dispersion (highest-IC feature in Yang 2026), severity-weighted
event counts, novelty share, theme-bucket counts for the GDELT era, and an
era indicator. Price-report articles are excluded from sentiment aggregates
but kept in volume. Within-era normalization happens at matrix assembly.

PIT: an article enters the aggregate for decision day D only if its usable_at
(store rules for LLM era; GDELT file_time + 30 min for the backfill era)
is strictly before D 00:00 UTC. Lookback window 7 days; the decay does the
short-horizon weighting.
"""

from __future__ import annotations

import math
from datetime import timedelta

import polars as pl

from cryptoacademy import config

HALF_LIVES_H = {"h1d": 24.0, "h3d": 72.0, "h7d": 168.0}
LOOKBACK = timedelta(days=7)
GDELT_PIT_BUFFER = timedelta(minutes=30)

THEME_BUCKETS = {
    "macro": ["ECON_CENTRALBANK", "ECON_INTEREST", "ECON_INFLATION", "EPU_"],
    "regulation": ["REGULAT", "LEGISLAT", "TAX_", "SANCTION"],
    "hack": ["CYBER_ATTACK", "HACKER", "FRAUD", "CORRUPTION"],
    "solvency": ["BANKRUPT", "ECON_BUBBLE"],
}


def _explode_to_decision_days(df: pl.DataFrame, usable_col: str) -> pl.DataFrame:
    """Attach each article to every decision day D (00:00 UTC) with
    usable_at < D <= usable_at + LOOKBACK, and compute its age at D."""
    return (
        df.with_columns(
            pl.datetime_ranges(
                pl.col(usable_col).dt.truncate("1d") + pl.duration(days=1),
                pl.col(usable_col) + LOOKBACK,
                interval="1d",
                time_zone="UTC",
            ).alias("decision_day")
        )
        .filter(pl.col("decision_day").list.len() > 0)
        .explode("decision_day")
        .with_columns(
            ((pl.col("decision_day") - pl.col(usable_col)).dt.total_minutes() / 60.0).alias(
                "age_h"
            )
        )
        .filter(pl.col("age_h") > 0)
    )


def _decayed(value: pl.Expr, weight: pl.Expr, half_life_h: float) -> pl.Expr:
    lam = math.log(2.0) / half_life_h
    w = weight * (-lam * pl.col("age_h")).exp()
    return (value * w).sum() / (w.sum() + 1e-12)


def llm_era_daily(asset: str) -> pl.DataFrame:
    """Aggregate LLM-scored live articles into daily features for one asset."""
    import time

    import duckdb

    conn = None
    for attempt in range(6):  # collector holds the write lock ~5 min per run
        try:
            conn = duckdb.connect(str(config.NEWS_DB_PATH), read_only=True)
            break
        except duckdb.IOException:
            if attempt == 5:
                raise
            time.sleep(20)
    assert conn is not None
    rows = conn.execute(
        """
        SELECT a.published_at_utc, a.first_seen_at_utc, a.backfilled,
               s.sentiment, s.confidence, s.event_type, s.severity,
               s.is_price_report, s.duplicate_of IS NOT NULL AS is_dup
        FROM articles a JOIN article_scores s USING (url_hash, revision_no)
        WHERE s.model != 'dedup' OR s.duplicate_of IS NOT NULL
        """
    ).pl()
    conn.close()
    if rows.is_empty():
        return pl.DataFrame()
    from cryptoacademy.news.pit import usable_at

    rows = rows.with_columns(
        pl.struct(["published_at_utc", "first_seen_at_utc", "backfilled"])
        .map_elements(
            lambda r: usable_at(
                r["published_at_utc"], r["first_seen_at_utc"], r["backfilled"]
            ),
            return_dtype=pl.Datetime(time_zone="UTC"),
        )
        .alias("usable_at")
    )
    e = _explode_to_decision_days(rows, "usable_at")
    scored = e.filter(~pl.col("is_dup"))
    sent = scored.filter(~pl.col("is_price_report"))

    conf = pl.col("confidence").fill_null(0.5)
    aggs = [
        _decayed(pl.col("sentiment"), conf, hl).alias(f"news_sent_{k}")
        for k, hl in HALF_LIVES_H.items()
    ]
    aggs += [
        ((pl.col("sentiment") < -0.15).cast(pl.Float64) * conf).sum()
        .truediv(conf.sum() + 1e-12)
        .alias("news_neg_share"),
        pl.col("sentiment").std().alias("news_dispersion"),
        pl.col("severity").max().alias("news_max_severity"),
    ]
    sent_daily = sent.group_by("decision_day").agg(aggs)

    # severity-weighted event counts per type (24h window only)
    ev = (
        scored.filter(pl.col("age_h") <= 24)
        .group_by(["decision_day", "event_type"])
        .agg((pl.col("severity") * conf).sum().alias("evt_score"))
        .pivot(values="evt_score", index="decision_day", on="event_type")
        .rename(lambda c: c if c == "decision_day" else f"evt_{c}")
    )

    vol = (
        e.filter(pl.col("age_h") <= 24)
        .group_by("decision_day")
        .agg(
            pl.len().alias("news_count_24h"),
            (~pl.col("is_dup")).mean().alias("news_novel_share"),
        )
    )
    out = (
        sent_daily.join(vol, on="decision_day", how="full", coalesce=True)
        .join(ev, on="decision_day", how="left")
        .sort("decision_day")
        .with_columns(pl.lit(1).alias("era_llm"), pl.lit(asset).alias("asset"))
    )
    return out


def gdelt_era_daily(asset: str) -> pl.DataFrame:
    """Aggregate GDELT GKG rows into era-1 daily features for one asset."""
    files = sorted((config.RAW_DIR / "gdelt").glob("*/gkg_*.parquet"))
    frames = []
    for f in files:
        try:
            frames.append(pl.read_parquet(f))
        except Exception:  # truncated by a killed harvester: drop -> re-harvested
            import logging

            logging.getLogger(__name__).warning("corrupt gdelt file removed: %s", f)
            f.unlink(missing_ok=True)
    if not frames:
        return pl.DataFrame()
    # diagonal: files harvested before the `themes` column existed get nulls
    df = pl.concat(frames, how="diagonal_relaxed")
    if "themes" not in df.columns:
        df = df.with_columns(pl.lit(None, dtype=pl.String).alias("themes"))
    df = df.with_columns(pl.col("themes").fill_null(""))
    df = df.filter(pl.col("assets").str.contains(asset)).with_columns(
        (pl.col("file_time") + GDELT_PIT_BUFFER).alias("usable_at")
    )
    if df.is_empty():
        return pl.DataFrame()
    e = _explode_to_decision_days(df, "usable_at")

    one = pl.lit(1.0)
    aggs = [
        _decayed(pl.col("tone"), one, hl).alias(f"news_sent_{k}")
        for k, hl in HALF_LIVES_H.items()
    ]
    aggs += [
        (pl.col("tone") < -2.0).mean().alias("news_neg_share"),
        pl.col("tone").std().alias("news_dispersion"),
        pl.col("positive").mean().alias("gdelt_pos_mag"),
        pl.col("negative").mean().alias("gdelt_neg_mag"),
        pl.col("n_themes").mean().alias("gdelt_complexity"),
    ]
    daily = e.group_by("decision_day").agg(aggs)

    win24 = e.filter(pl.col("age_h") <= 24)
    theme_aggs = [pl.len().alias("news_count_24h")]
    for bucket, pats in THEME_BUCKETS.items():
        cond = pl.any_horizontal(
            [pl.col("themes").str.contains(p, literal=True) for p in pats]
        )
        theme_aggs.append(cond.cast(pl.Float64).mean().alias(f"gdelt_theme_{bucket}"))
    counts = win24.group_by("decision_day").agg(theme_aggs)

    return (
        daily.join(counts, on="decision_day", how="full", coalesce=True)
        .sort("decision_day")
        .with_columns(pl.lit(0).alias("era_llm"), pl.lit(asset).alias("asset"))
    )


def abnormal_attention(daily: pl.DataFrame, count_col: str = "news_count_24h") -> pl.DataFrame:
    """Da-Engelberg-Gao abnormal attention with a same-weekday baseline:
    log(1+N_t) - log(1+median of same weekday over trailing 8 weeks).
    Computed within-era by the caller; strictly causal (shift 1 week)."""
    return (
        daily.sort("decision_day")
        .with_columns(pl.col("decision_day").dt.weekday().alias("_dow"))
        .with_columns(
            pl.col(count_col)
            .shift(1)
            .rolling_median(8)
            .over("_dow")
            .alias("_baseline")
        )
        .with_columns(
            ((1 + pl.col(count_col)).log() - (1 + pl.col("_baseline")).log()).alias(
                "news_attn_abnormal"
            ),
            (
                pl.col(count_col)
                < pl.col(count_col).shift(1).rolling_quantile(0.1, window_size=8).over("_dow")
            ).alias("low_news_flag"),
        )
        .drop("_dow", "_baseline")
    )
