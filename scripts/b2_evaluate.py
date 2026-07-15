"""B2 one-shot evaluation (protocol: docs/b2-preregistration.md, FROZEN).

Order enforced by this script:
  1. refuse to run if results already exist (re-runs only for pre-run-review
     confirmed code defects, --force-defect "reason", and they are registered);
  2. register ALL candidate identities (intent) in the lab registry;
  3. evaluate once, net of the frozen cost model;
  4. log metrics per identity, apply the FROZEN champion rule, write results.

Run with the LAB venv:  .venv\\Scripts\\python.exe scripts\\b2_evaluate.py
Strategy code is imported from C:\\CryptoBot\\src (single source of truth —
the same functions the bot will run in production).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import date

import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.validation import registry, stats

sys.path.insert(0, r"C:\CryptoBot\src")
from cryptobot.engine import sizing, strategies

# ---- frozen protocol constants (docs/b2-preregistration.md) -----------------
CUTOFF = date(2026, 7, 11)
SCORE_START = date(2021, 1, 1)
FEE = 0.0010
SLIP = {"BTC": 0.0005, "ETH": 0.0010}
HIGHVOL_PCT = 0.80
HIGHVOL_WARMUP = 365
DRAG_LIMIT = 0.10
MAXDD_LIMIT = 0.40
ANN = 365
PHASE = "bot-b2"
ASSETS = ("BTC", "ETH")

OUT_DIR = config.DATA_DIR / "b2"
RESULTS_JSON = OUT_DIR / "b2_results.json"
RESULTS_MD = config.PROJECT_ROOT / "docs" / "b2-results.md"

CANDIDATES: list[tuple[str, str, dict]] = [
    ("S1_SMA100_HOLD", "96h", {"kind": "s1", "sma": 100}),
    ("S1_SMA200_HOLD", "96h", {"kind": "s1", "sma": 200}),
    ("S2_DONCH_N10", "96h", {"kind": "s2", "entry": 10, "exit": 5, "gate_sma": 200}),
    ("S2_DONCH_N20", "96h", {"kind": "s2", "entry": 20, "exit": 10, "gate_sma": 200}),
    ("S3_EWMAC", "96h", {"kind": "s3", "gate_sma": 200,
                          "specs": [[8, 32, 5.3], [32, 128, 2.65]], "cap": 20, "avg": 10}),
    ("S2_DONCH_N5_FAST", "24h", {"kind": "s2", "entry": 5, "exit": 2, "gate_sma": 200}),
    ("COMBO", "96h", {"kind": "combo", "families": ["S2_DONCH_N10", "S2_DONCH_N20", "S3_EWMAC"],
                       "inclusion": "cost_drag<=0.10", "weights": "equal",
                       "fallback": "S1_SMA200_HOLD"}),
]
COMBO_FAMILIES = ["S2_DONCH_N10", "S2_DONCH_N20", "S3_EWMAC"]


# ---- data --------------------------------------------------------------------
def load_daily(asset: str) -> pl.DataFrame:
    path = config.RAW_DIR / "klines" / asset / "spot" / f"{asset}USDT_1h.parquet"
    df = (
        pl.read_parquet(path)
        .with_columns(pl.col("open_time").dt.date().alias("day"))
        .group_by("day", maintain_order=True)
        .agg(pl.col("close").last())
        .sort("day")
        .filter(pl.col("day") <= CUTOFF)
    )
    days = df["day"].to_list()
    gaps = [(a, b) for a, b in itertools.pairwise(days) if (b - a).days != 1]
    if gaps:
        raise RuntimeError(f"{asset}: daily gaps present: {gaps[:5]}")
    return df


def highvol_flags(vol_ann: np.ndarray) -> np.ndarray:
    """True where 30d EWMA vol exceeds the expanding 80th pct of its own
    history (>= HIGHVOL_WARMUP observations; frozen definition)."""
    flags = np.zeros(len(vol_ann), dtype=bool)
    for t in range(HIGHVOL_WARMUP, len(vol_ann)):
        flags[t] = vol_ann[t] > np.quantile(vol_ann[: t + 1], HIGHVOL_PCT)
    return flags


# ---- engine ------------------------------------------------------------------
def scalars_for(cfg: dict, closes: dict[str, np.ndarray],
                family_scalars: dict[str, dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    out = {}
    for a in ASSETS:
        c = closes[a]
        if cfg["kind"] == "s1":
            out[a] = strategies.s1_gate(c, cfg["sma"])
        elif cfg["kind"] == "s2":
            gate = strategies.s1_gate(c, cfg["gate_sma"])
            out[a] = strategies.s2_donchian(c, cfg["entry"], cfg["exit"], gate=gate)
        elif cfg["kind"] == "s3":
            gate = strategies.s1_gate(c, cfg["gate_sma"])
            out[a] = strategies.s3_ewmac(c, gate=gate)
        elif cfg["kind"] == "combo":
            included = cfg["_included"]
            out[a] = strategies.combo([family_scalars[f][a] for f in included])
        else:
            raise ValueError(cfg["kind"])
    return out


def run_config(scalars: dict[str, np.ndarray], rets: dict[str, np.ndarray],
               vols: dict[str, np.ndarray], hv: dict[str, np.ndarray],
               score_mask: np.ndarray) -> dict:
    """Weights, costs, net daily portfolio returns; metrics on the scored window.

    Timing: w[t] (decided at close t) earns day t+1's return; costs of moving
    from w[t-1] to w[t] are charged in day t+1's return."""
    T = len(score_mask)
    scal = np.column_stack([scalars[a] for a in ASSETS])
    vol = np.column_stack([vols[a] for a in ASSETS])
    targets = sizing.target_weights(scal, vol)
    held = sizing.apply_buffer(targets)

    turnover = np.abs(np.diff(held, axis=0, prepend=np.zeros((1, len(ASSETS)))))
    side_cost = np.column_stack([
        FEE + SLIP[a] * np.where(hv[a], 2.0, 1.0) for a in ASSETS
    ])
    daily_cost = (turnover * side_cost).sum(axis=1)

    r = np.column_stack([rets[a] for a in ASSETS])
    port = np.zeros(T)
    port[1:] = (held[:-1] * r[1:]).sum(axis=1) - daily_cost[:-1]

    net = port[score_mask]
    gross = (held[:-1] * r[1:]).sum(axis=1)[score_mask[1:]]
    costs = daily_cost[:-1][score_mask[1:]]
    years = len(net) / ANN

    equity = np.cumprod(1 + net)
    dd = 1 - equity / np.maximum.accumulate(equity)
    sr_d = stats.sharpe(net)
    skew, kurt = stats._moments(net)

    # round trips: flat-to-flat episodes per asset on held weight
    rts, wins = 0, 0
    for i, _a in enumerate(ASSETS):
        h = held[score_mask, i]
        ra = r[score_mask, i]
        in_pos, pnl = False, 0.0
        for t in range(len(h) - 1):
            if h[t] > 1e-9:
                if not in_pos:
                    in_pos, pnl = True, 0.0
                pnl += h[t] * ra[t + 1]
            elif in_pos:
                rts += 1
                wins += pnl > 0
                in_pos = False
        if in_pos:
            rts += 1
            wins += pnl > 0

    return {
        "held": held, "net_daily": net,
        "metrics": {
            "ann_return": float(np.mean(net) * ANN),
            "ann_vol": float(np.std(net, ddof=1) * np.sqrt(ANN)),
            "sharpe_ann": float(sr_d * np.sqrt(ANN)),
            "sharpe_daily": float(sr_d),
            "skew": float(skew), "kurt": float(kurt),
            "max_dd": float(dd.max()),
            "psr_vs_0": float(stats.psr(sr_d, len(net), skew, kurt)),
            "cost_drag_ann": float(np.mean(costs) * ANN),
            "gross_ann": float(np.mean(gross) * ANN),
            "turnover_ann_oneway": float(turnover[:-1][score_mask[1:]].sum() / years),
            "round_trips_per_yr": float(rts / years),
            "hit_rate": float(wins / rts) if rts else None,
            "round_trips_total": rts,
            "avg_exposure": float(held[score_mask].sum(axis=1).mean()),
            "t_days": len(net),
        },
    }


