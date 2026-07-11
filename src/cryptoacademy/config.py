"""Central configuration. Paths are derived from the package location so that
scheduled tasks work regardless of the current working directory."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import truststore
import yaml
from dotenv import load_dotenv

# Use the Windows certificate store for TLS: this machine sits behind a
# TLS-intercepting proxy/antivirus whose root CA is not in certifi's bundle.
truststore.inject_into_ssl()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIGS_DIR = PROJECT_ROOT / "configs"
NEWS_DB_PATH = DATA_DIR / "news.duckdb"

load_dotenv(PROJECT_ROOT / ".env")

# Point-in-time buffers: an article is usable for a decision at time T only if
# usable_at = max(published_at, first_seen_at) + buffer <= T.
# Live-collected rows have a first_seen_at we control -> small buffer.
# Backfilled rows only carry a publisher/aggregator claim -> conservative buffer.
LIVE_BUFFER = timedelta(minutes=30)
BACKFILL_BUFFER = timedelta(hours=4)

# Lockbox: events from this instant onward are excluded from every training /
# CV / selection run (build_training_frame enforces it). Opened ONCE at the
# end of Phase 5. NOTE (audit 2026-07-11): selection during Phases 4.2-4.4 ran
# WITHOUT this cutoff and consumed ~218 events from 2026-H1 — that period is
# documented as a contaminated holdout in the audit; the cutoff now prevents
# any further touching.
LOCKBOX_START = "2026-01-01"

USER_AGENT = "CryptoAcademyResearch/3.0 (+academic thesis project; contact via GitHub)"

HTTP_TIMEOUT = 30.0


def env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key, default)
    return value if value else default


def load_assets() -> dict[str, dict]:
    """Asset universe (single parametrized code path for every asset)."""
    with open(CONFIGS_DIR / "assets.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["assets"]


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
