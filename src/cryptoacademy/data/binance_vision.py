"""Bulk historical downloads from data.binance.vision (free, no auth).

Known quirks handled here:
- Some monthly CSVs include a header row, most don't -> detect and skip.
- Since 2025-01, kline timestamps switched from milliseconds to MICROSECONDS
  -> normalize by magnitude.
- The current (incomplete) month has no monthly file -> topped up from the
  public REST klines endpoint.
"""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import UTC, datetime, timedelta

import httpx
import polars as pl
from tenacity import retry, stop_after_attempt, wait_exponential

from cryptoacademy import config

log = logging.getLogger(__name__)

BASE = "https://data.binance.vision/data"
REST_SPOT = "https://api.binance.com/api/v3/klines"
REST_FUT = "https://fapi.binance.com/fapi/v1/klines"

KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
FUNDING_COLS = ["calc_time", "funding_interval_hours", "funding_rate"]


def _normalize_epoch(col: pl.Expr) -> pl.Expr:
    """Binance switched ms -> us in 2025; normalize both to ms."""
    return pl.when(col > 1_000_000_000_000_000).then(col // 1000).otherwise(col)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30))
def _download(client: httpx.Client, url: str) -> bytes | None:
    resp = client.get(url)
    if resp.status_code == 404:
        return None  # month not available (pre-listing or current month)
    resp.raise_for_status()
    return resp.content


def _read_zip_csv(content: bytes, columns: list[str]) -> pl.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        raw = zf.read(zf.namelist()[0])
    df = pl.read_csv(raw, has_header=False, new_columns=columns, infer_schema_length=0)
    # Drop a header row if present (first cell is not numeric).
    first = df[0, 0]
    if isinstance(first, str) and not first.replace(".", "").replace("-", "").isdigit():
        df = df.slice(1)
    return df


def _months(start: str, end_exclusive: datetime) -> list[str]:
    out = []
    year, month = int(start[:4]), int(start[5:7])
    while (year, month) < (end_exclusive.year, end_exclusive.month):
        out.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def _kline_df(df: pl.DataFrame) -> pl.DataFrame:
    df = df.select(
        _normalize_epoch(pl.col("open_time").cast(pl.Int64)).alias("open_time_ms"),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64),
        pl.col("quote_volume").cast(pl.Float64),
        pl.col("trades").cast(pl.Int64),
        pl.col("taker_buy_base").cast(pl.Float64),
        pl.col("taker_buy_quote").cast(pl.Float64),
    )
    return df.with_columns(
        pl.from_epoch("open_time_ms", time_unit="ms").dt.replace_time_zone("UTC").alias("open_time")
    ).drop("open_time_ms").sort("open_time").unique(subset=["open_time"], keep="first")


