"""Triple-barrier / CUSUM / weights — tests against the known-bug checklist."""

import numpy as np
import polars as pl

from cryptoacademy.labels.core import (
    TripleBarrierConfig,
    concurrency,
    cusum_events,
    daily_vol_on_hourly,
    sample_weights,
    triple_barrier,
)

CFG = TripleBarrierConfig(pt_mult=2.0, sl_mult=2.0, horizon_bars=48, min_trgt=1e-6)


def _flat(n: int, price: float = 100.0):
    close = np.full(n, price)
    return close.copy(), close.copy(), close.copy()  # high, low, close


def test_upper_barrier_hit():
    high, low, close = _flat(200)
    sigma = np.full(200, 0.01)
    trgt = 0.01 * np.sqrt(48 / 24)  # horizon-scaled
    up_price = 100 * (1 + 2 * trgt)
    high[60] = up_price + 0.01  # wick touches upper at bar 60
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG)
    assert ev["label"].to_list() == [1]
    assert ev["touch"].to_list() == ["up"]
    assert ev["t1_idx"].to_list() == [60]


def test_lower_barrier_hit_via_low_wick():
    high, low, close = _flat(200)
    sigma = np.full(200, 0.01)
    trgt = 0.01 * np.sqrt(2)
    low[55] = 100 * (1 - 2 * trgt) - 0.01
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG)
    assert ev["label"].to_list() == [-1]
    assert ev["touch"].to_list() == ["down"]


def test_double_touch_resolves_pessimistically():
    high, low, close = _flat(200)
    sigma = np.full(200, 0.01)
    trgt = 0.01 * np.sqrt(2)
    high[52] = 100 * (1 + 2 * trgt) + 1
    low[52] = 100 * (1 - 2 * trgt) - 1
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG)
    assert ev["label"].to_list() == [-1]  # stop-loss wins the tie


def test_decision_bar_own_wick_is_ignored():
    """Bug class #3: the entry bar's high/low happened before entry."""
    high, low, close = _flat(200)
    sigma = np.full(200, 0.01)
    trgt = 0.01 * np.sqrt(2)
    high[50] = 100 * (1 + 2 * trgt) + 5  # huge wick ON the event bar itself
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG)
    assert ev["touch"].to_list() == ["vertical"]  # not an 'up' touch


def test_event_past_data_end_is_dropped_not_truncated():
    high, low, close = _flat(100)
    sigma = np.full(100, 0.01)
    ev = triple_barrier(high, low, close, np.array([80]), sigma, CFG)  # 80+48 > 99
    assert len(ev) == 0


def test_vertical_label_sign_and_zero_conventions():
    high, low, close = _flat(200)
    close[98] = 100.4  # small drift up by vertical bar (event 50 + H 48)
    for i in range(51, 99):
        close[i] = 100.2
        high[i] = 100.3
        low[i] = 100.1
    sigma = np.full(200, 0.01)
    ev_sign = triple_barrier(high, low, close, np.array([50]), sigma, CFG)
    assert ev_sign["label"].to_list() == [1]
    cfg0 = TripleBarrierConfig(pt_mult=2, sl_mult=2, horizon_bars=48, vertical_label="zero")
    ev_zero = triple_barrier(high, low, close, np.array([50]), sigma, cfg0)
    assert ev_zero["label"].to_list() == [0]


def test_meta_label_binary():
    high, low, close = _flat(200)
    sigma = np.full(200, 0.01)
    trgt = 0.01 * np.sqrt(2)
    high[60] = 100 * (1 + 2 * trgt) + 0.01
    # primary said LONG -> profit barrier hit -> meta 1
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG, side=np.array([1]))
    assert ev["label"].to_list() == [1]
    # primary said SHORT -> the same up-move is the short's stop -> meta 0
    ev = triple_barrier(high, low, close, np.array([50]), sigma, CFG, side=np.array([-1]))
    assert ev["label"].to_list() == [0]


def test_cusum_fires_on_cumulative_drift_and_resets():
    close = np.full(300, 100.0)
    for i in range(1, 300):
        close[i] = close[i - 1] * 1.002  # +0.2% per bar
    thr = np.full(300, 0.01)  # fires every ~5 bars
    ev = cusum_events(close, thr)
    # r = ln(1.002) ~ 0.001998 per bar -> fires every 6th bar -> ~49 events
    assert 45 <= len(ev) <= 55
    assert np.all(np.diff(ev) >= 5)  # reset spacing


def test_sigma_is_causal():
    """Bug class #1: tampering the future must not change past sigma."""
    rng = np.random.default_rng(3)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 5000)))
    s1 = daily_vol_on_hourly(close, span_days=2, min_days=1)
    tampered = close.copy()
    tampered[-1] *= 3.0
    s2 = daily_vol_on_hourly(tampered, span_days=2, min_days=1)
    np.testing.assert_allclose(s1[:-1], s2[:-1])


def test_concurrency_and_uniqueness():
    events = pl.DataFrame({"t0_idx": [0, 5], "t1_idx": [10, 15], "label": [1, -1]})
    c = concurrency(events, 20)
    assert c[0] == 1 and c[7] == 2 and c[12] == 1 and c[16] == 0
    close = np.linspace(100, 110, 20)
    w = sample_weights(events, close, last_weight=0.75)
    assert w["uniqueness"].to_list()[0] < 1.0  # overlap reduces uniqueness
    # newest event's decay factor is exactly 1, older one >= last_weight
    decays = w.sort("t1_idx")["w_decay"].to_list()
    assert abs(decays[-1] - 1.0) < 1e-9
    assert decays[0] >= 0.75 - 1e-9
