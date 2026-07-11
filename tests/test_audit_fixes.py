"""Tests for the 2026-07-11 audit fixes: each one pins an invariant that a
confirmed finding showed was unguarded."""

from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import polars as pl
import pytest

from cryptoacademy import config

# ---------------------------------------------------------------- regime

def test_regime_smoothing_does_not_span_gaps():
    """3-day median must be DATE-windowed: values weeks apart across a series
    hole must not blend, and the delta must be nulled across gaps."""
    from cryptoacademy.news.regime import smoothed_regime_features

    regime = pl.DataFrame(
        {
            "date": [date(2025, 6, 12), date(2025, 6, 13), date(2025, 6, 14),
                     # 16-day hole (the real GDELT outage shape)
                     date(2025, 7, 1), date(2025, 7, 2)],
            "risk_appetite": [2, 2, 2, -2, -2],
            "crypto_stress": [0, 0, 0, 3, 3],
            "macro_stress": [0, 0, 0, 3, 3],
            "confidence": [0.9] * 5,
        }
    )
    out = smoothed_regime_features(regime)
    post_gap = out.filter(
        pl.col("decision_day") == datetime(2025, 7, 2, tzinfo=UTC)
    )
    # a row-based median would blend the pre-gap +2 values into this window
    assert post_gap["regime_crypto_stress"][0] == 3
    assert post_gap["regime_risk_appetite"][0] == -2
    # delta across the hole is meaningless -> null
    assert post_gap["regime_ra_delta"][0] is None
    # gap size is surfaced as a staleness signal
    assert post_gap["regime_gap_days"][0] == 17
    # decision-day keying: regime(D) usable at D+1
    assert out["decision_day"][0] == datetime(2025, 6, 13, tzinfo=UTC)


def test_regime_delta_kept_on_consecutive_days():
    from cryptoacademy.news.regime import smoothed_regime_features

    regime = pl.DataFrame(
        {
            "date": [date(2025, 1, 1), date(2025, 1, 2)],
            "risk_appetite": [0, 2],
            "crypto_stress": [1, 1],
            "macro_stress": [0, 0],
            "confidence": [0.8, 0.8],
        }
    )
    out = smoothed_regime_features(regime)
    assert out["regime_ra_delta"][1] == 2


# ---------------------------------------------------------------- anonymize

def test_anonymize_homonym_guards():
    from cryptoacademy.news.anonymize import anonymize

    # non-crypto senses must survive untouched
    for text in [
        "Scientists study warming near the Arctic Circle",
        "Google releases Gemini Ultra model to developers",
        "An avalanche of lawsuits hit the sector",
        "Compound interest explained for beginners",
        "Temperatures hit 40 Celsius in Madrid",
        "The rise of the digital nomad lifestyle",
    ]:
        anon, _ = anonymize(text)
        for token in ("EXCHANGE_J", "STABLECOIN_C", "CHAIN_E", "PROTOCOL_C", "LENDER_A"):
            assert token not in anon, f"{text!r} -> {anon!r}"

    # genuine crypto senses must still be anonymized
    anon, _ = anonymize("Gemini exchange wins New York trust license")
    assert "EXCHANGE_J" in anon
    anon, _ = anonymize("Avalanche launches new subnet for DeFi")
    assert "CHAIN_E" in anon
    anon, _ = anonymize("Celsius freezes withdrawals amid market crash")
    assert "LENDER_A" in anon


def test_anonymize_still_kills_hindsight_entities():
    from cryptoacademy.news.anonymize import anonymize

    anon, hits = anonymize("FTX collapses as Alameda balance sheet leaks; SBF resigns")
    assert "FTX" not in anon and "Alameda" not in anon and "SBF" not in anon
    assert hits >= 3


# ---------------------------------------------------------------- telegram

def test_telegram_escapes_html(monkeypatch):
    from cryptoacademy.notify import telegram

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        captured.update(json)
        return FakeResp()

    monkeypatch.setattr(telegram, "env", lambda k, d=None: "x")
    monkeypatch.setattr(telegram.httpx, "post", fake_post)
    ok = telegram.send("error: <Response [403]> & more")
    assert ok
    assert "<" not in captured["text"] and "&lt;" in captured["text"]


# ---------------------------------------------------------------- gdelt

def test_harvest_day_leaves_partial_day_pending(monkeypatch, tmp_path):
    """A day with non-404 permanent failures must NOT be written (file
    existence = day done would make the partial day permanent)."""
    from cryptoacademy.news import gdelt

    monkeypatch.setattr(config, "RAW_DIR", tmp_path)

    class FakeClient:
        def get(self, url):
            raise OSError("network down")

    day = datetime(2026, 3, 1, tzinfo=UTC)
    n = gdelt.harvest_day(FakeClient(), day)
    assert n == 0
    assert not (tmp_path / "gdelt" / "2026" / "gkg_20260301.parquet").exists()


