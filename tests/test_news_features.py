"""News aggregation: PIT window discipline, decay direction, attention baseline."""

from datetime import UTC, datetime, timedelta

import polars as pl

from cryptoacademy.features.news import (
    _decayed,
    _explode_to_decision_days,
    abnormal_attention,
)

D = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)


def test_article_maps_only_to_future_decision_days():
    df = pl.DataFrame(
        {"usable_at": [D - timedelta(hours=3)]},
        schema={"usable_at": pl.Datetime(time_zone="UTC")},
    )
    e = _explode_to_decision_days(df, "usable_at")
    days = e["decision_day"].to_list()
    assert min(days) == D  # first decision day AFTER usable_at
    assert all(d > D - timedelta(hours=3) for d in days)
    assert (e["age_h"] > 0).all()


def test_article_usable_exactly_at_midnight_goes_to_next_day():
    df = pl.DataFrame(
        {"usable_at": [D]}, schema={"usable_at": pl.Datetime(time_zone="UTC")}
    )
    e = _explode_to_decision_days(df, "usable_at")
    assert min(e["decision_day"].to_list()) == D + timedelta(days=1)


def test_decay_weights_recent_articles_more():
    df = pl.DataFrame({"s": [1.0, -1.0], "age_h": [1.0, 100.0]})
    v = df.select(_decayed(pl.col("s"), pl.lit(1.0), 24.0).alias("x"))["x"][0]
    # exact: (e^-l - e^-100l)/(e^-l + e^-100l) with l = ln2/24 -> 0.8916
    assert v > 0.85


def test_abnormal_attention_same_weekday_baseline():
    days = [D + timedelta(days=i) for i in range(9 * 7)]
    counts = [10.0 + (5.0 if d.weekday() == 0 else 0.0) for d in days]  # busy Mondays
    daily = pl.DataFrame(
        {"decision_day": days, "news_count_24h": counts},
        schema_overrides={"decision_day": pl.Datetime(time_zone="UTC")},
    )
    out = abnormal_attention(daily)
    tail = out.tail(14).filter(pl.col("news_attn_abnormal").is_not_null())
    # ordinary Mondays are NOT abnormal once the baseline is same-weekday
    assert tail["news_attn_abnormal"].abs().max() < 0.05
