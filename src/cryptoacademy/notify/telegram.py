"""Telegram notifications. No-op (with a log line) until the token/chat_id are
set in .env, so the pipeline never depends on it."""

from __future__ import annotations

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
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # notifications must never break the pipeline
        log.warning("telegram send failed: %s", exc)
        return False
