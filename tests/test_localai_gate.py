"""The local AI (Ollama GPU model) must never start on its own. It may run
only while (a) Ian's persistent switch (data/local_ai.on, created ONLY by the
explicit `cryptoacademy ai on` command) is on and unexpired, or (b) the run
was explicitly authorized via CRYPTOACADEMY_ENABLE_LOCAL_AI. This machine is
shared with gaming; the default is OFF and nothing automatic may flip it.
These tests are the CI guarantee that every Ollama entry point is gated and
refuses by default."""

from datetime import UTC, datetime, timedelta

import pytest

from cryptoacademy import localai
from cryptoacademy.localai import ENABLE_ENV, LocalAIDisabled


@pytest.fixture(autouse=True)
def _isolated_switch(monkeypatch, tmp_path):
    """Point the persistent switch at a temp dir so tests never touch (or get
    polluted by) the real data/local_ai.on."""
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    monkeypatch.setattr(localai, "_flag_path", lambda: tmp_path / "local_ai.on")


def test_disabled_by_default():
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed("test op")


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "Yes", "on", " on "])
def test_env_enabled_values(monkeypatch, val):
    monkeypatch.setenv(ENABLE_ENV, val)
    assert localai.local_ai_enabled()
    localai.ensure_local_ai_allowed()  # must not raise


@pytest.mark.parametrize("val", ["", "0", "false", "no", "off", "bogus"])
def test_env_disabled_values(monkeypatch, val):
    monkeypatch.setenv(ENABLE_ENV, val)
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed()


def test_switch_on_off_roundtrip():
    localai.switch_on()
    assert localai.local_ai_enabled()
    localai.ensure_local_ai_allowed()  # must not raise
    assert "ON" in localai.switch_status()
    localai.switch_off()
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed()
    assert localai.switch_status() == "OFF"


def test_switch_with_future_expiry():
    localai.switch_on(hours=1)
    assert localai.local_ai_enabled()
    assert "ON until" in localai.switch_status()


def test_expired_switch_is_off():
    localai.switch_on(hours=1)
    expired = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    localai._flag_path().write_text(expired, encoding="utf-8")
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed()


def test_corrupt_flag_fails_closed():
    localai._flag_path().write_text("not-a-timestamp", encoding="utf-8")
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed()


def test_scoring_generate_gated():
    """_generate must refuse (before any network call) when the AI is off."""
    from cryptoacademy.news import scoring

    with pytest.raises(LocalAIDisabled):
        scoring._generate("hello", {"type": "object"})


def test_scoring_embed_gated():
    from cryptoacademy.news import scoring

    with pytest.raises(LocalAIDisabled):
        scoring.embed(["hello"])


def test_regime_classify_gated():
    """The gate fires before the http client is ever touched, so a dummy client
    (None) is safe here."""
    from cryptoacademy.news import regime

    with pytest.raises(LocalAIDisabled):
        regime.classify_day(None, ["alpha beta gamma"], [])