def bh_benchmarks(rets: dict[str, np.ndarray], days: list[date],
                  score_mask: np.ndarray) -> dict[str, np.ndarray]:
    """BH_BTC (enter once) and BH_5050 (monthly rebalance, costs charged)."""
    T = len(days)
    r = np.column_stack([rets[a] for a in ASSETS])
    out = {}
    net = np.zeros(T)
    net[1:] = r[1:, 0]
    net[np.argmax(score_mask)] -= FEE + SLIP["BTC"]  # one entry at window start
    out["BH_BTC"] = net[score_mask]

    v = np.array([0.5, 0.5])
    net2 = np.zeros(T)
    started = False
    for t in range(1, T):
        if not score_mask[t]:
            continue
        if not started:
            net2[t] -= FEE + (SLIP["BTC"] + SLIP["ETH"]) / 2
            started = True
        growth = v * (1 + r[t])
        net2[t] += growth.sum() - v.sum()   # = sum(v * r), v normalized to 1
        v = growth / growth.sum()           # drifted weights
        if days[t].month != days[t - 1].month:  # first day of month: rebalance
            trade = np.abs(v - 0.5).sum()
            cost = trade * (FEE + (SLIP["BTC"] + SLIP["ETH"]) / 2)
            net2[t] -= cost
            v = np.array([0.5, 0.5])
    out["BH_5050"] = net2[score_mask]
    return out


