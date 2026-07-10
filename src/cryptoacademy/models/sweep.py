"""Phase 4.2 search: Optuna sweep, SHAP-stability feature selection, and
per-block ablations. Every evaluation goes through evaluate_config, which
registers the trial — the registry count IS the DSR deflation input.

Selection happens on purged-CV scores; the final honest assessment comes
later (CPCV distribution + DSR with the full registry N + the untouched
lockbox at the end of Phase 5).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np

from cryptoacademy.models.dataset import build_training_frame
from cryptoacademy.models.train import BASE_PARAMS, block_features, evaluate_config
from cryptoacademy.validation.cv import PurgedKFold

log = logging.getLogger(__name__)

ALL_BLOCKS = ["price", "derivatives", "onchain", "macro", "news"]


def optuna_sweep(horizon: str, n_trials: int = 40) -> dict:
    """LightGBM hyperparameters x barrier variant, scored by mean purged-CV
    MCC. Optuna's sampler sees only fold-internal aggregate scores."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: optuna.Trial) -> float:
        params = dict(BASE_PARAMS)
        params.update(
            num_leaves=trial.suggest_int("num_leaves", 7, 31),
            max_depth=trial.suggest_int("max_depth", 3, 5),
            learning_rate=trial.suggest_float("learning_rate", 0.02, 0.1, log=True),
            n_estimators=trial.suggest_int("n_estimators", 100, 500, step=100),
            min_child_samples=trial.suggest_int("min_child_samples", 50, 200, step=25),
            feature_fraction=trial.suggest_float("feature_fraction", 0.3, 0.7),
            lambda_l1=trial.suggest_float("lambda_l1", 1e-3, 10, log=True),
            lambda_l2=trial.suggest_float("lambda_l2", 1e-3, 10, log=True),
        )
        barrier_mult = trial.suggest_categorical("barrier_mult", [1.0, 1.5, 2.0])
        metrics = evaluate_config(
            horizon, ALL_BLOCKS, params=params, tag="sweep",
            barrier_mult=barrier_mult,
        )
        return metrics["mean_mcc"]

    study = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=42)
    )
    study.optimize(objective, n_trials=n_trials)
    log.info("%s sweep best: mcc=%.4f params=%s", horizon, study.best_value, study.best_params)
    return {"best_value": study.best_value, "best_params": study.best_params}


def shap_stable_features(
    horizon: str,
    params: dict,
    barrier_mult: float | None = None,
    top_k: int = 60,
    worst_rank_cap: int = 80,
) -> list[str]:
    """Features whose per-fold mean |SHAP| rank stays inside worst_rank_cap in
    EVERY purged fold (stability beats magnitude under non-stationarity),
    capped at top_k by mean rank."""
    import lightgbm as lgb
    import shap

    df, all_features = build_training_frame(horizon, barrier_mult)
    feats = block_features(all_features, ALL_BLOCKS)
    df = df.sort("t0_time")
    x = df.select(feats).to_numpy().astype(np.float64)
    y = (df["label"].to_numpy() == 1).astype(int)
    w = df["sample_weight"].to_numpy()
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()

    ranks = []
    cv = PurgedKFold(n_splits=5, embargo=timedelta(days=22))
    for train_idx, _test_idx in cv.split(t0, t1):
        model = lgb.LGBMClassifier(**params)
        model.fit(x[train_idx], y[train_idx], sample_weight=w[train_idx])
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(x[train_idx])
        if isinstance(sv, list):  # binary: [class0, class1]
            sv = sv[1]
        mean_abs = np.abs(sv).mean(axis=0)
        order = np.argsort(-mean_abs)
        rank = np.empty(len(feats), dtype=int)
        rank[order] = np.arange(len(feats))
        ranks.append(rank)
    ranks_arr = np.vstack(ranks)  # folds x features
    worst = ranks_arr.max(axis=0)
    mean_rank = ranks_arr.mean(axis=0)
    stable = [
        (mean_rank[i], feats[i]) for i in range(len(feats)) if worst[i] <= worst_rank_cap
    ]
    stable.sort()
    selected = [f for _, f in stable[:top_k]]
    log.info("%s SHAP-stable selection: %d/%d features survive", horizon, len(selected),
             len(feats))
    return selected


def block_ablations(horizon: str, params: dict, barrier_mult: float | None = None) -> dict:
    """Each block alone + leave-one-block-out — the thesis's core table."""
    results: dict[str, float] = {}
    for block in ALL_BLOCKS:
        m = evaluate_config(
            horizon, [block], params=params, tag=f"ablate-only-{block}",
            barrier_mult=barrier_mult,
        )
        results[f"only_{block}"] = m["mean_mcc"]
        remaining = [b for b in ALL_BLOCKS if b != block]
        m = evaluate_config(
            horizon, remaining, params=params, tag=f"ablate-drop-{block}",
            barrier_mult=barrier_mult,
        )
        results[f"drop_{block}"] = m["mean_mcc"]
    full = evaluate_config(
        horizon, ALL_BLOCKS, params=params, tag="ablate-full", barrier_mult=barrier_mult
    )
    results["full"] = full["mean_mcc"]
    return results
