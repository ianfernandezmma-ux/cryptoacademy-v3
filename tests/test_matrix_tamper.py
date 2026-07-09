"""Assembly-level tamper invariant (audit gap #9 — the one test that catches a
forgotten shift anywhere in the pipeline).

Build the full matrix from synthetic raw files, then tamper the LAST day of
every raw input (prices, funding, on-chain) and assert that every feature at
decision days STRICTLY BEFORE the tampered day is unchanged.
"""

import random
from datetime import UTC, datetime, timedelta

import polars as pl
import polars.testing as plt
import pytest

from cryptoacademy import config
from cryptoacademy.features import matrix as matrix_mod

N_DAYS = 60
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _write_raw(root, tamper: bool) -> None:
    rng = random.Random(11)
    rows = []
    price = 100.0
    for i in range(N_DAYS * 24):
        r = rng.gauss(0, 0.005)
        o = price
        c = price * (2.718281828 ** r)
        rows.append(
            {
                "open_time": T0 + timedelta(hours=i),
                "open": o, "high": max(o, c) * 1.001, "low": min(o, c) * 0.999,
                "close": c, "volume": 10.0, "quote_volume": 10.0 * c,
                "trades": 5, "taker_buy_base": 5.0, "taker_buy_quote": 5.0 * c,
            }
        )
        price = c
    klines = pl.DataFrame(rows)
    funding = pl.DataFrame(
        {
            "funding_time": [T0 + timedelta(hours=8 * i) for i in range(N_DAYS * 3)],
            "funding_rate": [rng.gauss(1e-4, 5e-5) for _ in range(N_DAYS * 3)],
        }
    )
    onchain = pl.DataFrame(
        {
            "asset": ["btc"] * N_DAYS,
            "date": [T0 + timedelta(days=i) for i in range(N_DAYS)],
            "AdrActCnt": [1e6 + rng.random() for _ in range(N_DAYS)],
            "TxCnt": [3e5] * N_DAYS,
            "HashRate": [5e8] * N_DAYS,
            "CapMrktCurUSD": [2e12] * N_DAYS,
            "CapMVRVCur": [2.0] * N_DAYS,
            "published_at_utc": [
                T0 + timedelta(days=i + 1, hours=3) for i in range(N_DAYS)
            ],
        }
    )
    if tamper:  # catastrophic fake LAST day in every source
        last_day_start = (N_DAYS - 1) * 24
        for h in range(24):
            klines[last_day_start + h, "close"] = 9999.0
            klines[last_day_start + h, "high"] = 10000.0
            klines[last_day_start + h, "volume"] = 1e9
        funding[len(funding) - 1, "funding_rate"] = 0.5
        onchain[N_DAYS - 1, "AdrActCnt"] = 1e12

    (root / "klines" / "BTC" / "spot").mkdir(parents=True, exist_ok=True)
    klines.write_parquet(root / "klines" / "BTC" / "spot" / "BTCUSDT_1h.parquet")
    (root / "funding" / "BTC").mkdir(parents=True, exist_ok=True)
    funding.write_parquet(root / "funding" / "BTC" / "BTCUSDT_funding.parquet")
    (root / "onchain").mkdir(parents=True, exist_ok=True)
    onchain.write_parquet(root / "onchain" / "coinmetrics.parquet")


@pytest.fixture()
def synthetic_env(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    monkeypatch.setattr(config, "RAW_DIR", raw)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "NEWS_DB_PATH", tmp_path / "missing.duckdb")
    monkeypatch.setattr(matrix_mod, "config", config)
    return raw


def test_tampering_last_day_never_changes_earlier_decisions(synthetic_env):
    _write_raw(synthetic_env, tamper=False)
    base = matrix_mod.build_matrix("BTC")

    _write_raw(synthetic_env, tamper=True)
    tampered = matrix_mod.build_matrix("BTC")

    tamper_day = T0 + timedelta(days=N_DAYS - 1)
    base_before = base.filter(pl.col("decision_day") <= tamper_day)
    tampered_before = tampered.filter(pl.col("decision_day") <= tamper_day)
    plt.assert_frame_equal(base_before, tampered_before)
    # sanity: the tamper DOES show up at the next decision day
    after_b = base.filter(pl.col("decision_day") > tamper_day)
    after_t = tampered.filter(pl.col("decision_day") > tamper_day)
    assert len(after_t) == len(after_b)
    if len(after_t):
        assert after_t["ret_1d"].to_list() != after_b["ret_1d"].to_list()
