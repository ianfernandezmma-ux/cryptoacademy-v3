"""Alternative data with genuine backfill and clean point-in-time semantics.

- Binance Vision futures `metrics` (5-min OI, top-trader & global long/short
  ratios, taker buy/sell) — daily immutable dumps since 2020-09; the only
  honest positioning history (REST keeps 30 days).
- Deribit DVOL (30d implied vol index) since 2021-03, public, immutable.
- Wikipedia pageviews (attention proxy) since 2015-07, immutable.
- CFTC COT (CME BTC/ETH positioning). PIT rule: Tuesday data published FRIDAY
  ~15:30 ET -> downstream features must apply a 3-day publication embargo.
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

METRICS_BASE = "https://data.binance.vision/data/futures/um/daily/metrics"
METRICS_START = datetime(2020, 9, 1, tzinfo=UTC)
METRICS_COLS = [
    "create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
    "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
    "count_long_short_ratio", "sum_taker_long_short_vol_ratio",
]


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30))
def _get(client: httpx.Client, url: str, **kwargs) -> httpx.Response | None:
    resp = client.get(url, **kwargs)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp


def download_metrics(asset: str, symbol: str) -> pl.DataFrame:
    """All daily `metrics` zips, resumable: skips days already in the parquet."""
    dest = config.RAW_DIR / "metrics" / asset
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{symbol}_metrics.parquet"
    existing = pl.read_parquet(path) if path.exists() else None
    have_days = (
        set(existing["create_time"].dt.date().unique().to_list()) if existing is not None else set()
    )
    frames: list[pl.DataFrame] = [existing] if existing is not None else []
    day = METRICS_START
    yesterday = datetime.now(UTC) - timedelta(days=1)
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        while day <= yesterday:
            if day.date() not in have_days:
                fname = f"{symbol}-metrics-{day:%Y-%m-%d}.zip"
                resp = _get(client, f"{METRICS_BASE}/{symbol}/{fname}")
                if resp is not None:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                        raw = zf.read(zf.namelist()[0])
                    df = pl.read_csv(raw, infer_schema_length=0)
                    df = df.select(
                        pl.col("create_time")
                        .str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
                        .dt.replace_time_zone("UTC"),
                        pl.col("sum_open_interest").cast(pl.Float64),
                        pl.col("sum_open_interest_value").cast(pl.Float64),
                        pl.col("count_toptrader_long_short_ratio").cast(pl.Float64),
                        pl.col("sum_toptrader_long_short_ratio").cast(pl.Float64),
                        pl.col("count_long_short_ratio").cast(pl.Float64),
                        pl.col("sum_taker_long_short_vol_ratio").cast(pl.Float64),
                    ).drop_nulls(subset=["create_time"])
                    frames.append(df)
            day += timedelta(days=1)
    out = (
        pl.concat(frames)
        .sort("create_time")
        .unique(subset=["create_time"], keep="first")
    )
    out.write_parquet(path)
    log.info("%s metrics: %d rows (%s -> %s)", asset, len(out),
             out["create_time"].min(), out["create_time"].max())
    return out


def download_dvol(currency: str) -> pl.DataFrame:
    """Deribit DVOL daily candles since index launch (2021-03)."""
    url = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
    start_ms = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() * 1000)
    end_ms = int(datetime.now(UTC).timestamp() * 1000)
    rows: list[list[float]] = []
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        while True:
            resp = client.get(url, params={
                "currency": currency, "resolution": "1D",
                "start_timestamp": start_ms, "end_timestamp": end_ms,
            })
            resp.raise_for_status()
            result = resp.json()["result"]
            rows = result["data"] + rows
            continuation = result.get("continuation")
            if not continuation or not result["data"]:
                break
            end_ms = continuation
    df = (
        pl.DataFrame(
            {
                "timestamp_ms": [int(r[0]) for r in rows],
                "dvol_open": [r[1] for r in rows],
                "dvol_high": [r[2] for r in rows],
                "dvol_low": [r[3] for r in rows],
                "dvol_close": [r[4] for r in rows],
            }
        )
        .with_columns(
            pl.from_epoch("timestamp_ms", time_unit="ms").dt.replace_time_zone("UTC").alias("time")
        )
        .drop("timestamp_ms")
        .sort("time")
        .unique(subset=["time"], keep="first")
    )
    dest = config.RAW_DIR / "options"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / f"{currency}_dvol.parquet")
    log.info("%s DVOL: %d days", currency, len(df))
    return df


WIKI_PAGES = ["Bitcoin", "Ethereum", "Cryptocurrency"]


def download_wiki_pageviews() -> pl.DataFrame:
    """Daily Wikipedia pageviews (immutable — the cleanest attention proxy)."""
    frames = []
    end = datetime.now(UTC).strftime("%Y%m%d")
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        for page in WIKI_PAGES:
            url = (
                "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
                f"en.wikipedia/all-access/user/{page}/daily/20200101/{end}"
            )
            resp = client.get(url)
            resp.raise_for_status()
            items = resp.json()["items"]
            frames.append(
                pl.DataFrame(
                    {
                        "date": [i["timestamp"][:8] for i in items],
                        "page": page,
                        "views": [i["views"] for i in items],
                    }
                )
            )
    df = (
        pl.concat(frames)
        .with_columns(pl.col("date").str.to_datetime("%Y%m%d").dt.replace_time_zone("UTC"))
        .sort(["page", "date"])
    )
    dest = config.RAW_DIR / "attention"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "wiki_pageviews.parquet")
    log.info("wiki pageviews: %d rows across %d pages", len(df), len(WIKI_PAGES))
    return df


def download_cot() -> pl.DataFrame:
    """CFTC Traders-in-Financial-Futures for CME Bitcoin/Ether.

    Stored with report_date (Tuesday). Downstream features MUST add the
    publication lag: usable from Friday 15:30 ET of the same week (~report_date
    + 3 days). We store published_at_utc explicitly to force the point.
    """
    url = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
    params = {
        "$where": "contract_market_name like '%BITCOIN%' "
                  "OR contract_market_name like '%ETHER%'",
        "$limit": "50000",
    }
    with httpx.Client(timeout=120.0, headers={"User-Agent": config.USER_AGENT}) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        raise RuntimeError("CFTC returned no rows")
    df = pl.DataFrame(rows)
    keep = [c for c in df.columns if c in {
        "report_date_as_yyyy_mm_dd", "contract_market_name", "open_interest_all",
        "lev_money_positions_long", "lev_money_positions_short",
        "asset_mgr_positions_long", "asset_mgr_positions_short",
        "dealer_positions_long_all", "dealer_positions_short_all",
        "nonrept_positions_long_all", "nonrept_positions_short_all",
    }]
    df = df.select(keep).with_columns(
        pl.col("report_date_as_yyyy_mm_dd").str.to_datetime("%Y-%m-%dT%H:%M:%S%.f", strict=False)
        .dt.replace_time_zone("UTC").alias("report_date"),
    ).drop("report_date_as_yyyy_mm_dd")
    # Publication embargo baked into the table itself.
    df = df.with_columns(
        (pl.col("report_date") + pl.duration(days=3, hours=20)).alias("published_at_utc")
    ).sort("report_date")
    dest = config.RAW_DIR / "positioning"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "cftc_cot.parquet")
    log.info("COT: %d rows, %s -> %s", len(df), df["report_date"].min(), df["report_date"].max())
    return df
