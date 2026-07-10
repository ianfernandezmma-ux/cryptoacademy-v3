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

# Barrier multiplier: 2.0 sigma of the horizon return left ~75% of events on
# the vertical barrier (labels degenerate toward fixed-horizon signs). 1.5 is
# the deliberate default; {1.0, 1.5, 2.0} is a REGISTERED grid dimension in
# Phase 4.2 — every choice counts as a trial for DSR.
DEFAULT_BARRIER_MULT = 1.5
MAX_VERTICAL_SHARE = 0.80


def _load_hourly(asset: str) -> pl.DataFrame:
    meta = config.load_assets()[asset]
    return pl.read_parquet(
        config.RAW_DIR / "klines" / asset / "spot" / f"{meta['spot_symbol']}_1h.parquet"
    ).sort("open_time")


def generate_for_asset(
    asset: str, k: float, horizon_bars: int, barrier_mult: float = DEFAULT_BARRIER_MULT
) -> pl.DataFrame:
    df = _load_hourly(asset)
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    sigma = daily_vol_on_hourly(close)
    events_idx = cusum_events(close, k * sigma)
    cfg = TripleBarrierConfig(
        pt_mult=barrier_mult, sl_mult=barrier_mult, horizon_bars=horizon_bars
    )
    events = triple_barrier(high, low, close, events_idx, sigma, cfg)
    if events.is_empty():
        return events
    events = sample_weights(events, close)
    times = df["open_time"]
    return events.with_columns(
        pl.Series("t0_time", [times[i] for i in events["t0_idx"].to_list()]),
        pl.Series("t1_time", [times[i] for i in events["t1_idx"].to_list()]),
        pl.lit(asset).alias("asset"),
        pl.lit(barrier_mult).alias("barrier_mult"),
        pl.lit(k).alias("cusum_k"),
    )


def calibrate_k(horizon_bars: int, barrier_mult: float = DEFAULT_BARRIER_MULT) -> float:
    """Largest event count that fits under the ceiling, counted on SURVIVING
    labeled events (raw CUSUM counts overcount: end-of-data and gap-window
    drops scale with the horizon)."""
    lo, hi = TARGET_EVENTS
    for k in K_GRID:
        total = 0
        for asset in config.load_assets():
            total += len(generate_for_asset(asset, k, horizon_bars, barrier_mult))
        log.info("k=%.2f -> %d surviving events (horizon %dh)", k, total, horizon_bars)
        if total <= hi:
            if total < lo:
                log.warning("k=%.2f undershoots target range [%d, %d]", k, lo, hi)
            return k
    log.warning("no k in grid fits under %d events; using largest k=%.2f", hi, K_GRID[-1])
    return K_GRID[-1]


def label_suffix(barrier_mult: float) -> str:
    """File suffix per barrier variant; the default keeps the plain name."""
    return "" if barrier_mult == DEFAULT_BARRIER_MULT else f"_m{round(barrier_mult * 10)}"


def generate_variants(mults: tuple[float, ...] = (1.0, 2.0)) -> None:
    """Label sets for non-default barrier multipliers (sweep dimension).
    Reuses the k calibrated for the default set so event SAMPLING is identical
    across variants — only the labeling differs."""
    dest = config.DATA_DIR / "labels"
    dest.mkdir(parents=True, exist_ok=True)
    for hname, hbars in HORIZONS.items():
        k = calibrate_k(hbars, DEFAULT_BARRIER_MULT)
        for mult in mults:
            for asset in config.load_assets():
                ev = generate_for_asset(asset, k, hbars, mult)
                if ev.is_empty():
                    continue
                ev.write_parquet(dest / f"labels_{asset}_{hname}{label_suffix(mult)}.parquet")
                log.info("variant m=%.1f %s %s: %d events", mult, asset, hname, len(ev))


def generate_all(barrier_mult: float = DEFAULT_BARRIER_MULT) -> dict:
    """Labels for every (asset, horizon). Returns summary stats per set."""
    dest = config.DATA_DIR / "labels"
    dest.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    for hname, hbars in HORIZONS.items():
        k = calibrate_k(hbars, barrier_mult)
        for asset in config.load_assets():
            ev = generate_for_asset(asset, k, hbars, barrier_mult)
            path = dest / f"labels_{asset}_{hname}.parquet"
            if ev.is_empty():
                log.error("%s %s: zero surviving events — not writing", asset, hname)
                summary[f"{asset}_{hname}"] = {"k": k, "events": 0}
                continue
            ev.write_parquet(path)
            labels = ev["label"].to_list()
            vert_share = ev.filter(pl.col("touch") == "vertical").height / len(ev)
            if vert_share > MAX_VERTICAL_SHARE:
                log.warning(
                    "%s %s: %.0f%% vertical touches (> %.0f%%) — barriers too wide, "
                    "labels degenerate toward fixed-horizon signs",
                    asset, hname, 100 * vert_share, 100 * MAX_VERTICAL_SHARE,
                )
            summary[f"{asset}_{hname}"] = {
                "k": k,
                "barrier_mult": barrier_mult,
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
