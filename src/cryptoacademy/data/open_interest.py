"""Open interest archiver.

Binance only serves ~30 days of OI history, so we must archive it ourselves
from day one. Each run appends the last 30 days of hourly OI (idempotent merge
on timestamp) plus a snapshot of current OI stamped with our fetch time —
giving the archive clean point-in-time semantics going forward.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

from cryptoacademy import config

log = logging.getLogger(__name__)

HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"


def _atomic_write_parquet(df: pl.DataFrame, path: Path) -> None:
    """Write parquet via temp file + fsync + rename so a crash never leaves a
    truncated archive at `path` (the 2026-07-12 crash zeroed both OI archives)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.write_parquet(tmp)
    with open(tmp, "rb+") as f:
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _load_archive(path: Path) -> pl.DataFrame | None:
    """Read the existing archive; on corruption, quarantine it and start fresh.

    OI is forward-only (Binance serves ~30d), so refusing to run for days over
    an unreadable file loses data permanently. The 5-min `metrics` dataset
    holds OI redundantly, so quarantining (never deleting) is safe.
    """
    if not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception:
        quarantine = path.with_name(
            f"{path.name}.corrupt-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
        )
        path.replace(quarantine)
        log.error(
            "Archive %s is unreadable; quarantined to %s and rebuilding fresh",
            path,
            quarantine,
        )
        return None


def archive_open_interest(asset: str, symbol: str) -> int:
    """Fetch hourly OI history (max ~30d) and merge into the archive parquet."""
    fetched_at = datetime.now(UTC)
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        resp = client.get(HIST_URL, params={"symbol": symbol, "period": "1h", "limit": 500})
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        return 0
    new = pl.DataFrame(
        {
            "timestamp_ms": [int(r["timestamp"]) for r in rows],
            "open_interest": [float(r["sumOpenInterest"]) for r in rows],
            "open_interest_usd": [float(r["sumOpenInterestValue"]) for r in rows],
        }
    ).with_columns(
        pl.from_epoch("timestamp_ms", time_unit="ms").dt.replace_time_zone("UTC").alias("time"),
        pl.lit(fetched_at).alias("fetched_at_utc"),
    ).drop("timestamp_ms")

    dest = config.RAW_DIR / "open_interest" / asset
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{symbol}_oi.parquet"
    old = _load_archive(path)
    old_len = 0
    if old is not None:
        old_len = len(old)
        merged = pl.concat([old, new]).sort("time").unique(subset=["time"], keep="first")
    else:
        merged = new.sort("time")
    _atomic_write_parquet(merged, path)
    log.info("%s OI archive: %d rows total", asset, len(merged))
    return max(len(merged) - old_len, 0)
