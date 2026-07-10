"""Chronos-2 zero-shot benchmark (Phase 4.4).

No tuning by construction — one registered config per horizon. The 120M
encoder forecasts the daily log-price H steps ahead from a trailing context;
P(up) is read off the quantile grid where it crosses the last close
(interpolated), giving a thresholdable score comparable to the classifiers.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.models.dataset import build_training_frame
from cryptoacademy.validation.registry import log_trial, register_trial

log = logging.getLogger(__name__)

CONTEXT = 512
QUANTILES = [round(q, 2) for q in np.arange(0.05, 0.96, 0.05)]
HORIZON_DAYS = {"24h": 1, "96h": 4}
MODEL_ID = "amazon/chronos-2"


def _prob_up(quantile_row: np.ndarray, last_close: float) -> float:
    """P(price_H > last_close) from an ascending quantile grid (interpolated)."""
    q = np.asarray(QUANTILES)
    v = np.sort(quantile_row)  # enforce monotone (model output can wiggle)
    if last_close <= v[0]:
        return 1.0 - q[0] / 2
    if last_close >= v[-1]:
        return q[-1] / 20  # ~0.05/2: nearly all mass below
    level = float(np.interp(last_close, v, q))
    return 1.0 - level


def evaluate_chronos(horizon: str) -> dict:
    import torch
    from chronos import BaseChronosPipeline
    from sklearn.metrics import matthews_corrcoef

    from cryptoacademy.features.resample import to_daily

    trial_cfg = {"model_id": MODEL_ID, "context": CONTEXT, "quantiles": QUANTILES,
                 "h_days": HORIZON_DAYS[horizon]}
    register_trial("4.4", "chronos2-zeroshot", horizon, trial_cfg)

    pipeline = BaseChronosPipeline.from_pretrained(
        MODEL_ID, device_map="cuda" if torch.cuda.is_available() else "cpu",
        torch_dtype=torch.bfloat16,
    )

    df, _ = build_training_frame(horizon)
    df = df.sort("t0_time")
    h_days = HORIZON_DAYS[horizon]

    # unique forecast tasks: (asset, decision_day)
    daily_by_asset = {}
    for asset, meta in config.load_assets().items():
        hourly = pl.read_parquet(
            config.RAW_DIR / "klines" / asset / "spot" / f"{meta['spot_symbol']}_1h.parquet"
        )
        d = to_daily(hourly).sort("date")
        daily_by_asset[asset] = (d["date"].to_numpy(), d["close"].to_numpy())

    tasks = df.select(["asset", "decision_day"]).unique().sort(["asset", "decision_day"])
    contexts, lasts, keys = [], [], []
    for asset, day in tasks.iter_rows():
        dates, close = daily_by_asset[asset]
        # numpy datetime64 arrays are tz-naive UTC; strip tzinfo before comparing
        day_np = np.datetime64(day.replace(tzinfo=None))
        j = int(np.searchsorted(dates, day_np))  # bars strictly before decision day
        if j < 64:
            continue
        ctx = np.log(close[max(0, j - CONTEXT):j])
        contexts.append(torch.tensor(ctx, dtype=torch.float32))
        lasts.append(float(ctx[-1]))
        keys.append((asset, day))

    probs: dict[tuple, float] = {}
    batch = 128
    for b0 in range(0, len(contexts), batch):
        chunk = contexts[b0 : b0 + batch]
        quantiles, _ = pipeline.predict_quantiles(
            chunk, prediction_length=h_days, quantile_levels=QUANTILES
        )
        # returns a list of per-series tensors [h_days, n_q] (or one stacked tensor)
        for i in range(len(chunk)):
            q_i = quantiles[i]
            if hasattr(q_i, "cpu"):
                q_i = q_i.float().cpu().numpy()
            # per-series output is [1, h_days, n_q]; drop the batch dim
            arr_i = np.asarray(q_i).reshape(-1, len(QUANTILES))
            probs[keys[b0 + i]] = _prob_up(arr_i[h_days - 1, :], lasts[b0 + i])

    rows = df.select(["asset", "decision_day", "label"]).iter_rows()
    y_true, y_pred = [], []
    for asset, day, label in rows:
        p = probs.get((asset, day))
        if p is None:
            continue
        y_true.append(1 if label == 1 else 0)
        y_pred.append(1 if p >= 0.5 else 0)
    yt, yp = np.array(y_true), np.array(y_pred)
    metrics = {
        "n_events": len(yt),
        "mean_acc": float((yt == yp).mean()),
        "mean_mcc": float(matthews_corrcoef(yt, yp)),
        "pred_up_share": float(yp.mean()),
    }
    log_trial("4.4", "chronos2-zeroshot", horizon, trial_cfg, metrics)
    log.info("chronos2 %s: %s", horizon, metrics)
    return metrics