def test_harvest_day_writes_clean_404_day(monkeypatch, tmp_path):
    """Pure-404 days (genuine GDELT outages) still produce the 0-row parquet
    so they are not retried forever."""
    from cryptoacademy.news import gdelt

    monkeypatch.setattr(config, "RAW_DIR", tmp_path)

    class FakeResp:
        status_code = 404

    class FakeClient:
        def get(self, url):
            return FakeResp()

    day = datetime(2026, 3, 2, tzinfo=UTC)
    n = gdelt.harvest_day(FakeClient(), day)
    assert n == 0
    assert (tmp_path / "gdelt" / "2026" / "gkg_20260302.parquet").exists()


# ---------------------------------------------------------------- lockbox

def _write_minimal_frames(tmp_path, asset: str, t0s: list[datetime]):
    (tmp_path / "labels").mkdir(parents=True, exist_ok=True)
    (tmp_path / "features").mkdir(parents=True, exist_ok=True)
    n = len(t0s)
    pl.DataFrame(
        {
            "t0_time": t0s,
            "t1_time": t0s,
            "label": [1] * n,
            "ret": [0.01] * n,
            "trgt": [0.02] * n,
            "touch": ["up"] * n,
            "t0_idx": list(range(n)),
            "t1_idx": list(range(n)),
            "uniqueness": [1.0] * n,
            "w_attrib": [1.0] * n,
            "w_decay": [1.0] * n,
            "sample_weight": [1.0] * n,
            "asset": [asset] * n,
            "barrier_mult": [1.5] * n,
            "cusum_k": [1.5] * n,
        }
    ).write_parquet(tmp_path / "labels" / f"labels_{asset}_24h.parquet")
    days = sorted({t.replace(hour=0, minute=0) for t in t0s})
    pl.DataFrame(
        {
            "decision_day": days,
            "feat_a": [0.5] * len(days),
            "asset": [asset] * len(days),
        }
    ).write_parquet(tmp_path / "features" / f"matrix_{asset}.parquet")


def test_lockbox_events_excluded_by_default(monkeypatch, tmp_path):
    from cryptoacademy.models.dataset import build_training_frame

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        config, "load_assets", lambda: {"btc": {}, "eth": {}}
    )
    t0s = [
        datetime(2025, 6, 1, 12, tzinfo=UTC),
        datetime(2025, 12, 31, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 0, tzinfo=UTC),   # lockbox
        datetime(2026, 6, 1, 12, tzinfo=UTC),  # lockbox
    ]
    for asset in ("btc", "eth"):
        _write_minimal_frames(tmp_path, asset, t0s)

    df, _ = build_training_frame("24h")
    assert len(df) == 4  # 2 assets x 2 pre-lockbox events
    assert df["t0_time"].max() < datetime(2026, 1, 1, tzinfo=UTC)

    df_all, _ = build_training_frame("24h", include_lockbox=True)
    assert len(df_all) == 8


# ---------------------------------------------------------------- permutation

def test_rotation_permutation_detects_real_alignment():
    from cryptoacademy.validation.regime_gates import (
        permutation_pvalue,
        spearman_rho,
    )

    rng = np.random.default_rng(7)
    # autocorrelated x, y = x + noise: aligned, p must be small
    x = np.cumsum(rng.normal(size=250))
    y = x + rng.normal(scale=0.5, size=250)
    rho = spearman_rho(x, y)
    p = permutation_pvalue(x, y, rho, 500, rng)
    assert p < 0.05


def test_rotation_permutation_not_fooled_by_shared_autocorrelation():
    """Two INDEPENDENT random walks are the classic spurious-correlation
    trap: an iid shuffle yields tiny p-values here; rotation must not."""
    from cryptoacademy.validation.regime_gates import (
        permutation_pvalue,
        spearman_rho,
    )

    rng = np.random.default_rng(11)
    rejections = 0
    for _ in range(10):
        x = np.cumsum(rng.normal(size=250))
        y = np.cumsum(rng.normal(size=250))
        rho = spearman_rho(x, y)
        if rho is None:
            continue
        p = permutation_pvalue(x, y, abs(rho), 200, rng)
        if p < 0.05:
            rejections += 1
    # iid shuffling rejects nearly always on random walks; rotation should
    # reject rarely (allow a little slack — it is still only ~250 points)
    assert rejections <= 3


# ---------------------------------------------------------------- variants

def test_generate_variants_requires_default_labels(monkeypatch, tmp_path):
    from cryptoacademy.labels.generate import generate_variants

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "load_assets", lambda: {"btc": {}})
    with pytest.raises(RuntimeError, match="default labels missing"):
        generate_variants()
