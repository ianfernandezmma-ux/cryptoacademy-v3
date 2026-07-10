"""PatchTST-style classifier (Phase 4.4 DL challenger), plain torch.

Framing per the July-2026 stack research: at 2.5k events the evaluation
protocol is the hard part, so the model is a minimal ~150-line PatchTST
(RevIN -> patch unfold -> linear embed -> TransformerEncoder -> mean-pool)
with the event's tabular features concatenated to the pooled embedding.
Purged CV + registry, deterministic runs, no early stopping, no compile.

Sequence input: the trailing W daily log returns of the event's asset ending
at the decision day BEFORE the event (same information boundary as the
tabular features)."""

from __future__ import annotations

import logging
import os
from datetime import timedelta

import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.models.dataset import build_training_frame
from cryptoacademy.models.train import block_features
from cryptoacademy.validation.cv import PurgedKFold
from cryptoacademy.validation.registry import log_trial, register_trial

log = logging.getLogger(__name__)

DL_DEFAULTS = {
    "window": 64,
    "patch_len": 8,
    "d_model": 64,
    "n_layers": 2,
    "n_heads": 4,
    "dropout": 0.3,
    "lr": 3e-4,
    "weight_decay": 1e-3,
    "epochs": 30,
    "batch_size": 64,
    "seed": 42,
}


