"""Central authorization gate for the local AI (the Ollama GPU model).

This machine is also used for gaming, so the local LLM must NEVER start on its
own. Every code path that contacts Ollama — news scoring, dedup embeddings,
risk-regime classification — calls :func:`ensure_local_ai_allowed` first.

Policy (updated 2026-07-15, Ian's decision): the local AI is allowed to run —
including from scheduled tasks — but ONLY while Ian's manual switch is on.
Nothing ever turns the switch on automatically, so it can never interrupt a
game. Two ways to authorize:

1. **The persistent switch** (preferred): ``cryptoacademy ai on`` creates the
   flag file ``data/local_ai.on``; ``cryptoacademy ai off`` removes it. While
   the flag exists (and has not expired), every gated entry point may run.
   ``ai on --hours N`` writes an expiry so a forgotten switch turns itself
   off. The flag is created ONLY by this explicit command (or an equivalent
   user-facing toggle, e.g. the bot UI) — never by any scheduled or automatic
   path.
2. **One-process override** (legacy, still supported): set
   ``CRYPTOACADEMY_ENABLE_LOCAL_AI=1`` for a single command; it vanishes when
   the process exits::

       $env:CRYPTOACADEMY_ENABLE_LOCAL_AI = '1'
       .venv\\Scripts\\python.exe -m cryptoacademy score-news

Consequences by construction:

- Default is OFF. A scheduled task or stray import that reaches for the GPU
  model while the switch is off fails fast with :class:`LocalAIDisabled`
  (scheduled callers catch it / check first and skip cleanly — no alarms).
- Turning the switch off takes effect for every subsequent gate check; long
  processes should re-check between batches so ``ai off`` interrupts work
  between items.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

ENABLE_ENV = "CRYPTOACADEMY_ENABLE_LOCAL_AI"
_TRUTHY = {"1", "true", "yes", "on"}

# Persistent user switch. Lives under data/ (gitignored). Import config lazily
# in _flag_path() so this module stays import-light for the gate tests.
FLAG_FILENAME = "local_ai.on"


class LocalAIDisabled(RuntimeError):
    """Raised when local-AI (Ollama) work is attempted without authorization."""


def _flag_path() -> Path:
    from cryptoacademy import config

    return config.DATA_DIR / FLAG_FILENAME


def _flag_active() -> bool:
    """True if the persistent switch is on and not expired.

    The flag file contains either ``forever`` or an ISO-8601 UTC expiry
    timestamp. An expired or unreadable flag counts as OFF (fail closed).
    """
    path = _flag_path()
    try:
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8").strip()
        if content in ("", "forever"):
            return True
        expiry = datetime.fromisoformat(content)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return datetime.now(UTC) < expiry
    except (OSError, ValueError):
        return False


def switch_on(hours: float | None = None) -> Path:
    """Turn the persistent switch ON (explicit user action only).

    Never call this from scheduled or automatic code paths."""
    path = _flag_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if hours is None:
        path.write_text("forever", encoding="utf-8")
    else:
        expiry = datetime.now(UTC).timestamp() + hours * 3600
        path.write_text(
            datetime.fromtimestamp(expiry, tz=UTC).isoformat(), encoding="utf-8"
        )
    return path


def switch_off() -> None:
    """Turn the persistent switch OFF."""
    _flag_path().unlink(missing_ok=True)


def switch_status() -> str:
    """Human-readable status of the switch (for `cryptoacademy ai status`)."""
    if os.environ.get(ENABLE_ENV, "").strip().lower() in _TRUTHY:
        return "ON for this process (env override)"
    path = _flag_path()
    if not _flag_active():
        return "OFF"
    content = path.read_text(encoding="utf-8").strip()
    return "ON (no expiry)" if content in ("", "forever") else f"ON until {content}"


def local_ai_enabled() -> bool:
    """True if this process is authorized to use the local AI right now."""
    if os.environ.get(ENABLE_ENV, "").strip().lower() in _TRUTHY:
        return True
    return _flag_active()


def ensure_local_ai_allowed(operation: str = "the local AI") -> None:
    """Gate for every Ollama call.

    Raises :class:`LocalAIDisabled` unless the persistent switch is on or this
    run was explicitly authorized via ``CRYPTOACADEMY_ENABLE_LOCAL_AI``. Call
    it immediately before any request to the local model; long loops should
    call it per item so `ai off` takes effect promptly.
    """
    if not local_ai_enabled():
        raise LocalAIDisabled(
            f"Local AI is disabled: refusing to run {operation}. This machine "
            f"is shared with gaming, so the Ollama model never starts on its "
            f"own. Turn it on when you want it:\n"
            f"    .venv\\Scripts\\python.exe -m cryptoacademy ai on   "
            f"(optionally: --hours 4)\n"
            f"and off again with 'ai off'. One-command override: set "
            f"{ENABLE_ENV}=1 for that process only."
        )
