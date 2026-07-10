# ruff: noqa: E501 - readability of report strings beats the line limit here
"""Validation harness for daily regime scores (CryptoAcademy Phase 4.3).

Input: a DataFrame with columns [date, risk_appetite, crypto_stress,
macro_stress, confidence], one row per calendar day (UTC).

All tests are CAUSAL in orientation: the regime score for day D is assumed
to be produced from information available up to the end of day D (23:59:59
UTC). Every outcome it is compared against is computed strictly from bars
whose open_time >= (D + 1 day) 00:00 UTC — i.e. the FORWARD 7-day window
[D+1d, D+8d). Nothing contemporaneous with day D enters the outcome, so a
passing gate is evidence of predictive value, not of the classifier merely
describing the day it just saw.

Checks implemented (see `validate_regime_scores`):
  1. spearman_stress_vs_fwd_vol : Spearman rho of crypto_stress(D) vs
     next-7-day realized vol, permutation-test p-value (one-sided,
     H1: rho > 0).                GATE: rho > 0.2 and p < 0.05.
  2. event_study_drawdown       : mean forward 7-day max drawdown
     (magnitude, >= 0) conditional on risk_appetite <= -1 (risk-off)
     vs >= +1 (risk-on).          GATE: dd(risk-off) > dd(risk-on).
  3. persistence                : mean run length (days) of
     sign(risk_appetite); row-normalized transition matrix of
     crypto_stress (transitions counted only between consecutive
     calendar days).              GATE: mean run >= 3 (5 preferred).
  4. auc_stress_extreme         : AUC of the binary flag
     (crypto_stress >= 2) ranking top-decile next-7d realized-vol days.
     Reported, no hard gate (0.5 = uninformative).

Degenerate inputs (constant series, empty conditional buckets, single
class) never raise: the affected check reports status "unavailable" with
a reason, and its gate is neither passed nor failed.

Realized vol for day D = sqrt( sum of squared 1h log close-to-close
returns over the 168 hourly bars in [D+1d, D+8d) ). Forward max drawdown
= max peak-to-trough decline of hourly closes in the same window,
reported as a positive fraction. Windows with < MIN_COVERAGE * 168 bars
(data gaps, end of history) yield null outcomes and are dropped from the
tests row-wise.

Dependencies: polars, numpy (stdlib otherwise).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import numpy as np
import polars as pl

from cryptoacademy import config

DEFAULT_KLINES = str(config.RAW_DIR / "klines" / "BTC" / "spot" / "BTCUSDT_1h.parquet")
FWD_HOURS = 168            # 7 * 24
MIN_COVERAGE = 0.90        # require >= 90% of the 168 forward bars
GATE_RHO = 0.2
GATE_P = 0.05
GATE_MEAN_RUN = 3.0
PREF_MEAN_RUN = 5.0
REQUIRED_COLS = ("date", "risk_appetite", "crypto_stress", "macro_stress", "confidence")


# --------------------------------------------------------------------------
# Forward-outcome construction from hourly klines
# --------------------------------------------------------------------------

def load_hourly_closes(klines_path: str = DEFAULT_KLINES) -> pl.DataFrame:
    """Load hourly klines, return sorted [open_time, close, log_ret]."""
    k = (
        pl.read_parquet(klines_path)
        .select("open_time", "close")
        .sort("open_time")
        .unique(subset="open_time", keep="first", maintain_order=True)
        .with_columns((pl.col("close") / pl.col("close").shift(1)).log().alias("log_ret"))
    )
    return k


def compute_forward_outcomes(klines: pl.DataFrame) -> pl.DataFrame:
    """Per calendar day D (UTC): forward realized vol and max drawdown over
    the hourly bars with open_time in [D+1d, D+8d).

    Returns [date, fwd_vol_7d, fwd_maxdd_7d, fwd_n_bars]; outcomes are null
    when bar coverage < MIN_COVERAGE * FWD_HOURS (gaps / end of history).
    """
    # ns since epoch, numpy views
    t_ns = klines["open_time"].dt.epoch(time_unit="ns").to_numpy()
    close = klines["close"].to_numpy()
    r2 = np.square(np.nan_to_num(klines["log_ret"].to_numpy(), nan=0.0))
    cum_r2 = np.concatenate(([0.0], np.cumsum(r2)))  # cum_r2[j] = sum r2[:j]

    d0 = klines["open_time"].dt.date().min()
    d1 = klines["open_time"].dt.date().max()
    dates = [d0 + _dt.timedelta(days=i) for i in range((d1 - d0).days + 1)]

    day_ns = 24 * 3600 * 10**9
    epoch = _dt.date(1970, 1, 1)
    starts = np.array([((d - epoch).days + 1) * day_ns for d in dates])  # D+1d 00:00
    ends = starts + 7 * day_ns                                           # D+8d 00:00
    i0 = np.searchsorted(t_ns, starts, side="left")
    i1 = np.searchsorted(t_ns, ends, side="left")
    n_bars = i1 - i0
    min_bars = int(MIN_COVERAGE * FWD_HOURS)

    vols = np.full(len(dates), np.nan)
    dds = np.full(len(dates), np.nan)
    for j in range(len(dates)):
        if n_bars[j] < min_bars:
            continue
        a, b = int(i0[j]), int(i1[j])
        vols[j] = np.sqrt(cum_r2[b] - cum_r2[a])
        c = close[a:b]
        dds[j] = float(np.max(1.0 - c / np.maximum.accumulate(c)))  # >= 0

    return pl.DataFrame(
        {
            "date": dates,
            "fwd_vol_7d": vols,
            "fwd_maxdd_7d": dds,
            "fwd_n_bars": n_bars,
        }
    ).with_columns(
        pl.when(pl.col("fwd_vol_7d").is_nan()).then(None).otherwise(pl.col("fwd_vol_7d")).alias("fwd_vol_7d"),
        pl.when(pl.col("fwd_maxdd_7d").is_nan()).then(None).otherwise(pl.col("fwd_maxdd_7d")).alias("fwd_maxdd_7d"),
    )


# --------------------------------------------------------------------------
# Stats primitives (no scipy)
# --------------------------------------------------------------------------

def _midranks(x: np.ndarray) -> np.ndarray:
    """Average ranks (1-based) with midrank tie handling."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    xs = x[order]
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return ranks


