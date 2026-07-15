"""B2.1 one-shot evaluation (protocol: docs/b2.1-preregistration.md, FROZEN).

Scope (stopping rule): the frozen B2 champion at vol target 0.20, with and
without the frozen cash-yield convention. No new families, no re-ranking.
Registers intent → evaluates once → persists DAILY ARTIFACTS (methodology
audit fix #1) → applies the frozen adoption rule.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import date, timedelta

import httpx
import numpy as np
import polars as pl

from cryptoacademy import config
from cryptoacademy.validation import registry, stats

sys.path.insert(0, r"C:\CryptoBot\src")
from cryptobot.engine import sizing, strategies

# frozen constants (b2.1-preregistration + b2-preregistration)
CUTOFF = date(2026, 7, 11)
SCORE_START = date(2021, 1, 1)
FEE = 0.0010
SLIP = {"BTC": 0.0005, "ETH": 0.0010}
HIGHVOL_PCT, HIGHVOL_WARMUP = 0.80, 365
ANN = 365
PHASE = "bot-b2.1"
ASSETS = ("BTC", "ETH")
VT_NEW = 0.20
VT12_SHARPE, VT12_MAXDD = 1.014, 0.068  # B2 champion, from b2_results.json

OUT = config.DATA_DIR / "b2"
RESULTS_JSON = OUT / "b21_results.json"
DAILY_PARQUET = OUT / "b21_daily.parquet"
DTB3_CSV = OUT / "dtb3.csv"


def load_daily(asset: str) -> pl.DataFrame:
    import itertools

    path = config.RAW_DIR / "klines" / asset / "spot" / f"{asset}USDT_1h.parquet"
    df = (
        pl.read_parquet(path)
        .sort("open_time")
        .with_columns(pl.col("open_time").dt.date().alias("day"))
        .group_by("day", maintain_order=True)
        .agg(pl.col("close").last())
        .sort("day")
        .filter(pl.col("day") <= CUTOFF)
    )
    days = df["day"].to_list()
    if [g for g in itertools.pairwise(days) if (g[1] - g[0]).days != 1]:
        raise RuntimeError(f"{asset}: daily gaps")
    if days[0] != date(2020, 1, 1):
        raise RuntimeError(f"{asset}: series must start 2020-01-01")
    return df


def highvol_flags(vol_ann: np.ndarray) -> np.ndarray:
    flags = np.zeros(len(vol_ann), dtype=bool)
    for t in range(HIGHVOL_WARMUP, len(vol_ann)):
        flags[t] = vol_ann[t] > np.quantile(vol_ann[: t + 1], HIGHVOL_PCT)
    return flags


def fetch_dtb3(days: list[date]) -> np.ndarray:
    """DTB3 (FRED public CSV), applied with the frozen t-2 publication lag and
    forward-fill; saved locally for reproducibility."""
    if DTB3_CSV.exists():
        raw = DTB3_CSV.read_text(encoding="utf-8")
    else:
        r = httpx.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3",
            timeout=60, follow_redirects=True,
        )
        r.raise_for_status()
        raw = r.text
        OUT.mkdir(parents=True, exist_ok=True)
        DTB3_CSV.write_text(raw, encoding="utf-8")
    df = pl.read_csv(io.StringIO(raw), try_parse_dates=True)
    published: dict[date, float] = {}
    for row in df.iter_rows():
        try:
            published[row[0]] = float(row[1]) / 100.0
        except (TypeError, ValueError):
            continue  # '.' placeholder days
    rate = np.zeros(len(days))
    last = 0.0
    lookup_floor = min(published) if published else None
    for i, d in enumerate(days):
        target = d - timedelta(days=2)  # frozen publication lag
        while lookup_floor and target >= lookup_floor and target not in published:
            target -= timedelta(days=1)
        if target in published:
            last = published[target]
        rate[i] = max(last, 0.0)
    return rate


def run(scalars, rets, vols, hv, score_mask, vol_target, yield_rate=None):
    """Same engine as B2 run_config, parametrized vol target + optional yield."""
    T = len(score_mask)
    scal = np.column_stack([scalars[a] for a in ASSETS])
    vol = np.column_stack([vols[a] for a in ASSETS])
    targets = sizing.target_weights(scal, vol, vol_target=vol_target)
    held = sizing.apply_buffer(targets)
    turnover = np.abs(np.diff(held, axis=0, prepend=np.zeros((1, len(ASSETS)))))
    side_cost = np.column_stack([FEE + SLIP[a] * np.where(hv[a], 2.0, 1.0) for a in ASSETS])
    daily_cost = (turnover * side_cost).sum(axis=1)
    r = np.column_stack([rets[a] for a in ASSETS])
    port = np.zeros(T)
    port[1:] = (held[:-1] * r[1:]).sum(axis=1) - daily_cost[:-1]
    gross_exp = held.sum(axis=1)
    if yield_rate is not None:
        idle = 1.0 - np.maximum(gross_exp, np.concatenate(([0.0], gross_exp[:-1])))
        port = port + np.clip(idle, 0, 1) * yield_rate / ANN
    net = port[score_mask]
    years = len(net) / ANN
    equity = np.cumprod(1 + net)
    dd = 1 - equity / np.maximum.accumulate(equity)
    sr_d = stats.sharpe(net)
    skew, kurt = stats._moments(net)
    active = net[gross_exp[score_mask] > 1e-9]
    m = {
        "ann_return": float(np.mean(net) * ANN),
        "ann_vol": float(np.std(net, ddof=1) * np.sqrt(ANN)),
        "sharpe_ann_rf0": float(sr_d * np.sqrt(ANN)),
        "max_dd": float(dd.max()),
        "psr_vs_0": float(stats.psr(sr_d, len(net), skew, kurt)),
        "skew": float(skew), "kurt": float(kurt),
        "cost_drag_ann": float(np.mean(daily_cost[:-1][score_mask[1:]]) * ANN),
        "turnover_ann_oneway": float(turnover[:-1][score_mask[1:]].sum() / years),
        "avg_exposure": float(gross_exp[score_mask].mean()),
        "time_in_market": float((gross_exp[score_mask] > 1e-9).mean()),
        "sharpe_active_days": (
            float(stats.sharpe(active) * np.sqrt(ANN)) if len(active) > 2 else None
        ),
        "t_days": len(net),
    }
    return {"net_daily": net, "held": held[score_mask], "metrics": m}


def main() -> int:
    if RESULTS_JSON.exists():
        print(f"REFUSED: {RESULTS_JSON} exists (one-shot; see b2.1 prereg §5).")
        return 1
    daily = {a: load_daily(a) for a in ASSETS}
    days = daily["BTC"]["day"].to_list()
    assert days == daily["ETH"]["day"].to_list()
    closes = {a: daily[a]["close"].to_numpy().astype(float) for a in ASSETS}
    rets = {}
    for a in ASSETS:
        c = closes[a]
        rr = np.diff(c, prepend=c[0]) / np.concatenate(([c[0]], c[:-1]))
        rr[0] = 0.0
        rets[a] = rr
    vols = {a: sizing.ewma_vol_annualized(rets[a]) for a in ASSETS}
    hv = {a: highvol_flags(vols[a]) for a in ASSETS}
    mask = np.array([d >= SCORE_START for d in days])
    dtb3 = fetch_dtb3(days)
    print(f"days={len(days)}, scored={mask.sum()}, DTB3 mean={dtb3[mask].mean():.3%}")

    # register intent (2 identities) BEFORE evaluating
    cfgs = {
        "S2_DONCH_N20_VT20": {"base": "c0fbd4d88776", "vol_target": 0.20, "yield": None},
        "S2_DONCH_N20_VT20_YIELD": {"base": "c0fbd4d88776", "vol_target": 0.20,
                                     "yield": "DTB3 t-2 lag, idle=1-max(g_t,g_t-1)"},
    }
    tids = {n: registry.register_trial(PHASE, n, "96h", c,
                                       notes="b2.1 frozen round (docs/b2.1-preregistration.md)")
            for n, c in cfgs.items()}
    n_union = registry.n_trials()

    # champion scalars (identical rules)
    scalars = {}
    for a in ASSETS:
        gate = strategies.s1_gate(closes[a], 200)
        scalars[a] = strategies.s2_donchian(closes[a], 20, 10, gate=gate)
    ones = {a: np.ones(len(days)) for a in ASSETS}

    res = {
        "S2_DONCH_N20_VT20": run(scalars, rets, vols, hv, mask, VT_NEW),
        "S2_DONCH_N20_VT20_YIELD": run(scalars, rets, vols, hv, mask, VT_NEW, dtb3),
        "BENCH_VT20_5050": run(ones, rets, vols, hv, mask, VT_NEW),
        "BENCH_VT20_5050_YIELD": run(ones, rets, vols, hv, mask, VT_NEW, dtb3),
        "BENCH_VT12_CHAMPION_YIELD": run(scalars, rets, vols, hv, mask, 0.12, dtb3),
        "BENCH_CASH_YIELD": run(
            {a: np.zeros(len(days)) for a in ASSETS}, rets, vols, hv, mask, VT_NEW, dtb3
        ),
    }

    # excess-of-cash Sharpe (dual convention) + year clusters
    cash = res["BENCH_CASH_YIELD"]["net_daily"]
    scored_days = [d for d, x in zip(days, mask, strict=True) if x]
    years_list = sorted({d.year for d in scored_days})
    for _name, r_ in res.items():
        ex = r_["net_daily"] - cash
        r_["metrics"]["sharpe_ann_excess_cash"] = float(stats.sharpe(ex) * np.sqrt(ANN))
        ys = []
        for y in years_list:
            yv = np.array(
                [v for d, v in zip(scored_days, r_["net_daily"], strict=True) if d.year == y]
            )
            ys.append(float(stats.sharpe(yv) * np.sqrt(ANN)))
        r_["metrics"]["per_year_sharpe"] = dict(zip(map(str, years_list), ys, strict=True))
        arr = np.array(ys[:-1])  # full years only
        r_["metrics"]["year_cluster"] = {
            "mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)),
            "t": float(arr.mean() / (arr.std(ddof=1) / np.sqrt(len(arr)))),
        }

    # frozen rails formula + adoption rule
    m20 = res["S2_DONCH_N20_VT20"]["metrics"]
    maxdd20 = m20["max_dd"]
    rails = {
        "soft_derisk": round(max(0.10, 1.05 * maxdd20), 2),
        "hard_kill": 0.20 if maxdd20 <= 0.12 else round(min(1.8 * maxdd20, 0.25), 2),
        "daily_loss_pause": 0.04, "daily_loss_kill": 0.08,
    }
    adopted = (
        m20["sharpe_ann_rf0"] >= VT12_SHARPE - 0.15
        and maxdd20 <= 2.2 * VT12_MAXDD
        and m20["cost_drag_ann"] <= 0.10
    )

    for n, c in cfgs.items():
        registry.log_trial(PHASE, n, "96h", c, res[n]["metrics"],
                           notes=f"b2.1 one-shot; adopted={adopted}; rails={rails}")

    # persist daily artifacts (methodology fix #1)
    frames = {"day": [str(d) for d in scored_days]}
    for n, r_ in res.items():
        frames[f"{n}__net"] = r_["net_daily"].tolist()
        for i, a in enumerate(ASSETS):
            frames[f"{n}__w_{a}"] = r_["held"][:, i].tolist()
    pl.DataFrame(frames).write_parquet(DAILY_PARQUET)

    payload = {
        "protocol": "docs/b2.1-preregistration.md",
        "paper_equity_usdt": 1000,
        "n_union_registry": n_union,
        "adopted_vt20_yield": bool(adopted),
        "rails_derived": rails,
        "trial_ids": tids,
        "results": {n: r_["metrics"] for n, r_ in res.items()},
    }
    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("adopted_vt20_yield", "rails_derived")}, indent=2))
    for n, r_ in res.items():
        m = r_["metrics"]
        print(f"{n:28} ret={m['ann_return']:7.3f} vol={m['ann_vol']:6.3f} "
              f"SR0={m['sharpe_ann_rf0']:5.2f} SRxc={m['sharpe_ann_excess_cash']:5.2f} "
              f"DD={m['max_dd']:6.3f} drag={m['cost_drag_ann']:6.4f}")
    print(f"results -> {RESULTS_JSON}\ndaily artifacts -> {DAILY_PARQUET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