def _set_deterministic(seed: int) -> None:
    import random

    import torch

    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def _build_model(cfg: dict, n_exog: int):
    import torch
    from torch import nn

    class RevIN(nn.Module):
        def forward(self, x):  # x: [B, W]
            mu = x.mean(dim=1, keepdim=True)
            sd = x.std(dim=1, keepdim=True) + 1e-8
            return (x - mu) / sd

    class PatchTSTClassifier(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.revin = RevIN()
            self.patch_len = cfg["patch_len"]
            n_patches = cfg["window"] // cfg["patch_len"]
            self.embed = nn.Linear(cfg["patch_len"], cfg["d_model"])
            self.pos = nn.Parameter(torch.zeros(1, n_patches, cfg["d_model"]))
            layer = nn.TransformerEncoderLayer(
                d_model=cfg["d_model"], nhead=cfg["n_heads"],
                dim_feedforward=cfg["d_model"] * 2, dropout=cfg["dropout"],
                activation="gelu", batch_first=True, norm_first=True,
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=cfg["n_layers"])
            self.head = nn.Sequential(
                nn.Linear(cfg["d_model"] + n_exog, 64),
                nn.GELU(),
                nn.Dropout(cfg["dropout"]),
                nn.Linear(64, 1),
            )

        def forward(self, seq, exog):  # seq: [B, W], exog: [B, n_exog]
            z = self.revin(seq)
            patches = z.unfold(1, self.patch_len, self.patch_len)  # [B, P, L]
            h = self.embed(patches) + self.pos
            h = self.encoder(h).mean(dim=1)  # [B, d_model]
            return self.head(torch.cat([h, exog], dim=1)).squeeze(-1)

    return PatchTSTClassifier()


def _daily_returns_by_asset() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """asset -> (dates[D], daily log returns[D]) from spot 1h klines."""
    from cryptoacademy.features.resample import to_daily

    out = {}
    for asset, meta in config.load_assets().items():
        hourly = pl.read_parquet(
            config.RAW_DIR / "klines" / asset / "spot" / f"{meta['spot_symbol']}_1h.parquet"
        )
        daily = to_daily(hourly).sort("date")
        r = daily.select(pl.col("close").log().diff().alias("r"))["r"].to_numpy()
        dates = daily["date"].to_numpy()
        out[asset] = (dates, np.nan_to_num(r, nan=0.0))
    return out


def _sequences(df: pl.DataFrame, window: int) -> np.ndarray:
    """[N, window] trailing daily returns ending at each event's decision day
    (exclusive of the event's own day — same boundary as the feature matrix)."""
    by_asset = _daily_returns_by_asset()
    seq = np.zeros((len(df), window), dtype=np.float32)
    decision = df["decision_day"].to_numpy()
    assets = df["asset"].to_list()
    for i in range(len(df)):
        dates, r = by_asset[assets[i]]
        # decision day D uses bars through D-1: idx of first date >= D
        j = int(np.searchsorted(dates, decision[i]))
        lo = max(0, j - window)
        chunk = r[lo:j]
        seq[i, window - len(chunk):] = chunk
    return seq


def evaluate_patchtst(
    horizon: str,
    cfg: dict | None = None,
    n_splits: int = 5,
    embargo_days: int = 22,
    barrier_mult: float | None = None,
) -> dict:
    """Purged-CV evaluation of the PatchTST classifier. Registers the trial."""
    import torch
    from sklearn.metrics import matthews_corrcoef

    from cryptoacademy.labels.generate import DEFAULT_BARRIER_MULT

    c = {**DL_DEFAULTS, **(cfg or {})}
    bm = barrier_mult if barrier_mult is not None else DEFAULT_BARRIER_MULT
    trial_cfg = {"model": "patchtst-clf", "cfg": c, "n_splits": n_splits,
                 "embargo_days": embargo_days, "barrier_mult": bm}
    register_trial("4.4", "patchtst", horizon, trial_cfg)
    _set_deterministic(c["seed"])

    df, all_feats = build_training_frame(horizon, barrier_mult)
    df = df.sort("t0_time")
    feats = block_features(all_feats, ["price", "derivatives", "onchain", "macro", "news"])
    x_exog = df.select(feats).to_numpy().astype(np.float32)
    seq = _sequences(df, c["window"])
    y = (df["label"].to_numpy() == 1).astype(np.float32)
    t0 = df["t0_time"].to_numpy()
    t1 = df["t1_time"].to_numpy()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    fold_metrics = []
    cv = PurgedKFold(n_splits=n_splits, embargo=timedelta(days=embargo_days))
    for fold_i, (train_idx, test_idx) in enumerate(cv.split(t0, t1)):
        # per-fold impute + standardize exog with TRAIN stats only.
        # Columns that are ALL-NaN within this train fold (e.g. LLM-era news
        # features early in history) get mu=0/sd=1 -> neutral zeros, not NaN
        # poison (a single NaN made the whole model output NaN silently).
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mu = np.nanmean(x_exog[train_idx], axis=0)
            sd = np.nanstd(x_exog[train_idx], axis=0)
        mu = np.where(np.isfinite(mu), mu, 0.0)
        sd = np.where(np.isfinite(sd) & (sd > 1e-12), sd, 1.0)
        xe = (np.where(np.isnan(x_exog), mu, x_exog) - mu) / sd
        xe = np.clip(xe, -5, 5).astype(np.float32)
        assert np.isfinite(xe).all(), "non-finite features after fold standardization"

        model = _build_model(c, xe.shape[1]).to(device)
        opt = torch.optim.AdamW(model.parameters(), lr=c["lr"], weight_decay=c["weight_decay"])
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=c["epochs"])
        loss_fn = torch.nn.BCEWithLogitsLoss()

        tr_seq = torch.tensor(seq[train_idx], device=device)
        tr_exog = torch.tensor(xe[train_idx], device=device)
        tr_y = torch.tensor(y[train_idx], device=device)
        n = len(train_idx)
        gen = torch.Generator().manual_seed(c["seed"] + fold_i)
        model.train()
        for _epoch in range(c["epochs"]):
            perm = torch.randperm(n, generator=gen)
            for b0 in range(0, n, c["batch_size"]):
                idx = perm[b0 : b0 + c["batch_size"]]
                opt.zero_grad()
                out = model(tr_seq[idx], tr_exog[idx])
                loss = loss_fn(out, tr_y[idx])
                if not torch.isfinite(loss):
                    raise RuntimeError(
                        f"non-finite loss at fold {fold_i} — refusing to train on NaN"
                    )
                loss.backward()
                opt.step()
            sched.step()

        model.eval()
        with torch.no_grad():
            logits = model(
                torch.tensor(seq[test_idx], device=device),
                torch.tensor(xe[test_idx], device=device),
            )
            proba = torch.sigmoid(logits).cpu().numpy()
        pred = (proba >= 0.5).astype(int)
        yt = y[test_idx].astype(int)
        fold_metrics.append(
            {
                "fold": fold_i,
                "n_test": len(test_idx),
                "acc": float((pred == yt).mean()),
                "mcc": float(matthews_corrcoef(yt, pred)),
            }
        )
        log.info("patchtst %s fold %d: %s", horizon, fold_i, fold_metrics[-1])

    means = {
        f"mean_{k}": float(np.mean([m[k] for m in fold_metrics])) for k in ("acc", "mcc")
    }
    metrics = {"folds": fold_metrics, **means, "device": device}
    log_trial("4.4", "patchtst", horizon, trial_cfg, metrics)
    log.info("patchtst %s: %s", horizon, means)
    return metrics