def spearman_rho(x: np.ndarray, y: np.ndarray) -> float | None:
    """Spearman rho with midranks. None if either side has zero variance."""
    rx, ry = _midranks(x), _midranks(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0.0 or sy == 0.0:
        return None
    return float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (sx * sy))


def permutation_pvalue(
    x: np.ndarray, y: np.ndarray, rho_obs: float, n_perm: int, rng: np.random.Generator
) -> float:
    """One-sided permutation p-value for H1: rho > 0 (shuffle x vs fixed y)."""
    ry = _midranks(y)
    rx = _midranks(x)
    rxc = rx - rx.mean()
    ryc = ry - ry.mean()
    denom = rx.std() * ry.std() * len(x)
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(len(x))
        rho_p = float(np.dot(rxc[perm], ryc)) / denom
        if rho_p >= rho_obs:
            hits += 1
    return (1 + hits) / (n_perm + 1)


def binary_score_auc(score: np.ndarray, label: np.ndarray) -> float | None:
    """Mann-Whitney AUC of `score` ranking `label` (1 = positive).
    Midrank tie handling; None if a class or the score is degenerate."""
    n_pos = int(label.sum())
    n_neg = len(label) - n_pos
    if n_pos == 0 or n_neg == 0 or np.all(score == score[0]):
        return None
    r = _midranks(score)
    return float((r[label == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _run_lengths(vals: np.ndarray) -> list[int]:
    """Lengths of maximal runs of equal consecutive values."""
    if len(vals) == 0:
        return []
    runs, cur = [], 1
    for i in range(1, len(vals)):
        if vals[i] == vals[i - 1]:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    return runs


# --------------------------------------------------------------------------
# The four checks
# --------------------------------------------------------------------------

def check_spearman_stress_vol(joined: pl.DataFrame, n_perm: int, rng: np.random.Generator) -> dict:
    d = joined.drop_nulls(["crypto_stress", "fwd_vol_7d"])
    out: dict[str, Any] = {"n": d.height}
    if d.height < 30:
        out.update(status="unavailable", reason=f"only {d.height} usable rows (<30)", gate=None)
        return out
    x = d["crypto_stress"].to_numpy().astype(float)
    y = d["fwd_vol_7d"].to_numpy().astype(float)
    rho = spearman_rho(x, y)
    if rho is None:
        out.update(status="unavailable", reason="zero variance in crypto_stress or fwd vol", gate=None)
        return out
    p = permutation_pvalue(x, y, rho, n_perm, rng)
    out.update(
        status="ok", rho=rho, p_value=p, n_perm=n_perm,
        gate=bool(rho > GATE_RHO and p < GATE_P),
        gate_rule=f"rho > {GATE_RHO} and p < {GATE_P}",
    )
    return out


def check_event_study_drawdown(joined: pl.DataFrame) -> dict:
    d = joined.drop_nulls(["risk_appetite", "fwd_maxdd_7d"])
    off = d.filter(pl.col("risk_appetite") <= -1)["fwd_maxdd_7d"]
    on = d.filter(pl.col("risk_appetite") >= 1)["fwd_maxdd_7d"]
    out: dict[str, Any] = {"n_risk_off": off.len(), "n_risk_on": on.len()}
    if off.len() < 5 or on.len() < 5:
        out.update(
            status="unavailable",
            reason=f"insufficient bucket sizes (risk-off={off.len()}, risk-on={on.len()}, need >=5 each)",
            gate=None,
        )
        return out
    m_off, m_on = float(off.mean()), float(on.mean())
    # Welch t-stat (informational only; overlapping forward windows make
    # observations serially dependent, so this overstates significance —
    # use it to spot coin-flip sign passes, not as a formal test)
    v_off = float(off.var()) / off.len()
    v_on = float(on.var()) / on.len()
    t_stat = (m_off - m_on) / np.sqrt(v_off + v_on) if (v_off + v_on) > 0 else None
    out.update(
        status="ok",
        mean_fwd_maxdd_risk_off=m_off,
        mean_fwd_maxdd_risk_on=m_on,
        difference=m_off - m_on,
        welch_t_informational=t_stat,
        gate=bool(m_off > m_on),
        gate_rule="mean fwd 7d max drawdown after risk-off > after risk-on",
    )
    return out


def check_persistence(regime: pl.DataFrame) -> dict:
    d = regime.drop_nulls(["risk_appetite"]).sort("date")
    out: dict[str, Any] = {"n": d.height}
    if d.height == 0:
        out.update(status="unavailable", reason="no rows", gate=None)
        return out
    sign = np.sign(d["risk_appetite"].to_numpy().astype(float)).astype(int)
    runs = _run_lengths(sign)
    mean_run = float(np.mean(runs))
    # transition matrix of crypto_stress, consecutive calendar days only
    ds = regime.drop_nulls(["crypto_stress"]).sort("date")
    states = sorted(ds["crypto_stress"].unique().to_list())
    idx = {s: i for i, s in enumerate(states)}
    counts = np.zeros((len(states), len(states)))
    dates = ds["date"].to_list()
    stress = ds["crypto_stress"].to_list()
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            counts[idx[stress[i - 1]], idx[stress[i]]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        tm = np.where(row_sums > 0, counts / row_sums, np.nan)
    out.update(
        status="ok",
        mean_run_length_days=mean_run,
        n_runs=len(runs),
        max_run_length_days=int(max(runs)),
        stress_states=states,
        stress_transition_matrix=[[None if np.isnan(v) else round(float(v), 4) for v in row] for row in tm],
        stress_n_transitions=int(row_sums.sum()),
        gate=bool(mean_run >= GATE_MEAN_RUN),
        gate_rule=f"mean run >= {GATE_MEAN_RUN} days ({PREF_MEAN_RUN} preferred)",
        meets_preferred=bool(mean_run >= PREF_MEAN_RUN),
        degenerate=bool(len(runs) == 1 or len(states) <= 1),
    )
    return out


def check_auc_stress_extreme(joined: pl.DataFrame) -> dict:
    d = joined.drop_nulls(["crypto_stress", "fwd_vol_7d"])
    out: dict[str, Any] = {"n": d.height}
    if d.height < 30:
        out.update(status="unavailable", reason=f"only {d.height} usable rows (<30)", gate=None)
        return out
    vol = d["fwd_vol_7d"].to_numpy().astype(float)
    thr = float(np.quantile(vol, 0.9))
    label = (vol >= thr).astype(int)
    score = (d["crypto_stress"].to_numpy().astype(float) >= 2).astype(float)
    auc = binary_score_auc(score, label)
    if auc is None:
        out.update(status="unavailable", reason="degenerate score (crypto_stress>=2 never varies) or single-class labels", gate=None)
        return out
    out.update(
        status="ok", auc=auc,
        n_top_decile=int(label.sum()),
        n_flagged=int(score.sum()),
        top_decile_vol_threshold=thr,
        gate=None, gate_rule="informational (0.5 = uninformative)",
    )
    return out


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def validate_regime_scores(
    regime: pl.DataFrame,
    klines_path: str = DEFAULT_KLINES,
    n_perm: int = 1000,
    seed: int = 42,
    outcomes: pl.DataFrame | None = None,
) -> dict:
    """Run all quality gates. `outcomes` may be passed to reuse a
    precomputed compute_forward_outcomes() frame (else built from
    klines_path). Returns a nested dict; see module docstring."""
    missing = [c for c in REQUIRED_COLS if c not in regime.columns]
    if missing:
        raise ValueError(f"regime frame missing columns: {missing}")
    regime = regime.with_columns(pl.col("date").cast(pl.Date)).sort("date")
    if outcomes is None:
        outcomes = compute_forward_outcomes(load_hourly_closes(klines_path))
    joined = regime.join(outcomes, on="date", how="left")
    n_no_outcome = joined["fwd_vol_7d"].null_count()

    rng = np.random.default_rng(seed)
    results = {
        "meta": {
            "n_regime_days": regime.height,
            "date_range": (str(regime["date"].min()), str(regime["date"].max())),
            "n_days_without_forward_outcome": n_no_outcome,
            "causality": "regime(D) vs outcomes over [D+1d 00:00, D+8d 00:00) UTC — strictly forward",
        },
        "spearman_stress_vs_fwd_vol": check_spearman_stress_vol(joined, n_perm, rng),
        "event_study_drawdown": check_event_study_drawdown(joined),
        "persistence": check_persistence(regime),
        "auc_stress_extreme": check_auc_stress_extreme(joined),
    }
    gates = {
        name: results[name].get("gate")
        for name in ("spearman_stress_vs_fwd_vol", "event_study_drawdown", "persistence")
    }
    results["summary"] = {
        "gates": gates,
        "all_gates_pass": all(v is True for v in gates.values()),
        "any_unavailable": any(v is None for v in gates.values()),
    }
    return results


def format_report(results: dict) -> str:
    """Human-readable multi-line report."""
    lines = []
    m = results["meta"]
    lines.append(f"Regime validation — {m['n_regime_days']} days {m['date_range'][0]}..{m['date_range'][1]}")
    lines.append(f"  causality: {m['causality']}")
    lines.append(f"  days lacking forward outcome (gaps/end of data): {m['n_days_without_forward_outcome']}")

    def gate_str(g):
        return "PASS" if g is True else ("FAIL" if g is False else "UNAVAILABLE")

    r = results["spearman_stress_vs_fwd_vol"]
    if r["status"] == "ok":
        lines.append(f"[1] Spearman crypto_stress vs fwd 7d vol: rho={r['rho']:+.4f}, "
                     f"perm p={r['p_value']:.4f} (n={r['n']})  GATE({r['gate_rule']}): {gate_str(r['gate'])}")
    else:
        lines.append(f"[1] Spearman: UNAVAILABLE — {r['reason']}")

    r = results["event_study_drawdown"]
    if r["status"] == "ok":
        lines.append(f"[2] Event study fwd 7d maxDD: risk-off={r['mean_fwd_maxdd_risk_off']:.4f} "
                     f"(n={r['n_risk_off']}), risk-on={r['mean_fwd_maxdd_risk_on']:.4f} (n={r['n_risk_on']}), "
                     f"diff={r['difference']:+.4f}"
                     + (f" (Welch t~{r['welch_t_informational']:.2f}, informational)"
                        if r.get("welch_t_informational") is not None else "")
                     + f"  GATE: {gate_str(r['gate'])}")
    else:
        lines.append(f"[2] Event study: UNAVAILABLE — {r['reason']}")

    r = results["persistence"]
    if r["status"] == "ok":
        lines.append(f"[3] Persistence: mean run={r['mean_run_length_days']:.2f}d "
                     f"({r['n_runs']} runs, max {r['max_run_length_days']}d)  "
                     f"GATE(>=3d): {gate_str(r['gate'])}"
                     + ("  [meets preferred >=5d]" if r.get("meets_preferred") else "")
                     + ("  [DEGENERATE: single run or single stress state]" if r.get("degenerate") else ""))
        lines.append(f"    crypto_stress states {r['stress_states']}, "
                     f"{r['stress_n_transitions']} day-to-day transitions; P=")
        for s, row in zip(r["stress_states"], r["stress_transition_matrix"], strict=True):
            lines.append(f"      {s}: {row}")
    else:
        lines.append(f"[3] Persistence: UNAVAILABLE — {r['reason']}")

    r = results["auc_stress_extreme"]
    if r["status"] == "ok":
        lines.append(f"[4] AUC (crypto_stress>=2 -> top-decile fwd vol): {r['auc']:.4f} "
                     f"(flagged {r['n_flagged']}/{r['n']}, positives {r['n_top_decile']}) [informational]")
    else:
        lines.append(f"[4] AUC: UNAVAILABLE — {r['reason']}")

    s = results["summary"]
    lines.append(f"SUMMARY: gates={s['gates']}  all_pass={s['all_gates_pass']}"
                 + ("  (some gates unavailable)" if s["any_unavailable"] else ""))
    return "\n".join(lines)