def download_klines(
    asset: str, symbol: str, market: str, interval: str = "1h", start: str = "2020-01"
) -> pl.DataFrame:
    """market: 'spot' or 'futures/um'."""
    path = "spot" if market == "spot" else "futures/um"
    now = datetime.now(UTC)
    frames: list[pl.DataFrame] = []
    with httpx.Client(timeout=120.0, headers={"User-Agent": config.USER_AGENT}) as client:
        for month in _months(start, now):
            fname = f"{symbol}-{interval}-{month}.zip"
            url = f"{BASE}/{path}/monthly/klines/{symbol}/{interval}/{fname}"
            content = _download(client, url)
            if content is None:
                log.info("%s %s %s: no monthly file (skipped)", asset, market, month)
                continue
            frames.append(_kline_df(_read_zip_csv(content, KLINE_COLS)))
            log.info("%s %s %s: ok", asset, market, month)
        # Top up from REST (1000-bar pages). Start at the last bar we already
        # hold, NOT the 1st of the current month: in the first days of a month
        # the previous month's zip is not published yet and its tail hours
        # would silently go missing — a partial D-1 bar exactly at the
        # decision boundary.
        rest = REST_SPOT if market == "spot" else REST_FUT
        existing_path = (
            config.RAW_DIR / "klines" / asset / market.replace("/", "_")
            / f"{symbol}_{interval}.parquet"
        )
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if existing_path.exists():
            last_held = pl.read_parquet(existing_path, columns=["open_time"])[
                "open_time"
            ].max()
            if last_held.tzinfo is None:
                last_held = last_held.replace(tzinfo=UTC)
            top_up_from = min(month_start, last_held)
        else:
            # fresh clone: the previous month's zip may not exist yet either
            prev = (month_start - timedelta(days=1)).replace(day=1)
            top_up_from = prev
        start_ms = int(top_up_from.timestamp() * 1000)
        rows: list[list] = []
        while True:
            resp = client.get(
                rest,
                params={"symbol": symbol, "interval": interval, "startTime": start_ms,
                        "limit": 1000},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < 1000:
                break
            start_ms = batch[-1][0] + 1
        if rows:
            df = pl.DataFrame(
                [[str(v) for v in r] for r in rows], schema=KLINE_COLS, orient="row"
            )
            frames.append(_kline_df(df))
    out = pl.concat(frames).sort("open_time").unique(subset=["open_time"], keep="first")
    dest = config.RAW_DIR / "klines" / asset / market.replace("/", "_")
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{symbol}_{interval}.parquet"
    if path.exists():  # incremental top-up: merge with what we already have
        out = (
            pl.concat([pl.read_parquet(path), out])
            .sort("open_time")
            .unique(subset=["open_time"], keep="last")
        )
    out.write_parquet(path)
    return out


def download_funding(asset: str, symbol: str, start: str = "2020-01") -> pl.DataFrame:
    now = datetime.now(UTC)
    frames: list[pl.DataFrame] = []
    with httpx.Client(timeout=120.0, headers={"User-Agent": config.USER_AGENT}) as client:
        for month in _months(start, now):
            url = f"{BASE}/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"
            content = _download(client, url)
            if content is None:
                continue
            frames.append(_read_zip_csv(content, FUNDING_COLS))
        # Current month via REST (full history endpoint, paginated).
        resp = client.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={
                "symbol": symbol,
                "startTime": int(datetime(now.year, now.month, 1, tzinfo=UTC).timestamp() * 1000),
                "limit": 1000,
            },
        )
        resp.raise_for_status()
        rest_rows = resp.json()
    out = pl.concat(frames).select(
        _normalize_epoch(pl.col("calc_time").cast(pl.Int64)).alias("calc_time_ms"),
        pl.col("funding_rate").cast(pl.Float64),
    )
    if rest_rows:
        out = pl.concat([
            out,
            pl.DataFrame(
                {
                    "calc_time_ms": [int(r["fundingTime"]) for r in rest_rows],
                    "funding_rate": [float(r["fundingRate"]) for r in rest_rows],
                }
            ),
        ])
    out = (
        out.with_columns(
            pl.from_epoch("calc_time_ms", time_unit="ms")
            .dt.replace_time_zone("UTC")
            .alias("funding_time")
        )
        .drop("calc_time_ms")
        .sort("funding_time")
        .unique(subset=["funding_time"], keep="first")
    )
    dest = config.RAW_DIR / "funding" / asset
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{symbol}_funding.parquet"
    if path.exists():
        out = (
            pl.concat([pl.read_parquet(path), out])
            .sort("funding_time")
            .unique(subset=["funding_time"], keep="last")
        )
    out.write_parquet(path)
    return out


def gap_report(df: pl.DataFrame, interval_minutes: int = 60) -> pl.DataFrame:
    """Bars whose gap to the previous bar exceeds the interval (exchange outages)."""
    gaps = df.select(
        pl.col("open_time"),
        (pl.col("open_time").diff().dt.total_minutes()).alias("gap_minutes"),
    ).filter(pl.col("gap_minutes") > interval_minutes)
    return gaps
