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
        throttled = 0
        while url:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                # cap the retries: an uncapped loop turns a persistent
                # throttle into an indefinitely hung daily_update that never
                # reaches its own failure alerting
                throttled += 1
                if throttled > 10:
                    resp.raise_for_status()
                time.sleep(min(6 * throttled, 60))
                continue
            throttled = 0
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

# Publication rules per official release schedules. Times are EASTERN and get
# converted to UTC properly (a fixed UTC offset would drift 1h every winter),
# and "next business day" respects weekends + US federal holidays: a Friday
# H.15 print is knowable Monday evening, not Saturday (audit finding C-1).
# M2SL is handled separately via ALFRED first-print vintages.
FRED_RULES: dict[str, tuple[int, str]] = {
    # series: (business days after reference date, release time ET "HH:MM")
    "RRPONTSYD": (0, "18:00"),      # NY Fed posts same afternoon ~13:15 ET
    "DFII10": (1, "16:15"),         # H.15: next business day 16:15 ET
    "T10YIE": (1, "16:15"),
    "BAMLH0A0HYM2": (1, "12:00"),   # ICE BofA via FRED next business morning
    "VIXCLS": (1, "12:00"),
    "WALCL": (1, "16:30"),          # Wed-dated H.4.1 released Thursday 16:30 ET
    "WTREGEN": (1, "16:30"),
    "DTWEXBGS": (6, "16:15"),       # H.10: following Monday -> ~4-6 busdays worst case
}


def _us_federal_holidays(years: range) -> list[str]:
    """Fixed + nth-weekday US federal holidays, observed-shifted, as ISO dates."""
    import datetime as dt

    out = []
    for y in years:
        fixed = [(1, 1), (6, 19), (7, 4), (11, 11), (12, 25)]
        for m, d in fixed:
            day = dt.date(y, m, d)
            if day.weekday() == 5:
                day -= dt.timedelta(days=1)
            elif day.weekday() == 6:
                day += dt.timedelta(days=1)
            out.append(day.isoformat())

        def nth_weekday(month: int, weekday: int, n: int, year: int = y) -> dt.date:
            d0 = dt.date(year, month, 1)
            offset = (weekday - d0.weekday()) % 7
            return d0 + dt.timedelta(days=offset + 7 * (n - 1))

        out.append(nth_weekday(1, 0, 3).isoformat())    # MLK: 3rd Mon Jan
        out.append(nth_weekday(2, 0, 3).isoformat())    # Presidents: 3rd Mon Feb
        last_may = dt.date(y, 5, 31)
        last_may -= dt.timedelta(days=(last_may.weekday() - 0) % 7)
        out.append(last_may.isoformat())                # Memorial: last Mon May
        out.append(nth_weekday(9, 0, 1).isoformat())    # Labor: 1st Mon Sep
        out.append(nth_weekday(10, 0, 2).isoformat())   # Columbus: 2nd Mon Oct
        out.append(nth_weekday(11, 3, 4).isoformat())   # Thanksgiving: 4th Thu Nov
    return out


_HOLIDAYS = _us_federal_holidays(range(2019, 2031))


def fred_published_at(ref_date: datetime, busdays: int, et_time: str) -> datetime:
    """Knowledge time for a FRED observation: reference date + N US business
    days, at the release time in America/New_York, converted to UTC."""
    from zoneinfo import ZoneInfo

    import numpy as np

    d = np.datetime64(ref_date.strftime("%Y-%m-%d"), "D")
    if busdays == 0:
        release_day = np.busday_offset(d, 0, roll="forward", holidays=_HOLIDAYS)
    else:
        release_day = np.busday_offset(d, busdays, roll="forward", holidays=_HOLIDAYS)
    hh, mm = (int(x) for x in et_time.split(":"))
    et = datetime.strptime(str(release_day), "%Y-%m-%d").replace(
        hour=hh, minute=mm, tzinfo=ZoneInfo("America/New_York")
    )
    return et.astimezone(UTC)