# ---- main --------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-defect", default=None,
                    help="Re-run ONLY for a pre-run-review confirmed code defect; "
                         "the reason is registered.")
    args = ap.parse_args()

    if RESULTS_JSON.exists() and not args.force_defect:
        print(f"REFUSED: {RESULTS_JSON} exists. One-shot protocol "
              "(docs/b2-preregistration.md §7).")
        return 1

    daily = {a: load_daily(a) for a in ASSETS}
    days_btc = daily["BTC"]["day"].to_list()
    assert days_btc == daily["ETH"]["day"].to_list(), "asset calendars differ"
    closes = {a: daily[a]["close"].to_numpy().astype(float) for a in ASSETS}
    rets = {
        a: np.diff(closes[a], prepend=closes[a][0])
        / np.concatenate(([closes[a][0]], closes[a][:-1]))
        for a in ASSETS
    }
    for a in ASSETS:
        rets[a][0] = 0.0
    vols = {a: sizing.ewma_vol_annualized(rets[a]) for a in ASSETS}
    hv = {a: highvol_flags(vols[a]) for a in ASSETS}
    score_mask = np.array([d >= SCORE_START for d in days_btc])
    print(f"days={len(days_btc)} ({days_btc[0]} -> {days_btc[-1]}), scored={score_mask.sum()}")

    # 2) register INTENT for all identities before any evaluation
    note = "b2 pre-registered grid (docs/b2-preregistration.md)"
    if args.force_defect:
        note += f" | RE-RUN after confirmed defect: {args.force_defect}"
    trial_ids = {}
    for name, horizon, cfg in CANDIDATES:
        public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
        trial_ids[name] = registry.register_trial(PHASE, name, horizon, public_cfg, notes=note)
    n_union = registry.n_trials()
    print(f"registered {len(CANDIDATES)} identities; union N = {n_union}")

    # 3) evaluate once
    family_scalars = {}
    results = {}
    for name, _horizon, cfg in CANDIDATES:
        if cfg["kind"] == "combo":
            continue
        sc = scalars_for(cfg, closes, family_scalars)
        family_scalars[name] = sc
        results[name] = run_config(sc, rets, vols, hv, score_mask)

    included = [f for f in COMBO_FAMILIES
                if results[f]["metrics"]["cost_drag_ann"] <= DRAG_LIMIT]
    combo_cfg = dict(CANDIDATES[-1][2])
    combo_cfg["_included"] = included or None
    if included:
        sc = scalars_for(combo_cfg, closes, family_scalars)
    else:  # frozen fallback
        sc = family_scalars["S1_SMA200_HOLD"]
    results["COMBO"] = run_config(sc, rets, vols, hv, score_mask)
    results["COMBO"]["metrics"]["included_families"] = included

    # benchmarks
    bench = {}
    vt = run_config({a: np.ones(len(days_btc)) for a in ASSETS}, rets, vols, hv, score_mask)
    bench["VT_5050"] = vt["metrics"]
    for bname, series in bh_benchmarks(rets, days_btc, score_mask).items():
        sr_d = stats.sharpe(series)
        eq = np.cumprod(1 + series)
        bench[bname] = {
            "ann_return": float(series.mean() * ANN),
            "ann_vol": float(series.std(ddof=1) * np.sqrt(ANN)),
            "sharpe_ann": float(sr_d * np.sqrt(ANN)),
            "max_dd": float((1 - eq / np.maximum.accumulate(eq)).max()),
        }
    bench["CASH"] = {"ann_return": 0.0, "ann_vol": 0.0, "sharpe_ann": 0.0, "max_dd": 0.0}

    # DSR (frozen: N = union registry, var = cross-section of the 7 candidates)
    daily_srs = [stats.sharpe(results[n]["net_daily"]) for n, _, _ in CANDIDATES]
    var_trials = float(np.var(daily_srs, ddof=1))
    for name, _, _ in CANDIDATES:
        m = results[name]["metrics"]
        m["dsr"] = float(stats.dsr(m["sharpe_daily"], m["t_days"], n_union, var_trials,
                                   m["skew"], m["kurt"]))

    # PBO across the 7 candidates
    matrix = np.column_stack([results[n]["net_daily"] for n, _, _ in CANDIDATES])
    pbo = stats.pbo_cscv(matrix, n_blocks=16)

    # per-year table
    years_list = sorted({d.year for d, m in zip(days_btc, score_mask, strict=True) if m})
    per_year = {}
    scored_days = [d for d, m in zip(days_btc, score_mask, strict=True) if m]
    for name, _, _ in CANDIDATES:
        net = results[name]["net_daily"]
        per_year[name] = {
            str(y): float(stats.sharpe(np.array([x for d, x in zip(scored_days, net, strict=True)
                                                 if d.year == y])) * np.sqrt(ANN))
            for y in years_list
        }

    # 4) frozen champion rule
    vt_sharpe = bench["VT_5050"]["sharpe_ann"]
    eligible = []
    for name, _, cfg in CANDIDATES:
        m = results[name]["metrics"]
        ok = (m["cost_drag_ann"] <= DRAG_LIMIT and m["max_dd"] <= MAXDD_LIMIT
              and m["sharpe_ann"] >= vt_sharpe)
        m["eligible"] = ok
        if ok:
            eligible.append((m["dsr"], -len(json.dumps(cfg)), -m["turnover_ann_oneway"], name))
    champion = max(eligible)[3] if eligible else None

    # log completed trials
    for name, horizon, cfg in CANDIDATES:
        public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
        m = {k: v for k, v in results[name]["metrics"].items()}
        registry.log_trial(PHASE, name, horizon, public_cfg, m,
                           notes=f"b2 one-shot result; champion={champion}")

    payload = {
        "protocol": "docs/b2-preregistration.md",
        "cutoff": str(CUTOFF), "score_start": str(SCORE_START),
        "n_union_registry": n_union, "var_trials_daily": var_trials,
        "pbo": pbo, "champion": champion,
        "vt_5050_sharpe_ann": vt_sharpe,
        "candidates": {n: results[n]["metrics"] for n, _, _ in CANDIDATES},
        "benchmarks": bench, "per_year_sharpe": per_year,
        "trial_ids": trial_ids,
        "included_families_combo": included,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("champion", "pbo", "vt_5050_sharpe_ann")}, indent=2))
    print(f"results -> {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
