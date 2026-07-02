"""Open interest archiver.

Binance only serves ~30 days of OI history, so we must archive it ourselves
from day one. Each run appends the last 30 days of hourly OI (idempotent merge
on timestamp) plus a snapshot of current OI stamped with our fetch time —
giving the archive clean point-in-time semantics going forward.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
import polars as pl

from cryptoacademy import config

log = logging.getLogger(__name__)

HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"


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
    old_len = 0
    if path.exists():
        old = pl.read_parquet(path)
        old_len = len(old)
        merged = pl.concat([old, new]).sort("time").unique(subset=["time"], keep="first")
    else:
        merged = new.sort("time")
    merged.write_parquet(path)
    log.info("%s OI archive: %d rows total", asset, len(merged))
    return max(len(merged) - old_len, 0)