def download_fred() -> pl.DataFrame:
    key = env("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing in .env")
    frames = []
    with httpx.Client(timeout=60.0) as client:
        for series, (busdays, et_time) in FRED_RULES.items():
            resp = client.get(
                FRED_URL,
                params={
                    "series_id": series, "api_key": key, "file_type": "json",
                    "observation_start": "2019-06-01",
                },
            )
            resp.raise_for_status()
            obs = resp.json()["observations"]
            dates = [datetime.strptime(o["date"], "%Y-%m-%d") for o in obs]
            frames.append(
                pl.DataFrame(
                    {
                        "series": series,
                        "date": dates,
                        "value": [o["value"] for o in obs],
                        "published_at_utc": [
                            fred_published_at(d, busdays, et_time) for d in dates
                        ],
                    }
                ).with_columns(
                    pl.col("date").dt.replace_time_zone("UTC"),
                    pl.col("value").cast(pl.Float64, strict=False),  # "." -> null
                    pl.col("published_at_utc").dt.convert_time_zone("UTC"),
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

# Primary: full-history pages. Fallback: the compact recent-flows pages —
# same table format (header split over two rows, handled by the parser) and
# ~13 recent business days, enough to keep the daily first-print vintage
# alive when Cloudflare blocks the all-data URL.
FARSIDE = {
    "BTC": (
        "https://farside.co.uk/bitcoin-etf-flow-all-data/",
        "https://farside.co.uk/btc/",
    ),
    "ETH": (
        "https://farside.co.uk/ethereum-etf-flow-all-data/",
        "https://farside.co.uk/eth/",
    ),
}
# Cloudflare bot-scores bare/outdated clients; send a coherent, current
# Chrome header set (no explicit Accept-Encoding — httpx negotiates what it
# can actually decode).
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Not)A;Brand";v="8", "Chromium";v="143", "Google Chrome";v="143"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


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
            # the compact pages split the header over two rows (tickers on
            # one, 'Total' on another) — merge all header-shaped rows seen
            # before the first data row, first non-empty cell per column wins
            if not rows and len(cells) > 3 and cells[0] in ("", "Date"):
                if header is None:
                    header = cells
                else:
                    header = [
                        h or c
                        for h, c in zip(
                            header + [""] * (len(cells) - len(header)),
                            cells + [""] * (len(header) - len(cells)),
                            strict=True,
                        )
                    ]
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


def _fetch_farside_asset(
    client: httpx.Client, asset: str, urls: tuple[str, ...]
) -> pl.DataFrame | None:
    """Try each URL with retries; None when Cloudflare blocks everything."""
    for url in urls:
        for attempt in range(4):
            try:
                resp = client.get(url)
            except httpx.HTTPError as exc:
                log.warning("etf flows %s: %s on %s", asset, exc, url)
                time.sleep(20 * (attempt + 1))
                continue
            if resp.status_code == 200:
                df = _parse_farside_table(resp.text)
                if len(df):
                    return df.with_columns(pl.lit(asset).alias("asset"))
                log.warning("etf flows %s: %s returned 200 but no rows parsed", asset, url)
                break  # page layout problem, retrying won't help — next URL
            log.warning("etf flows %s: HTTP %d from %s (attempt %d)",
                        asset, resp.status_code, url, attempt + 1)
            time.sleep(20 * (attempt + 1))
    return None


def download_etf_flows() -> pl.DataFrame:
    dest = config.RAW_DIR / "etf_flows"
    dest.mkdir(parents=True, exist_ok=True)
    ppath = dest / "farside.parquet"
    prior = pl.read_parquet(ppath) if ppath.exists() else None

    fresh_frames, blocked = [], []
    with httpx.Client(timeout=60.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
        for asset, urls in FARSIDE.items():
            # Cloudflare blocks intermittently (403); each missed day is a
            # PERMANENT first-print vintage gap, so retry hard, fall back to
            # the compact page, and alert distinctly so a manual snapshot can
            # still be taken in time
            df = _fetch_farside_asset(client, asset, urls)
            if df is None:
                blocked.append(asset)
            else:
                fresh_frames.append(df)

    if blocked:
        from cryptoacademy.notify import telegram

        telegram.send(
            f"ETF flows: Farside blocked for {', '.join(blocked)} after all "
            "retries + fallback URL — today's first-print vintage will be "
            "LOST unless snapped manually; keeping last good data"
        )
    if not fresh_frames:
        if prior is None:
            raise RuntimeError("etf flows: Farside blocked and no prior data on disk")
        # degrade gracefully: leave files untouched; the freshness gate in
        # daily-update flags the dataset once it stays blocked for days
        log.warning("etf flows: all sources blocked — keeping stale parquet")
        return prior

    fresh = pl.concat(fresh_frames).with_columns(
        # flows for day D fill in overnight; final by 12:00 UTC on D+1
        (pl.col("date").dt.replace_time_zone(None) + pl.duration(days=1, hours=12))
        .dt.replace_time_zone("UTC")
        .alias("published_at_utc")
    )
    # the compact fallback page only covers recent days, and a blocked asset
    # contributes nothing — retain prior rows outside each asset's freshly
    # fetched window so one degraded fetch never truncates the history
    parts = [fresh]
    if prior is not None:
        for asset in prior["asset"].unique().to_list():
            asset_fresh = fresh.filter(pl.col("asset") == asset)
            keep = pl.col("asset") == asset
            if len(asset_fresh):
                keep &= pl.col("date") < asset_fresh["date"].min()
            parts.append(prior.filter(keep).select(fresh.columns))
    df = pl.concat(parts).sort(["asset", "date"])
    df.write_parquet(ppath)
    # Farside restates cells in place for ~48h; keep append-only vintages so
    # the live era has true first-print flows (audit M-8). Pre-archive history
    # is revised-values era by construction — documented limitation. Only the
    # freshly OBSERVED rows are snapped — never carried-forward prior data.
    snap = fresh.with_columns(pl.lit(datetime.now(UTC)).alias("snapped_at_utc"))
    vpath = dest / "farside_vintages.parquet"
    if vpath.exists():
        snap = pl.concat([pl.read_parquet(vpath), snap], how="diagonal_relaxed")
    snap.write_parquet(vpath)
    log.info(
        "etf flows: %d rows (%d fresh%s, +vintage snapshot)",
        len(df), len(fresh), f", blocked: {','.join(blocked)}" if blocked else "",
    )
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
