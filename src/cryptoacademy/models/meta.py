"""Meta-labeling (Phase 4.4): a small secondary model that predicts whether
the primary's directional call will be profitable, used to filter false
positives and size positions (AFML §3.6; Joubert JFDS series).

Construction (leak-hygiene notes inline):
1. OOF primary: LightGBM (best 4.2 config) predicts each event's direction
   out-of-fold under PurgedKFold — an event's primary signal never comes from
   a model that saw it.
2. Meta labels: triple_barrier re-run with side = primary's OOF call, on the
   SAME event t0s and sigma; binary "did the call make money" (stop -> 0).
3. Secondary: logistic regression on <=8 slow features + the primary's OOF
   probability, evaluated under the SAME purged folds. Per the evidence, the
   meta layer should improve precision/drawdown, not total return — we report
   precision uplift at fixed coverage, per fold and per year.

Every configuration goes through the registry (phase 4.4).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.labels.core import TripleBarrierConfig, daily_vol_on_hourly, triple_barrier
from cryptoacademy.models.dataset import build_training_frame
from cryptoacademy.models.train import BASE_PARAMS, block_features
from cryptoacademy.validation.cv import PurgedKFold
from cryptoacademy.validation.registry import log_trial, register_trial

log = logging.getLogger(__name__)

META_FEATURES = [
    "vol_z_252d", "vol_ratio_5_63", "funding_z_30d",
    "drawdown_252d", "taker_imbalance_5d", "oi_chg_7d",
]
HORIZON_BARS = {"24h": 24, "96h": 96}


def _oof_primary(
    df: pl.DataFrame, feats: list[str], params: dict, n_splits: int, embargo_days: int
) -> np.ndarray:
    """Out-of-fold P(up) for every event under purged CV. Events never scored
    by a model that trained on them; events purged from every fold keep NaN."""
    import lightgbm as lgb

    x = df.select(feats).to_numpy().astype(np.float64)
    y = (df["label"].to_numpy() == 1).astype(int)
    w = df["sample_weight"].to_numpy()
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()
    oof = np.full(len(df), np.nan)
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for train_idx, test_idx in cv.split(t0, t1):
        model = lgb.LGBMClassifier(**params)
        model.fit(x[train_idx], y[train_idx], sample_weight=w[train_idx])
        oof[test_idx] = model.predict_proba(x[test_idx])[:, 1]
    return oof


def _meta_labels_for_asset(
    asset: str, horizon: str, events: pl.DataFrame, side: np.ndarray, barrier_mult: float
) -> np.ndarray:
    """Re-run the triple barrier with the primary's side on this asset's events."""
    meta = config.load_assets()[asset]
    hourly = pl.read_parquet(
        config.RAW_DIR / "klines" / asset / "spot" / f"{meta['spot_symbol']}_1h.parquet"
    ).sort("open_time")
    close = hourly["close"].to_numpy()
    sigma = daily_vol_on_hourly(close)
    cfg = TripleBarrierConfig(
        pt_mult=barrier_mult, sl_mult=barrier_mult, horizon_bars=HORIZON_BARS[horizon]
    )
    out = triple_barrier(
        hourly["high"].to_numpy(), hourly["low"].to_numpy(), close,
        events["t0_idx"].to_numpy(), sigma, cfg, side=side,
    )
    # triple_barrier drops nothing here (same event set that survived labeling)
    assert len(out) == len(events), "meta relabeling changed the event set"
    return out["label"].to_numpy()


def run_meta_labeling(
    horizon: str,
    params: dict | None = None,
    barrier_mult: float | None = None,
    n_splits: int = 5,
    embargo_days: int = 22,
    meta_threshold: float = 0.55,
) -> dict:
    """Full meta-labeling evaluation for one horizon. Registers the trial."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    from cryptoacademy.labels.generate import DEFAULT_BARRIER_MULT

    bm = barrier_mult if barrier_mult is not None else DEFAULT_BARRIER_MULT
    p = dict(params or BASE_PARAMS)
    trial_cfg = {
        "params": p, "barrier_mult": bm, "n_splits": n_splits,
        "embargo_days": embargo_days, "meta_threshold": meta_threshold,
        "meta_features": META_FEATURES,
    }
    register_trial("4.4", "meta-labeling", horizon, trial_cfg)

    df, all_feats = build_training_frame(horizon, barrier_mult)
    feats = block_features(all_feats, ["price", "derivatives", "onchain", "macro", "news"])
    df = df.sort("t0_time").with_row_index("_row")

    oof = _oof_primary(df, feats, p, n_splits, embargo_days)
    scored = ~np.isnan(oof)
    side = np.where(oof >= 0.5, 1, -1)

    # meta labels per asset on the same events
    meta_y = np.full(len(df), -1)
    for asset in df["asset"].unique().to_list():
        mask = (df["asset"] == asset).to_numpy()
        events = df.filter(pl.col("asset") == asset)
        meta_y[mask] = _meta_labels_for_asset(asset, horizon, events, side[mask], bm)

    # secondary model under the same purged folds
    xs_cols = [c for c in META_FEATURES if c in df.columns]
    x_meta = np.column_stack([oof, df.select(xs_cols).to_numpy().astype(np.float64)])
    x_meta = np.nan_to_num(x_meta, nan=0.0)  # logistic can't take NaN; 0 = z-neutral
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()
    ret = df["ret"].to_numpy()

    fold_rows = []
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for fold_i, (train_idx, test_idx) in enumerate(cv.split(t0, t1)):
        train_idx = train_idx[scored[train_idx]]
        test_idx = test_idx[scored[test_idx]]
        if len(train_idx) < 100 or len(test_idx) < 20:
            continue
        clf = LogisticRegression(max_iter=1000, C=0.5)
        clf.fit(x_meta[train_idx], meta_y[train_idx])
        p_win = clf.predict_proba(x_meta[test_idx])[:, 1]

        side_ret = side[test_idx] * ret[test_idx]  # primary's per-event PnL
        base_hit = float((side_ret > 0).mean())
        keep = p_win >= meta_threshold
        gated_hit = float((side_ret[keep] > 0).mean()) if keep.sum() >= 10 else None
        try:
            auc = float(roc_auc_score(meta_y[test_idx], p_win))
        except ValueError:
            auc = None
        fold_rows.append(
            {
                "fold": fold_i, "n_test": len(test_idx),
                "primary_hit": base_hit,
                "meta_gated_hit": gated_hit,
                "coverage": float(keep.mean()),
                "meta_auc": auc,
                "primary_mean_ret": float(side_ret.mean()),
                "gated_mean_ret": float(side_ret[keep].mean()) if keep.sum() >= 10 else None,
            }
        )

    def _mean(key: str) -> float | None:
        vals = [r[key] for r in fold_rows if r[key] is not None]
        return float(np.mean(vals)) if vals else None

    metrics = {
        "folds": fold_rows,
        "mean_primary_hit": _mean("primary_hit"),
        "mean_gated_hit": _mean("meta_gated_hit"),
        "mean_coverage": _mean("coverage"),
        "mean_meta_auc": _mean("meta_auc"),
        "precision_uplift": (
            (_mean("meta_gated_hit") or 0) - (_mean("primary_hit") or 0)
            if _mean("meta_gated_hit") is not None else None
        ),
        "n_events_scored": int(scored.sum()),
    }
    log_trial("4.4", "meta-labeling", horizon, trial_cfg, metrics)
    log.info("meta-labeling %s: %s", horizon, {k: v for k, v in metrics.items() if k != "folds"})
    return metrics
