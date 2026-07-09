"""Generic causality test for the feature layer.

Property: changing the LAST bar of the input must not change any feature value
on EARLIER bars. This catches full-sample statistics (global rank/mean),
centered windows and accidental negative shifts — the quiet killers.
"""

from datetime import UTC, datetime, timedelta

import polars as pl
import polars.testing as plt

from cryptoacademy.features.price import add_price_features
from cryptoacademy.features.resample import to_daily


def _synthetic_daily(n: int = 400, seed: int = 7) -> pl.DataFrame:
    import random

    rng = random.Random(seed)
    price = 100.0
    rows = []
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(n):
        r = rng.gauss(0, 0.03)
        o = price
        c = price * (2.718281828 ** r)
        hi = max(o, c) * (1 + abs(rng.gauss(0, 0.01)))
        lo = min(o, c) * (1 - abs(rng.gauss(0, 0.01)))
        vol = abs(rng.gauss(1000, 300)) + 1
        rows.append(
            {
                "date": t0 + timedelta(days=i),
                "open": o, "high": hi, "low": lo, "close": c,
                "volume": vol, "quote_volume": vol * c,
                "trades": int(vol), "taker_buy_base": vol * rng.random(),
                "taker_buy_quote": vol * c * 0.5, "n_bars": 24,
                "incomplete_day": False,
            }
        )
        price = c
    return pl.DataFrame(rows)


def test_future_bar_cannot_change_past_features():
    df = _synthetic_daily()
    base = add_price_features(df)

    tampered = df.clone()
    # a catastrophic fake final bar: +50% pump with huge volume
    tampered[-1, "close"] = df[-1, "close"] * 1.5
    tampered[-1, "high"] = df[-1, "high"] * 1.6
    tampered[-1, "volume"] = df[-1, "volume"] * 100
    tampered_out = add_price_features(tampered)

    plt.assert_frame_equal(base.head(len(base) - 1), tampered_out.head(len(base) - 1))


def test_resample_flags_incomplete_days():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    rows = []
    for d in range(2):
        hours = 24 if d == 0 else 20  # second day misses 4 bars (outage)
        for h in range(hours):
            rows.append(
                {
                    "open_time": t0 + timedelta(days=d, hours=h),
                    "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                    "volume": 10.0, "quote_volume": 1000.0, "trades": 5,
                    "taker_buy_base": 6.0, "taker_buy_quote": 600.0,
                }
            )
    daily = to_daily(pl.DataFrame(rows))
    assert daily["incomplete_day"].to_list() == [False, True]
    assert daily["volume"].to_list() == [240.0, 200.0]


def test_no_total_nan_columns():
    out = add_price_features(_synthetic_daily())
    tail = out.tail(50)  # after warmup, every feature must have values
    for col in out.columns:
        assert tail[col].null_count() < 50, f"column {col} is all-null after warmup"
