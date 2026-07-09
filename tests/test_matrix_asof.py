"""As-of join discipline: a value published AFTER decision time must be
invisible at that decision, visible at the next one; stale values get nulled."""

from datetime import UTC, datetime, timedelta

import polars as pl

from cryptoacademy.features.matrix import _asof_published

D = datetime(2026, 7, 2, 0, 0, tzinfo=UTC)


def _spine(days: int = 4) -> pl.DataFrame:
    return pl.DataFrame(
        {"decision_day": [D + timedelta(days=i) for i in range(days)]},
        schema={"decision_day": pl.Datetime(time_zone="UTC")},
    )


def test_value_published_one_hour_after_decision_is_invisible():
    src = pl.DataFrame(
        {
            "published_at_utc": [D + timedelta(hours=1)],  # 01:00 of decision day
            "value": [42.0],
        },
        schema_overrides={"published_at_utc": pl.Datetime(time_zone="UTC")},
    )
    out = _asof_published(_spine(), src, ["value"], "x", cap_hours=1000)
    vals = out["x_value"].to_list()
    assert vals[0] is None          # decision at D: not yet knowable
    assert vals[1] == 42.0          # decision at D+1: knowable


def test_stale_value_beyond_cap_is_nulled():
    src = pl.DataFrame(
        {"published_at_utc": [D - timedelta(days=10)], "value": [7.0]},
        schema_overrides={"published_at_utc": pl.Datetime(time_zone="UTC")},
    )
    out = _asof_published(_spine(), src, ["value"], "x", cap_hours=48)
    assert out["x_value"].to_list() == [None, None, None, None]
    assert out["x_age_h"][0] > 48


def test_age_column_reports_hours_since_publication():
    src = pl.DataFrame(
        {"published_at_utc": [D - timedelta(hours=6)], "value": [1.0]},
        schema_overrides={"published_at_utc": pl.Datetime(time_zone="UTC")},
    )
    out = _asof_published(_spine(1), src, ["value"], "x", cap_hours=100)
    assert out["x_age_h"][0] == 6.0
