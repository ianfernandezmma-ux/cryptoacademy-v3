"""Publication-clock rules (audit C-1/M-1/M-2): business days, holidays, DST."""

from datetime import UTC, datetime

import numpy as np
import polars as pl

from cryptoacademy.data.macro_onchain import fred_published_at
from cryptoacademy.features.derivatives import funding_daily
from cryptoacademy.features.resample import to_daily


def test_friday_h15_value_not_knowable_before_monday_evening():
    """C-1: Friday DFII10 releases the NEXT BUSINESS day (Monday) 16:15 ET."""
    friday = datetime(2026, 7, 10)  # a plain Friday
    pub = fred_published_at(friday, busdays=1, et_time="16:15")
    assert pub.weekday() == 0  # Monday
    assert pub > datetime(2026, 7, 13, 20, 0, tzinfo=UTC)  # after 16:00 ET


def test_holiday_pushes_release_to_next_business_day():
    """July 3 2026 is Independence Day observed (Jul 4 = Saturday)."""
    thursday = datetime(2026, 7, 2)
    pub = fred_published_at(thursday, busdays=1, et_time="16:15")
    assert pub.date().isoformat() == "2026-07-06"  # skips Fri (holiday) + weekend


def test_dst_winter_vs_summer_utc_offsets_differ():
    """M-2: 16:15 ET is 20:15 UTC in July but 21:15 UTC in January."""
    summer = fred_published_at(datetime(2026, 7, 7), 1, "16:15")
    winter = fred_published_at(datetime(2026, 1, 6), 1, "16:15")
    assert summer.hour == 20
    assert winter.hour == 21


def test_walcl_wednesday_dated_released_thursday():
    """M-1: H.4.1 Wednesday-dated data releases Thursday 16:30 ET, not +8d."""
    wednesday = datetime(2026, 7, 8)
    pub = fred_published_at(wednesday, busdays=1, et_time="16:30")
    assert pub.date().isoformat() == "2026-07-09"


def test_funding_at_midnight_belongs_to_that_day():
    """A funding stamp at exactly D 00:00 lands in day D (invisible at the
    D-midnight decision, visible at D+1)."""
    f = pl.DataFrame(
        {
            "funding_time": [
                datetime(2026, 7, 2, 0, 0, tzinfo=UTC),
                datetime(2026, 7, 2, 8, 0, tzinfo=UTC),
            ],
            "funding_rate": [0.0001, 0.0002],
        }
    )
    daily = funding_daily(f)
    assert len(daily) == 1
    assert daily["date"][0] == datetime(2026, 7, 2, 0, 0, tzinfo=UTC)
    assert abs(daily["funding_1d"][0] - 0.0003) < 1e-12


def test_daily_bar_unaffected_by_next_day_hours():
    """to_daily: tampering hours of day D+1 must not change bar D."""
    from datetime import timedelta

    rows = []
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    for h in range(48):
        rows.append(
            {
                "open_time": t0 + timedelta(hours=h),
                "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                "volume": 10.0, "quote_volume": 1000.0, "trades": 5,
                "taker_buy_base": 6.0, "taker_buy_quote": 600.0,
            }
        )
    df = pl.DataFrame(rows)
    base = to_daily(df)
    tampered = df.clone()
    tampered[30, "close"] = 500.0  # hour inside day 2
    tampered[30, "volume"] = 1e6
    out = to_daily(tampered)
    assert base.row(0) == out.row(0)  # day 1 untouched


def test_cusum_survives_nan_gap():
    """M-9: a NaN close must not poison the CUSUM accumulators forever."""
    from cryptoacademy.labels.core import cusum_events

    close = np.full(200, 100.0)
    for i in range(1, 200):
        close[i] = close[i - 1] * 1.002
    close[50] = np.nan
    ev = cusum_events(close, np.full(200, 0.01))
    assert len(ev) > 20  # still fires after the gap
    assert ev.max() > 60


def test_event_window_containing_gap_is_dropped():
    from cryptoacademy.labels.core import TripleBarrierConfig, triple_barrier

    high = np.full(200, 100.0)
    low = high.copy()
    close = high.copy()
    close[60] = np.nan
    cfg = TripleBarrierConfig(horizon_bars=48)
    ev = triple_barrier(high, low, close, np.array([30]), np.full(200, 0.01), cfg)
    assert len(ev) == 0
