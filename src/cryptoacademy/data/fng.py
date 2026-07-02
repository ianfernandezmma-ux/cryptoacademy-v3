"""Fear & Greed index (alternative.me): full daily history since 2018-02 in one
free call. PIT caveat: the index methodology changed over the years and values
are not re-published point-in-time — treat as an approximate market-state
feature, never as news."""

from __future__ import annotations

import httpx
import polars as pl

from cryptoacademy import config

URL = "https://api.alternative.me/fng/?limit=0&format=json"


def download_fng() -> pl.DataFrame:
    with httpx.Client(timeout=60.0, headers={"User-Agent": config.USER_AGENT}) as client:
        data = client.get(URL).raise_for_status().json()["data"]
    df = (
        pl.DataFrame(
            {
                "timestamp": [int(d["timestamp"]) for d in data],
                "fng_value": [int(d["value"]) for d in data],
                "fng_class": [d["value_classification"] for d in data],
            }
        )
        .with_columns(
            pl.from_epoch("timestamp", time_unit="s").dt.replace_time_zone("UTC").alias("date")
        )
        .drop("timestamp")
        .sort("date")
    )
    dest = config.RAW_DIR / "sentiment"
    dest.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest / "fear_greed.parquet")
    return df
