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


def test_expected_max_sharpe_closed_form_n2():
    """N=2, V=1: E = (1-g)*invPhi(1/2) + g*invPhi(1 - 1/(2e)) = g*invPhi(0.81606)."""
    from statistics import NormalDist

    expected = 0.5772156649015329 * NormalDist().inv_cdf(1 - 1 / (2 * np.e))
    assert expected_max_sharpe(2, 1.0) == pytest.approx(expected, abs=1e-12)
    assert expected == pytest.approx(0.5197, abs=2e-4)  # hand-computed pin


def test_pbo_rejects_odd_blocks_and_tiny_t():
    m = np.random.default_rng(0).normal(size=(100, 5))
    with pytest.raises(ValueError):
        pbo_cscv(m, n_blocks=7)
    with pytest.raises(ValueError):
        pbo_cscv(m[:20], n_blocks=16)


def test_pbo_ties_use_midrank_not_bottom():
    """All-identical strategies: winner must rank mid, not bottom (PBO ~0.5
    boundary, not 1.0)."""
    m = np.tile(np.random.default_rng(4).normal(0, 0.01, size=(200, 1)), (1, 10))
    result = pbo_cscv(m, n_blocks=4)
    # midrank of a 10-way tie -> omega = 5.5/11 = 0.5 exactly -> logit 0
    assert result["mean_logit"] == pytest.approx(0.0, abs=1e-9)


# ---- published reference vectors (cross-verified: pypbo tests, the
# ---- Bailey & Lopez de Prado papers, rubenbriones/Probabilistic-Sharpe-Ratio)


def test_vector_expected_max_of_100_standard_normals():
    """pypbo: EVT approximation for N=100 unit-variance trials."""
    assert expected_max_sharpe(100, 1.0) == pytest.approx(2.5306028932016846, abs=1e-9)


def test_vector_psr_sharpe_frontier_paper():
    """PSR paper example: monthly SR 1.585/sqrt(12), T=24, skew -2.448,
    raw kurt 10.164 -> 0.913234... (pypbo full precision)."""
    sr = 1.585 / (12**0.5)
    assert psr(sr, t=24, skew=-2.448, kurt=10.164) == pytest.approx(0.9132343069, abs=1e-6)


def test_vector_psr_normal_returns():
    """Same paper, Normal-returns variant: PSR(0.458, 24, 0, 3) ~ 0.982."""
    assert psr(0.458, t=24, skew=0.0, kurt=3.0) == pytest.approx(0.982, abs=1e-3)


def test_vector_dsr_deflated_sharpe_paper():
    """DSR paper worked example: daily SR 2.5/sqrt(250), N=100 trials with
    V[SR]=0.5/250, T=1250, skew -3, raw kurt 10 -> 0.900397 ('90% chance').
    With N=46 the paper prints 0.9505."""
    sr = 2.5 / (250**0.5)
    assert dsr(sr, t=1250, n_trials=100, var_trials=0.5 / 250,
               skew=-3.0, kurt=10.0) == pytest.approx(0.9003968344, abs=1e-6)
    assert dsr(sr, t=1250, n_trials=46, var_trials=0.5 / 250,
               skew=-3.0, kurt=10.0) == pytest.approx(0.9505, abs=1e-4)


def test_vector_mintrl_sharpe_frontier_figure8():
    """pypbo pin of the PSR paper's Figure 8: monthly SR 3/sqrt(12) vs
    benchmark 2.5/sqrt(12), skew -0.72, raw kurt 5.78 -> 27.3529 years."""
    obs = min_track_record_length(
        3 / (12**0.5), 2.5 / (12**0.5), skew=-0.72, kurt=5.78, confidence=0.95
    )
    assert obs / 12 == pytest.approx(27.352920196040301, abs=1e-6)


def test_vector_mintrl_psr_paper_examples():
    """rubenbriones pins (PSR paper): monthly SRs vs 0 benchmark, 95%."""
    a = min_track_record_length(0.7079, 0.0, skew=-0.2250, kurt=2.9570)
    assert a / 12 == pytest.approx(0.7152, abs=1e-3)
    b = min_track_record_length(0.8183, 0.0, skew=-1.4455, kurt=7.0497)
    assert b / 12 == pytest.approx(1.1593, abs=1e-3)


def test_registry_identity_hash_distinguishes_model_and_horizon(tmp_path, monkeypatch):
    from cryptoacademy.validation import registry

    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "trials.jsonl")
    registry.log_trial("p4", "lgbm", "24h", {}, {"sr": 0.1})
    registry.log_trial("p4", "lgbm", "96h", {}, {"sr": 0.1})
    registry.log_trial("p4", "patchtst", "24h", {}, {"sr": 0.1})
    registry.log_trial("p4", "lgbm", "24h", {}, {"sr": 0.2})  # re-run, same identity
    assert registry.n_trials(phase="p4") == 3
    assert registry.n_trials(phase="p4", horizon="24h") == 2
    # registered-but-crashed trials still count
    registry.register_trial("p4", "lgbm", "24h", {"lr": 0.1})
    assert registry.n_trials(phase="p4") == 4
