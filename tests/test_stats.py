"""Overfitting statistics: analytic sanity + behavioral properties.
Published reference vectors get appended when the research agent delivers
them (they must match to 4 decimals)."""

import numpy as np
import pytest

from cryptoacademy.validation.stats import (
    dsr,
    expected_max_sharpe,
    min_track_record_length,
    pbo_cscv,
    psr,
    sharpe,
)


def test_psr_of_zero_sharpe_is_half():
    assert psr(0.0, t=1000) == pytest.approx(0.5)


def test_psr_increases_with_track_length():
    assert psr(0.1, t=2000) > psr(0.1, t=200)


def test_psr_negative_skew_fat_tails_penalized():
    base = psr(0.1, t=500, skew=0.0, kurt=3.0)
    ugly = psr(0.1, t=500, skew=-1.0, kurt=8.0)
    assert ugly < base


def test_expected_max_sharpe_grows_with_trials():
    v = 0.02
    e10 = expected_max_sharpe(10, v)
    e100 = expected_max_sharpe(100, v)
    e1000 = expected_max_sharpe(1000, v)
    assert 0 < e10 < e100 < e1000


def test_dsr_deflates_with_search_size():
    sr, t = 0.15, 1000
    assert dsr(sr, t, n_trials=1, var_trials=0.02) > dsr(sr, t, n_trials=500, var_trials=0.02)


def test_min_trl_infinite_when_no_edge():
    assert min_track_record_length(0.05, 0.05, 0.0, 3.0) == float("inf")


def test_min_trl_reasonable_magnitude():
    # daily SR 0.1 vs 0: needs on the order of a few hundred days at 95%
    t = min_track_record_length(0.1, 0.0, 0.0, 3.0, confidence=0.95)
    assert 200 < t < 400


def test_pbo_high_for_pure_noise():
    rng = np.random.default_rng(2)
    m = rng.normal(0, 0.01, size=(600, 30))  # 30 skill-less strategies
    result = pbo_cscv(m, n_blocks=8)
    assert result["pbo"] > 0.35  # IS winner is noise -> OOS rank ~uniform


def test_pbo_low_for_one_true_skill():
    rng = np.random.default_rng(3)
    m = rng.normal(0, 0.01, size=(600, 30))
    m[:, 7] += 0.004  # one genuinely good strategy (SR ~0.4 per period)
    result = pbo_cscv(m, n_blocks=8)
    assert result["pbo"] < 0.1


def test_sharpe_zero_variance_safe():
    assert sharpe(np.zeros(50)) == 0.0
