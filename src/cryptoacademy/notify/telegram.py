"""Telegram notifications. No-op (with a log line) until the token/chat_id are
set in .env, so the pipeline never depends on it."""

from __future__ import annotations

import html
import logging

import httpx

from cryptoacademy.config import env

log = logging.getLogger(__name__)


def send(text: str) -> bool:
    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("telegram not configured; message suppressed: %s", text[:120])
        return False
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            # escape: alert text routinely embeds exception strings ('<', '&'
            # in URLs/reprs) and an unescaped char turns into a Telegram 400 —
            # the alert most worth delivering is the one that gets dropped
            json={"chat_id": chat_id, "text": html.escape(text), "parse_mode": "HTML"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # notifications must never break the pipeline
        log.error("telegram send FAILED (alert lost): %s | text: %s", exc, text[:200])
        return False
