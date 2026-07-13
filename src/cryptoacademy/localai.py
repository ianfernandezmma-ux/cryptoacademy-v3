"""Central authorization gate for the local AI (the Ollama GPU model).

This machine is also used for gaming, so the local LLM must NEVER start on its
own. Every code path that contacts Ollama — news scoring, dedup embeddings,
risk-regime classification — calls :func:`ensure_local_ai_allowed` first, and
that returns normally ONLY when the current process was explicitly authorized
for this run via the ``CRYPTOACADEMY_ENABLE_LOCAL_AI`` environment variable.

Consequences by construction:

- A scheduled task, a stray import, or any un-authorized invocation that tries
  to reach the GPU model fails fast with :class:`LocalAIDisabled` and never
  loads the model — nothing hits the GPU while you play.
- To run the local AI on purpose ("activate the AI to analyse news"), set the
  variable for that ONE command only, e.g. in PowerShell::

      $env:CRYPTOACADEMY_ENABLE_LOCAL_AI = '1'
      .venv\\Scripts\\python.exe -m cryptoacademy score-news

  The variable is not persisted, so the authorization lasts exactly one
  process and vanishes when it exits.
"""

from __future__ import annotations

import os

ENABLE_ENV = "CRYPTOACADEMY_ENABLE_LOCAL_AI"
_TRUTHY = {"1", "true", "yes", "on"}


class LocalAIDisabled(RuntimeError):
    """Raised when local-AI (Ollama) work is attempted without authorization."""


def local_ai_enabled() -> bool:
    """True only if this process was explicitly authorized to use the local AI."""
    return os.environ.get(ENABLE_ENV, "").strip().lower() in _TRUTHY


def ensure_local_ai_allowed(operation: str = "the local AI") -> None:
    """Gate for every Ollama call.

    Raises :class:`LocalAIDisabled` unless this run was explicitly authorized
    via ``CRYPTOACADEMY_ENABLE_LOCAL_AI``. Call it immediately before any
    request to the local model.
    """
    if not local_ai_enabled():
        raise LocalAIDisabled(
            f"Local AI is disabled: refusing to run {operation}. This machine "
            f"is shared with gaming, so the Ollama model never runs "
            f"automatically. To enable it for THIS command only, set "
            f"{ENABLE_ENV}=1 first, e.g. PowerShell:\n"
            f"    $env:{ENABLE_ENV}='1'; "
            f".venv\\Scripts\\python.exe -m cryptoacademy score-news"
        )
