"""On-chain (Coin Metrics), macro (FRED/ALFRED), stablecoins (DeFiLlama),
ETF flows (Farside) and Deribit options snapshots.

Every row carries published_at_utc — the moment the value became knowable —
per the lag table verified live on 2026-07-09 (docs/research/ingestion notes).
Feature assembly joins on published_at_utc, never on the reference date.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import httpx
import polars as pl

from cryptoacademy import config
from cryptoacademy.config import env

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- Coin Metrics

CM_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
# Free community set verified 2026-07-09 (FeeTotUSD/NVTAdj/CapRealUSD etc. are
# Pro-only now; RealCap is recoverable as CapMrktCurUSD / CapMVRVCur).
CM_METRICS = [
    "AdrActCnt", "TxCnt", "TxTfrCnt", "HashRate", "SplyCur",
    "CapMrktCurUSD", "CapMVRVCur", "IssTotUSD", "FlowInExUSD", "FlowOutExUSD",
    "AssetEODCompletionTime",
]


def download_coinmetrics(assets: list[str] | None = None) -> pl.DataFrame:
    assets = assets or ["btc", "eth"]
    rows: list[dict] = []
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        url: str | None = CM_URL
        params: dict | None = {
            "assets": ",".join(assets),
            "metrics": ",".join(CM_METRICS),
            "frequency": "1d",
            "start_time": "2020-01-01",
            "page_size": 10000,
            "paging_from": "start",
        }
        while url:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                time.sleep(6)
                continue
            resp.raise_for_status()
            payload = resp.json()
            rows.extend(payload["data"])
            url, params = payload.get("next_page_url"), None
            time.sleep(0.7)  # community limit: 10 req / 6 s
    df = pl.DataFrame(rows)
    value_cols = [c for c in df.columns if c not in ("asset", "time")]
    df = df.with_columns(
        pl.col("time")
        .str.to_datetime(time_zone="UTC")
        .dt.convert_time_zone("UTC")
        .alias("date"),
        *[pl.col(c).cast(pl.Float64, strict=False) for c in value_cols],
    ).drop("time")
    # knowledge time: exact EOD completion when present, else D+1 05:00 UTC
    df = df.with_columns(
        pl.when(pl.col("AssetEODCompletionTime").is_not_null())
        .then(pl.from_epoch((pl.col("AssetEODCompletionTime")).cast(pl.Int64), time_unit="s"))
        .otherwise(pl.col("date").dt.replace_time_zone(None) + pl.duration(days=1, hours=5))
        .dt.replace_time_zone("UTC")
        .alias("published_at_utc")
    )
    dest = config.RAW_DIR / "onchain"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "coinmetrics.parquet")
    log.info("coinmetrics: %d rows, %s assets", len(df), assets)
    return df


# ------------------------------------------------------------------ FRED/ALFRED

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
# series -> publication lag rule (hours added to the reference date, verified
# against the official release schedules). M2SL is handled via ALFRED vintages.
FRED_DAILY_SERIES: dict[str, int] = {
    "RRPONTSYD": 22,            # same-day ~18:00 ET -> 22:00 UTC
    "DFII10": 24 + 21,          # next business day 16:15 ET
    "T10YIE": 24 + 21,
    "BAMLH0A0HYM2": 24 + 17,
    "VIXCLS": 24 + 17,
    "WALCL": 24 * 8 + 21,       # Wed-dated week released Thu 16:30 ET (conservative)
    "WTREGEN": 24 * 8 + 21,
    "DTWEXBGS": 24 * 8 + 21,    # following Monday 16:15 ET (3-8d) -> conservative 8d
}


def download_fred() -> pl.DataFrame:
    key = env("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing in .env")
    frames = []
    with httpx.Client(timeout=60.0) as client:
        for series, lag_h in FRED_DAILY_SERIES.items():
            resp = client.get(
                FRED_URL,
                params={
                    "series_id": series, "api_key": key, "file_type": "json",
                    "observation_start": "2019-06-01",
                },
            )
            resp.raise_for_status()
            obs = resp.json()["observations"]
            frames.append(
                pl.DataFrame(
                    {
                        "series": series,
                        "date": [o["date"] for o in obs],
                        "value": [o["value"] for o in obs],
                    }
                ).with_columns(
                    pl.col("date").str.to_datetime().dt.replace_time_zone("UTC"),
                    pl.col("value").cast(pl.Float64, strict=False),  # "." -> null
                    (
                        pl.col("date").str.to_datetime() + pl.duration(hours=lag_h)
                    ).dt.replace_time_zone("UTC").alias("published_at_utc"),
                )
            )
        # M2SL as ORIGINALLY PUBLISHED (ALFRED first-print vintages)
        resp = client.get(
            FRED_URL,
            params={
                "series_id": "M2SL", "api_key": key, "file_type": "json",
                "observation_start": "2019-06-01", "output_type": 4,
                "realtime_start": "2019-06-01", "realtime_end": "9999-12-31",
            },
        )
        resp.raise_for_status()
        obs = resp.json()["observations"]
        frames.append(
            pl.DataFrame(
                {
                    "series": "M2SL",
                    "date": [o["date"] for o in obs],
                    "value": [o["value"] for o in obs],
                    "rt": [o["realtime_start"] for o in obs],
                }
            ).with_columns(
                pl.col("date").str.to_datetime().dt.replace_time_zone("UTC"),
                pl.col("value").cast(pl.Float64, strict=False),
                # first print became public on its realtime_start at 13:00 ET
                (
                    pl.col("rt").str.to_datetime() + pl.duration(hours=17)
                ).dt.replace_time_zone("UTC").alias("published_at_utc"),
            ).drop("rt")
        )
    df = pl.concat(frames)
    dest = config.RAW_DIR / "macro"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "fred.parquet")
    log.info("fred: %d rows, %d series", len(df), df["series"].n_unique())
    return df


# --------------------------------------------------------------- stablecoins

LLAMA_URL = "https://stablecoins.llama.fi"


def download_stablecoins() -> pl.DataFrame:
    frames = []
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        total = client.get(f"{LLAMA_URL}/stablecoincharts/all").raise_for_status().json()
        frames.append(
            pl.DataFrame(
                {
                    "series": "total_usd",
                    "date_s": [int(r["date"]) for r in total],
                    "value": [
                        float(r.get("totalCirculatingUSD", {}).get("peggedUSD") or 0)
                        for r in total
                    ],
                }
            )
        )
        for coin_id, name in ((1, "usdt"), (2, "usdc")):
            data = client.get(f"{LLAMA_URL}/stablecoin/{coin_id}").raise_for_status().json()
            toks = data.get("tokens") or []
            frames.append(
                pl.DataFrame(
                    {
                        "series": name,
                        "date_s": [int(r["date"]) for r in toks],
                        "value": [
                            float((r.get("circulating") or {}).get("peggedUSD") or 0)
                            for r in toks
                        ],
                    }
                )
            )
    df = (
        pl.concat(frames)
        .with_columns(
            pl.from_epoch("date_s", time_unit="s").dt.replace_time_zone("UTC").alias("date")
        )
        .drop("date_s")
        # today's row mutates intraday; day D is trustworthy from D+1 01:00 UTC
        .with_columns(
            (pl.col("date").dt.replace_time_zone(None) + pl.duration(days=1, hours=1))
            .dt.replace_time_zone("UTC")
            .alias("published_at_utc")
        )
    )
    dest = config.RAW_DIR / "stablecoins"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "stablecoins.parquet")
    log.info("stablecoins: %d rows", len(df))
    return df


# --------------------------------------------------------------- Farside ETF

FARSIDE = {
    "BTC": "https://farside.co.uk/bitcoin-etf-flow-all-data/",
    "ETH": "https://farside.co.uk/ethereum-etf-flow-all-data/",
}
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _parse_farside_table(html: str) -> pl.DataFrame:
    """Largest <table>: header row of tickers, date rows, footer 'Total'.
    Cells: '(59.1)' negative, '0.0' true zero, '-' fund-not-trading (null)."""
    from lxml import html as lhtml

    tree = lhtml.fromstring(html)
    tables = tree.xpath("//table")
    best = max(tables, key=lambda t: len(t.xpath(".//tr")))
    rows = []
    header: list[str] | None = None
    for tr in best.xpath(".//tr"):
        cells = ["".join(td.itertext()).strip() for td in tr.xpath("./td|./th")]
        if not cells:
            continue
        try:
            date = datetime.strptime(cells[0], "%d %b %Y").replace(tzinfo=UTC)
        except ValueError:
            if header is None and len(cells) > 3 and cells[0] in ("", "Date"):
                header = cells
            continue  # issuer-name/fee/seed/footer rows
        for i, raw in enumerate(cells[1:], start=1):
            if header is None or i >= len(header) or not header[i]:
                continue
            v = raw.replace(",", "").strip()
            if v in ("-", ""):
                value = None
            else:
                neg = v.startswith("(") and v.endswith(")")
                try:
                    value = float(v.strip("()"))
                except ValueError:
                    continue
                if neg:
                    value = -value
            rows.append({"date": date, "fund": header[i], "flow_musd": value})
    return pl.DataFrame(rows)


def download_etf_flows() -> pl.DataFrame:
    frames = []
    with httpx.Client(
        timeout=60.0, headers={"User-Agent": CHROME_UA}, follow_redirects=True
    ) as client:
        for asset, url in FARSIDE.items():
            resp = client.get(url)
            resp.raise_for_status()
            df = _parse_farside_table(resp.text).with_columns(pl.lit(asset).alias("asset"))
            frames.append(df)
    df = pl.concat(frames).with_columns(
        # flows for day D fill in overnight; final by 12:00 UTC on D+1
        (pl.col("date").dt.replace_time_zone(None) + pl.duration(days=1, hours=12))
        .dt.replace_time_zone("UTC")
        .alias("published_at_utc")
    )
    dest = config.RAW_DIR / "etf_flows"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "farside.parquet")
    log.info("etf flows: %d rows", len(df))
    return df


# ----------------------------------------------------- Deribit daily snapshot

def snapshot_options(currency: str) -> pl.DataFrame:
    """Forward-archive of the option chain (no free history exists).
    Stores per-instrument mark_iv/OI/volume with our snapshot time."""
    snapped_at = datetime.now(UTC)
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        resp = client.get(
            "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
            params={"currency": currency, "kind": "option"},
        )
        resp.raise_for_status()
        result = resp.json()["result"]
    df = pl.DataFrame(
        [
            {
                "instrument": r["instrument_name"],
                "mark_iv": r.get("mark_iv"),
                "underlying": r.get("underlying_price"),
                "open_interest": r.get("open_interest"),
                "volume": r.get("volume"),
                "snapped_at_utc": snapped_at,
            }
            for r in result
        ]
    )
    dest = config.RAW_DIR / "options" / "chain" / currency
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / f"chain_{snapped_at:%Y%m%d}.parquet")
    log.info("%s option chain: %d instruments", currency, len(df))
    return df


def backfill_macro_all() -> None:
    download_coinmetrics()
    download_fred()
    download_stablecoins()
    download_etf_flows()
