"""LightGBM training/evaluation under purged CV.

Discipline:
- Every evaluated configuration is REGISTERED before evaluation and its
  metrics logged after (validation.registry) — N_trials feeds DSR.
- CV is PurgedKFold over the events' real [t0, t1] intervals, embargo 22d.
- No early stopping in baselines (a fold-internal validation split is an easy
  leak surface); tree count is a fixed, registered hyperparameter.
- Small-sample regularization defaults per the research brief: shallow trees,
  strong min_child_samples, feature subsampling.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np

from cryptoacademy.models.dataset import build_training_frame
from cryptoacademy.validation.cv import PurgedKFold
from cryptoacademy.validation.registry import log_trial, register_trial

log = logging.getLogger(__name__)

# feature blocks by column prefix (ablation unit = block)
BLOCK_PREFIXES: dict[str, tuple[str, ...]] = {
    "price": (
        "ret_", "mom_voladj_", "rsi_", "macd", "bb_", "px_vs_", "drawdown",
        "close_in_range", "range_1d", "vol_parkinson", "vol_gk", "vol_ewma",
        "vol_ratio", "vol_of_vol", "vol_z", "volume_z", "taker_imbalance",
        "amihud", "vol_realized",
    ),
    "derivatives": (
        "funding_", "oi_", "top_ls", "global_ls", "taker_ls", "iv_", "vrp",
        "positioning_missing",
    ),
    "onchain": ("oc_",),
    "macro": ("macro_", "stable_", "etf_", "fng_"),
    "news": ("news_", "gdelt_", "evt_", "era_llm", "low_news_flag"),
}

BASE_PARAMS = {
    "objective": "binary",
    "num_leaves": 15,
    "max_depth": 4,
    "learning_rate": 0.05,
    "n_estimators": 300,
    "min_child_samples": 100,
    "feature_fraction": 0.5,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l1": 0.1,
    "lambda_l2": 1.0,
    "verbosity": -1,
    "seed": 42,
}


def block_features(feature_names: list[str], blocks: list[str]) -> list[str]:
    keep = []
    for name in feature_names:
        for block in blocks:
            if any(name.startswith(p) for p in BLOCK_PREFIXES[block]):
                keep.append(name)
                break
    return keep


def _mcc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import matthews_corrcoef

    return float(matthews_corrcoef(y_true, y_pred))


def evaluate_config(
    horizon: str,
    blocks: list[str],
    params: dict | None = None,
    n_splits: int = 5,
    embargo_days: int = 22,
    tag: str = "",
    barrier_mult: float | None = None,
    features_override: list[str] | None = None,
) -> dict:
    """Purged-CV evaluation of one configuration. Registers + logs the trial."""
    import lightgbm as lgb

    df, all_features = build_training_frame(horizon, barrier_mult)
    feats = features_override or block_features(all_features, blocks)
    if not feats:
        raise ValueError(f"no features for blocks {blocks}")

    config_dict = {
        "blocks": blocks, "params": params or BASE_PARAMS,
        "n_splits": n_splits, "embargo_days": embargo_days,
        "n_features": len(feats), "barrier_mult": float(df["barrier_mult"][0]),
        "cusum_k": float(df["cusum_k"][0]),
        "features_override": sorted(features_override) if features_override else None,
    }
    register_trial("4.2", f"lgbm{'-' + tag if tag else ''}", horizon, config_dict)

    df = df.sort("t0_time")
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()
    x = df.select(feats).to_numpy().astype(np.float64)
    y = (df["label"].to_numpy() == 1).astype(int)
    w = df["sample_weight"].to_numpy()
    ret = df["ret"].to_numpy()

    p = dict(params or BASE_PARAMS)
    fold_metrics = []
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for fold_i, (train_idx, test_idx) in enumerate(cv.split(t0, t1)):
        model = lgb.LGBMClassifier(**p)
        model.fit(x[train_idx], y[train_idx], sample_weight=w[train_idx])
        proba = model.predict_proba(x[test_idx])[:, 1]
        pred = (proba >= 0.5).astype(int)
        # side-following event returns (cost-free; costs enter in Phase 5)
        side = np.where(pred == 1, 1.0, -1.0)
        strat_ret = side * ret[test_idx]
        fold_metrics.append(
            {
                "fold": fold_i,
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "acc": float((pred == y[test_idx]).mean()),
                "mcc": _mcc(y[test_idx], pred),
                "hit_ret": float((strat_ret > 0).mean()),
                "mean_ret": float(strat_ret.mean()),
            }
        )
    means = {
        f"mean_{k}": float(np.mean([m[k] for m in fold_metrics]))
        for k in ("acc", "mcc", "hit_ret", "mean_ret")
    }
    metrics = {"folds": fold_metrics, **means}
    log_trial("4.2", f"lgbm{'-' + tag if tag else ''}", horizon, config_dict, metrics)
    log.info("%s %s blocks=%s -> %s", horizon, tag or "lgbm", blocks, means)
    return metrics


def run_baselines() -> dict:
    """The bars every later model must clear, both horizons."""
    results: dict[str, dict] = {}
    for horizon in ("24h", "96h"):
        df, _ = build_training_frame(horizon)
        base_rate = float((df["label"] == 1).mean())
        results[f"{horizon}_always_long_acc"] = {"mean_acc": max(base_rate, 1 - base_rate)}
        results[f"{horizon}_momentum"] = evaluate_config(
            horizon, ["price"], tag="momentum-baseline"
        )
        results[f"{horizon}_full"] = evaluate_config(
            horizon,
            ["price", "derivatives", "onchain", "macro", "news"],
            tag="full",
        )
    return results
