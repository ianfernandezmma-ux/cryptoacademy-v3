"""B2 engine alignment guard (pre-run review, MAJOR finding #2): the deadliest
bug class for the one-shot evaluation is same-bar execution — held[t]*r[t]
instead of held[t-1]*r[t] — which the strategy-level prefix-invariance tests
cannot see. This test pins the caller-side alignment in run_config."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, r"C:\CryptoBot\src")

_spec = importlib.util.spec_from_file_location(
    "b2_evaluate", Path(__file__).parents[1] / "scripts" / "b2_evaluate.py"
)
b2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b2)


@pytest.fixture()
def zero_costs(monkeypatch):
    monkeypatch.setattr(b2, "FEE", 0.0)
    monkeypatch.setattr(b2, "SLIP", {"BTC": 0.0, "ETH": 0.0})


def _inputs(T: int, big_day: int):
    """Flat returns except one +10% BTC day; constant floor vols; no high-vol."""
    rets = {a: np.zeros(T) for a in b2.ASSETS}
    rets["BTC"][big_day] = 0.10
    vols = {a: np.full(T, 0.20) for a in b2.ASSETS}
    hv = {a: np.zeros(T, dtype=bool) for a in b2.ASSETS}
    mask = np.ones(T, dtype=bool)
    return rets, vols, hv, mask


def test_position_taken_at_close_k_does_not_earn_day_k(zero_costs):
    """Signal fires AT the close of the big day -> it must earn NOTHING.
    A same-bar bug would credit w * 10% on day k."""
    T, k = 12, 6
    rets, vols, hv, mask = _inputs(T, big_day=k)
    scalars = {a: np.zeros(T) for a in b2.ASSETS}
    scalars["BTC"][k] = 1.0  # decided at close of day k, held during day k+1
    out = b2.run_config(scalars, rets, vols, hv, mask)
    assert np.allclose(out["net_daily"], 0.0), "same-bar execution detected"


def test_position_taken_day_before_earns_exactly_that_day(zero_costs):
    T, k = 12, 6
    rets, vols, hv, mask = _inputs(T, big_day=k)
    scalars = {a: np.zeros(T) for a in b2.ASSETS}
    scalars["BTC"][k - 1] = 1.0  # decided at close k-1 -> earns day k
    out = b2.run_config(scalars, rets, vols, hv, mask)
    w = 1.0 * 0.12 * 0.5 / 0.20  # = 0.30 (floor vol, no caps binding)
    expected = np.zeros(T)
    expected[k] = w * 0.10
    np.testing.assert_allclose(out["net_daily"], expected, atol=1e-12)


def test_costs_charged_on_rebalance_land_next_day():
    T, k = 12, 6
    rets, vols, hv, mask = _inputs(T, big_day=999 % T)  # big day irrelevant here
    rets["BTC"][:] = 0.0
    scalars = {a: np.zeros(T) for a in b2.ASSETS}
    scalars["BTC"][k - 1] = 1.0  # one entry (cost) and one exit (cost)
    out = b2.run_config(scalars, rets, vols, hv, mask)
    w = 0.30
    side = b2.FEE + b2.SLIP["BTC"]
    expected = np.zeros(T)
    expected[k] = -w * side       # entry turnover at k-1 charged in day k
    expected[k + 1] = -w * side   # exit turnover at k charged in day k+1
    np.testing.assert_allclose(out["net_daily"], expected, atol=1e-12)
