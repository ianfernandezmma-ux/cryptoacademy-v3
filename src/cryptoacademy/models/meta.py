"""Meta-labeling (Phase 4.4): a small secondary model that predicts whether
the primary's directional call will be profitable, used to filter false
positives and size positions (AFML §3.6; Joubert JFDS series).

Construction (leak-hygiene per the 4.4 adversarial audit):
1. TEST-side primary signal: outer OOF under PurgedKFold — the event's fold
   was the test fold, so no model that produced it saw the event.
2. TRAIN-side primary signal: NESTED inner OOF computed strictly within each
   outer training fold (audit M1: the outer OOF of a train event came from a
   primary that trained on the current TEST fold — optimistic contamination
   of the secondary's calibration).
3. Meta labels: with symmetric barriers, ret/touch are side-independent, so
   "did the call win" = (side * ret) > 0 exactly — no barrier re-run needed.
4. Secondary: logistic regression on <=8 slow features + the primary
   probability; uplift metrics compare ONLY folds where the gated bucket is
   valid (audit M2: mismatched fold subsets overstated uplift).

Every configuration goes through the registry (phase 4.4).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np

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


def _purged_oof(
    x: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    t0: np.ndarray,
    t1: np.ndarray,
    params: dict,
    n_splits: int,
    embargo_days: int,
) -> np.ndarray:
    """Out-of-fold P(up) under purged CV over the given (sub)set of events.
    Every event lands in exactly one test fold, so the output has no NaNs."""
    import lightgbm as lgb

    oof = np.full(len(y), np.nan)
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for train_idx, test_idx in cv.split(t0, t1):
        model = lgb.LGBMClassifier(**params)
        model.fit(x[train_idx], y[train_idx], sample_weight=w[train_idx])
        oof[test_idx] = model.predict_proba(x[test_idx])[:, 1]
    return oof


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

    df, all_feats = build_training_frame(horizon, barrier_mult)
    df = df.sort("t0_time")
    feats = block_features(all_feats, ["price", "derivatives", "onchain", "macro", "news"])
    xs_cols = [c for c in META_FEATURES if c in df.columns]
    trial_cfg = {
        "params": p, "barrier_mult": bm, "n_splits": n_splits,
        "embargo_days": embargo_days, "meta_threshold": meta_threshold,
        "meta_features": xs_cols,  # the columns actually used (audit M5)
        "nested_oof": True,
    }
    register_trial("4.4", "meta-labeling", horizon, trial_cfg)

    x = df.select(feats).to_numpy().astype(np.float64)
    y = (df["label"].to_numpy() == 1).astype(int)
    w = df["sample_weight"].to_numpy()
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()
    ret = df["ret"].to_numpy()
    x_slow = np.nan_to_num(
        df.select(xs_cols).to_numpy().astype(np.float64), nan=0.0
    )  # elementwise constant impute; features are z-scores where 0 is neutral

    # clean TEST-side signal: outer OOF (event's own fold was the test fold)
    outer_oof = _purged_oof(x, y, w, t0, t1, p, n_splits, embargo_days)

    fold_rows = []
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for fold_i, (train_idx, test_idx) in enumerate(cv.split(t0, t1)):
        # TRAIN-side signal: inner OOF restricted to this training fold
        # (audit M1 — the outer OOF of train events was produced by primaries
        # that saw this test fold)
        inner_oof = _purged_oof(
            x[train_idx], y[train_idx], w[train_idx], t0[train_idx], t1[train_idx],
            p, max(2, n_splits - 1), embargo_days,
        )
        side_tr = np.where(inner_oof >= 0.5, 1, -1)
        meta_y_tr = ((side_tr * ret[train_idx]) > 0).astype(int)
        if meta_y_tr.sum() in (0, len(meta_y_tr)):
            continue  # degenerate fold

        clf = LogisticRegression(max_iter=1000, C=0.5)
        clf.fit(np.column_stack([inner_oof, x_slow[train_idx]]), meta_y_tr)

        side_te = np.where(outer_oof[test_idx] >= 0.5, 1, -1)
        meta_y_te = ((side_te * ret[test_idx]) > 0).astype(int)
        p_win = clf.predict_proba(
            np.column_stack([outer_oof[test_idx], x_slow[test_idx]])
        )[:, 1]

        side_ret = side_te * ret[test_idx]
        keep = p_win >= meta_threshold
        valid = keep.sum() >= 10
        try:
            auc = float(roc_auc_score(meta_y_te, p_win))
        except ValueError:
            auc = None
        fold_rows.append(
            {
                "fold": fold_i, "n_test": len(test_idx),
                "primary_hit": float((side_ret > 0).mean()),
                "meta_gated_hit": float((side_ret[keep] > 0).mean()) if valid else None,
                "coverage": float(keep.mean()),
                "meta_auc": auc,
                "primary_mean_ret": float(side_ret.mean()),
                "gated_mean_ret": float(side_ret[keep].mean()) if valid else None,
            }
        )

    # uplift over the SAME folds only (audit M2)
    paired = [r for r in fold_rows if r["meta_gated_hit"] is not None]

    def _mean(rows: list[dict], key: str) -> float | None:
        vals = [r[key] for r in rows if r[key] is not None]
        return float(np.mean(vals)) if vals else None

    metrics = {
        "folds": fold_rows,
        "n_paired_folds": len(paired),
        "mean_primary_hit_paired": _mean(paired, "primary_hit"),
        "mean_gated_hit": _mean(paired, "meta_gated_hit"),
        "mean_coverage": _mean(fold_rows, "coverage"),
        "mean_meta_auc": _mean(fold_rows, "meta_auc"),
        "precision_uplift": (
            _mean(paired, "meta_gated_hit") - _mean(paired, "primary_hit")
            if paired else None
        ),
        "n_events": len(df),
    }
    log_trial("4.4", "meta-labeling", horizon, trial_cfg, metrics)
    log.info("meta-labeling %s: %s", horizon, {k: v for k, v in metrics.items() if k != "folds"})
    return metrics
