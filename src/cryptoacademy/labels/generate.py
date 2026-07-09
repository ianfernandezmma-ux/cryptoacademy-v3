"""Generate labels on real data for both horizons (24h and 96h decisions).

Calibration note: k (CUSUM threshold multiple of daily vol) is the sample-size
knob. We sweep k over a small grid and pick the smallest k whose total event
count across assets lands under the target ceiling — more events = more
statistical power, as long as uniqueness stays reasonable.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.labels.core import (
    TripleBarrierConfig,
    cusum_events,
    daily_vol_on_hourly,
    sample_weights,
    triple_barrier,
)

log = logging.getLogger(__name__)

HORIZONS = {"24h": 24, "96h": 96}
K_GRID = [0.5, 0.75, 1.0, 1.25, 1.5]
TARGET_EVENTS = (1500, 3200)  # total across assets, per horizon


def _load_hourly(asset: str) -> pl.DataFrame:
    meta = config.load_assets()[asset]
    return pl.read_parquet(
        config.RAW_DIR / "klines" / asset / "spot" / f"{meta['spot_symbol']}_1h.parquet"
    ).sort("open_time")


def generate_for_asset(asset: str, k: float, horizon_bars: int) -> pl.DataFrame:
    df = _load_hourly(asset)
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    sigma = daily_vol_on_hourly(close)
    events_idx = cusum_events(close, k * sigma)
    cfg = TripleBarrierConfig(pt_mult=2.0, sl_mult=2.0, horizon_bars=horizon_bars)
    events = triple_barrier(high, low, close, events_idx, sigma, cfg)
    if events.is_empty():
        return events
    events = sample_weights(events, close)
    times = df["open_time"]
    return events.with_columns(
        pl.Series("t0_time", [times[i] for i in events["t0_idx"].to_list()]),
        pl.Series("t1_time", [times[i] for i in events["t1_idx"].to_list()]),
        pl.lit(asset).alias("asset"),
    )


def calibrate_k(horizon_bars: int) -> float:
    """Smallest k in the grid whose total event count fits under the ceiling."""
    lo, hi = TARGET_EVENTS
    counts: dict[float, int] = {}
    for k in K_GRID:
        total = 0
        for asset in config.load_assets():
            df = _load_hourly(asset)
            close = df["close"].to_numpy()
            sigma = daily_vol_on_hourly(close)
            n_events = len(cusum_events(close, k * sigma))
            # rough survival estimate (end-drops are negligible at this scale)
            total += n_events
        counts[k] = total
        log.info("k=%.2f -> %d raw events (horizon %dh)", k, total, horizon_bars)
        if total <= hi:
            if total < lo:
                log.warning("k=%.2f undershoots target range [%d, %d]", k, lo, hi)
            return k
    log.warning("no k in grid fits under %d events; using largest k=%.2f", hi, K_GRID[-1])
    return K_GRID[-1]


def generate_all() -> dict:
    """Labels for every (asset, horizon). Returns summary stats per set."""
    dest = config.DATA_DIR / "labels"
    dest.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    for hname, hbars in HORIZONS.items():
        k = calibrate_k(hbars)
        for asset in config.load_assets():
            ev = generate_for_asset(asset, k, hbars)
            path = dest / f"labels_{asset}_{hname}.parquet"
            ev.write_parquet(path)
            labels = ev["label"].to_list()
            summary[f"{asset}_{hname}"] = {
                "k": k,
                "events": len(ev),
                "up": labels.count(1),
                "down": labels.count(-1),
                "flat": labels.count(0),
                "touch_up": ev.filter(pl.col("touch") == "up").height,
                "touch_down": ev.filter(pl.col("touch") == "down").height,
                "vertical": ev.filter(pl.col("touch") == "vertical").height,
                "mean_uniqueness": round(float(np.mean(ev["uniqueness"].to_numpy())), 3),
                "first": str(ev["t0_time"].min()),
                "last": str(ev["t0_time"].max()),
            }
            log.info("%s %s: %s", asset, hname, summary[f"{asset}_{hname}"])
    return summary
