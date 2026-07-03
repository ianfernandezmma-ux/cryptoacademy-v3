"""GDELT GKG 2.0 harvester — historical news backfill 2020->present.

GDELT publishes a GKG file every 15 minutes since 2015 (free, no auth). The
15-min file in which a URL appears is itself a point-in-time bound: GDELT saw
the article by then, independent of the publisher's claim.

Design:
- One UTC day = 96 files, filtered for crypto keywords, written to one parquet
  (`data/raw/gdelt/YYYY/gkg_YYYYMMDD.parquet`). File existence = day done, so
  the harvester is resumable at day granularity and safe to run from a
  scheduled task with a per-run day budget.
- We keep GDELT's own metadata (tone, themes, source) — enough to build daily
  attention/sentiment features without fetching 6-year-old article bodies.
- Empty days still produce a (0-row) parquet so known GDELT outages are not
  retried forever.
"""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import polars as pl

from cryptoacademy import config

log = logging.getLogger(__name__)

GDELT_BASE = "http://data.gdeltproject.org/gdeltv2"
GDELT_START = datetime(2020, 1, 1, tzinfo=UTC)

# Byte-level filter applied to the raw upper-cased line before parsing.
KEYWORDS: dict[str, tuple[bytes, ...]] = {
    "BTC": (b"BITCOIN", b" BTC ", b"BTCUSD"),
    "ETH": (b"ETHEREUM", b"ETHER PRICE", b"ETHUSD"),
    "CRYPTO": (b"CRYPTOCURRENC", b"CRYPTO CURRENC", b"CRYPTOASSET", b"CRYPTO MARKET"),
}
ANY_KEYWORD = tuple({kw for kws in KEYWORDS.values() for kw in kws})

# GKG 2.0 tab-separated column indices.
COL_DATE, COL_SOURCE, COL_URL, COL_THEMES, COL_TONE = 1, 3, 4, 7, 15

SCHEMA = {
    "gkg_time": pl.Datetime(time_zone="UTC"),
    "file_time": pl.Datetime(time_zone="UTC"),
    "source": pl.String,
    "url": pl.String,
    "assets": pl.String,
    "tone": pl.Float64,
    "positive": pl.Float64,
    "negative": pl.Float64,
    "polarity": pl.Float64,
    "n_themes": pl.Int32,
}


def _day_path(day: datetime) -> Path:
    d = config.RAW_DIR / "gdelt" / f"{day:%Y}"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"gkg_{day:%Y%m%d}.parquet"


def _parse_line(line: bytes, file_time: datetime) -> dict | None:
    upper = line.upper()
    if not any(kw in upper for kw in ANY_KEYWORD):
        return None
    cols = line.split(b"\t")
    if len(cols) < 16:
        return None
    try:
        gkg_time = datetime.strptime(cols[COL_DATE].decode("ascii"), "%Y%m%d%H%M%S").replace(
            tzinfo=UTC
        )
    except ValueError:
        return None
    assets = [a for a, kws in KEYWORDS.items() if any(kw in upper for kw in kws)]
    tone_parts = cols[COL_TONE].split(b",")
    try:
        tone, pos, neg, polarity = (float(tone_parts[i]) for i in range(4))
    except (ValueError, IndexError):
        tone = pos = neg = polarity = float("nan")
    return {
        "gkg_time": gkg_time,
        "file_time": file_time,
        "source": cols[COL_SOURCE].decode("utf-8", errors="replace"),
        "url": cols[COL_URL].decode("utf-8", errors="replace"),
        "assets": ",".join(assets),
        "tone": tone,
        "positive": pos,
        "negative": neg,
        "polarity": polarity,
        "n_themes": cols[COL_THEMES].count(b";") if cols[COL_THEMES] else 0,
    }


def harvest_day(client: httpx.Client, day: datetime) -> int:
    """Download & filter the 96 15-min GKG files of one UTC day."""
    rows: list[dict] = []
    stamp = day.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(96):
        url = f"{GDELT_BASE}/{stamp:%Y%m%d%H%M%S}.gkg.csv.zip"
        for attempt in range(3):
            try:
                resp = client.get(url)
                if resp.status_code == 404:
                    break  # known GDELT outage windows exist
                resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    raw = zf.read(zf.namelist()[0])
                file_time = stamp
                for line in raw.split(b"\n"):
                    parsed = _parse_line(line, file_time)
                    if parsed:
                        rows.append(parsed)
                break
            except Exception as exc:  # retry twice, then skip this 15-min file
                if attempt == 2:
                    log.warning("gdelt %s failed permanently: %s", url, exc)
        stamp += timedelta(minutes=15)
    df = pl.DataFrame(rows, schema=SCHEMA) if rows else pl.DataFrame(schema=SCHEMA)
    df.write_parquet(_day_path(day))
    return len(df)


def pending_days(start: datetime = GDELT_START) -> list[datetime]:
    """Days without a parquet yet, oldest first, up to yesterday (UTC)."""
    out = []
    day = start
    last = datetime.now(UTC) - timedelta(days=1)
    while day.date() <= last.date():
        if not _day_path(day).exists():
            out.append(day)
        day += timedelta(days=1)
    return out


def harvest(max_days: int = 30) -> dict:
    """Process up to max_days pending days. Designed for an hourly scheduled
    task: each run chips away at the backlog until the backfill completes."""
    todo = pending_days()
    if not todo:
        return {"processed": 0, "remaining": 0, "rows": 0}
    total_days = (datetime.now(UTC) - GDELT_START).days
    rows = 0
    batch = todo[:max_days]
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        for day in batch:
            n = harvest_day(client, day)
            rows += n
            log.info("gdelt %s: %d crypto rows", f"{day:%Y-%m-%d}", n)
    remaining = len(todo) - len(batch)
    done_pct = 100 * (total_days - remaining) / total_days
    log.info("gdelt run done: %d days, %d rows, %.1f%% complete", len(batch), rows, done_pct)
    return {
        "processed": len(batch),
        "remaining": remaining,
        "rows": rows,
        "done_pct": round(done_pct, 1),
    }
