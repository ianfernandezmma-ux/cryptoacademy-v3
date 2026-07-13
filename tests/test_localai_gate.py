"""The local AI (Ollama GPU model) must never run unless the run was explicitly
authorized via CRYPTOACADEMY_ENABLE_LOCAL_AI. This machine is shared with
gaming; automatic GPU use is forbidden. These tests are the CI guarantee that
every Ollama entry point is gated and refuses by default."""

import pytest

from cryptoacademy import localai
from cryptoacademy.localai import ENABLE_ENV, LocalAIDisabled


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed("test op")


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "Yes", "on", " on "])
def test_enabled_values(monkeypatch, val):
    monkeypatch.setenv(ENABLE_ENV, val)
    assert localai.local_ai_enabled()
    localai.ensure_local_ai_allowed()  # must not raise


@pytest.mark.parametrize("val", ["", "0", "false", "no", "off", "bogus"])
def test_disabled_values(monkeypatch, val):
    monkeypatch.setenv(ENABLE_ENV, val)
    assert not localai.local_ai_enabled()
    with pytest.raises(LocalAIDisabled):
        localai.ensure_local_ai_allowed()


def test_scoring_generate_gated(monkeypatch):
    """_generate must refuse (before any network call) when the AI is disabled."""
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    from cryptoacademy.news import scoring

    with pytest.raises(LocalAIDisabled):
        scoring._generate("hello", {"type": "object"})


def test_scoring_embed_gated(monkeypatch):
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    from cryptoacademy.news import scoring

    with pytest.raises(LocalAIDisabled):
        scoring.embed(["hello"])


def test_regime_classify_gated(monkeypatch):
    """The gate fires before the http client is ever touched, so a dummy client
    (None) is safe here."""
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    from cryptoacademy.news import regime

    with pytest.raises(LocalAIDisabled):
        regime.classify_day(None, ["alpha beta gamma"], [])
