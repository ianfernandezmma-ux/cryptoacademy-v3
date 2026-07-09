"""Event sampling (CUSUM) + triple-barrier labeling + sample weights.

Clean-room implementation against the AFML spec (López de Prado 2018) with the
crypto-specific conventions validated in Grądzki, Wójcik & Lessmann (2025,
Financial Innovation). Audited against the known bug checklist:

  1. sigma used for barriers at t0 is computed from returns ending <= t0.
  2. The barrier-touch scan starts at t0+1 (the decision bar's own high/low
     happened before our entry at its close).
  3. Events whose vertical window extends past the data end are DROPPED,
     never truncated.
  4. Touch detection uses 1h high/low (what a resting order would see).
  5. Double-touch within one bar resolves pessimistically (stop-loss first).
  6. EWM sigma carries min_periods so early-sample barriers aren't garbage.
  7. Concurrency is counted over full [t0, t1] spans.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl


def daily_vol_on_hourly(close: np.ndarray, span_days: int = 100, min_days: int = 30) -> np.ndarray:
    """EWM std of 24h log returns sampled on the hourly grid (AFML getDailyVol).

    Causal: sigma[t] uses only returns that END at or before bar t.
    """
    n = len(close)
    r = np.full(n, np.nan)
    r[24:] = np.log(close[24:] / close[:-24])
    alpha = 2.0 / (span_days * 24 + 1)
    sigma = np.full(n, np.nan)
    mean = var = 0.0
    count = 0
    for t in range(n):
        x = r[t]
        if not np.isnan(x):
            count += 1
            if count == 1:
                mean, var = x, 0.0
            else:
                delta = x - mean
                mean += alpha * delta
                var = (1 - alpha) * (var + alpha * delta * delta)
        if count >= min_days * 24:
            sigma[t] = np.sqrt(var)
    return sigma


def cusum_events(close: np.ndarray, threshold: np.ndarray) -> np.ndarray:
    """Symmetric CUSUM filter on log returns with a per-bar dynamic threshold.

    AFML one-sided reset: only the accumulator that fired is zeroed.
    Returns indices of event bars.
    """
    events = []
    s_pos = s_neg = 0.0
    logc = np.log(close)
    for t in range(1, len(close)):
        r = logc[t] - logc[t - 1]
        s_pos = max(0.0, s_pos + r)
        s_neg = min(0.0, s_neg + r)
        h = threshold[t]
        if np.isnan(h):
            continue
        if s_pos >= h:
            events.append(t)
            s_pos = 0.0
        elif s_neg <= -h:
            events.append(t)
            s_neg = 0.0
    return np.asarray(events, dtype=np.int64)


@dataclass
class TripleBarrierConfig:
    pt_mult: float = 2.0          # profit-take = pt_mult * trgt
    sl_mult: float = 2.0          # stop-loss  = sl_mult * trgt (symmetric primary)
    horizon_bars: int = 120       # vertical barrier: 5 days of 1h bars
    vertical_label: str = "sign"  # "sign" (AFML A) or "zero" (3-class B)
    min_trgt: float = 1e-4        # drop events with negligible vol target


def triple_barrier(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    event_idx: np.ndarray,
    sigma: np.ndarray,
    cfg: TripleBarrierConfig,
    side: np.ndarray | None = None,
) -> pl.DataFrame:
    """Label events. Returns one row per SURVIVING event:
    t0_idx, t1_idx (actual touch bar), label, ret, trgt, touch ('up'|'down'|'vertical').

    With `side` given (meta-labeling), barriers apply to side-adjusted returns
    and the label is binary {0,1}: did the primary's call make money.
    """
    n = len(close)
    horizon_scale = np.sqrt(cfg.horizon_bars / 24.0)  # sigma is daily; scale to H
    out = []
    n_double = 0
    for k, t0 in enumerate(event_idx):
        trgt = sigma[t0] * horizon_scale
        if np.isnan(trgt) or trgt < cfg.min_trgt:
            continue
        t1_max = t0 + cfg.horizon_bars
        if t1_max >= n:
            continue  # DROP: full window not observed
        s = 1.0 if side is None else float(side[k])
        p0 = close[t0]
        up = p0 * (1 + cfg.pt_mult * trgt) if s > 0 else p0 * (1 + cfg.sl_mult * trgt)
        dn = p0 * (1 - cfg.sl_mult * trgt) if s > 0 else p0 * (1 - cfg.pt_mult * trgt)

        label = None
        touch = "vertical"
        t1 = t1_max
        adverse = "down" if s > 0 else "up"  # the stop-loss side for this trade
        for i in range(t0 + 1, t1_max + 1):  # scan starts at t0+1
            hit_up = high[i] >= up
            hit_dn = low[i] <= dn
            if hit_up and hit_dn:
                n_double += 1
                # pessimistic tie-break: the adverse barrier is deemed first
                hit_up = adverse == "up"
                hit_dn = adverse == "down"
            if hit_up:
                touch, t1 = "up", i
                label = 1 if s > 0 else -1
                break
            if hit_dn:
                touch, t1 = "down", i
                label = -1 if s > 0 else 1
                break
        # a touched barrier fills AT the barrier price (a wick-only touch would
        # otherwise report the bar's close and mislabel the trade's PnL)
        if touch == "up":
            ret = up / p0 - 1.0
        elif touch == "down":
            ret = dn / p0 - 1.0
        else:
            ret = close[t1] / p0 - 1.0
        if label is None:  # vertical barrier reached
            label = int(np.sign(ret * s)) if cfg.vertical_label == "sign" else 0
        if side is not None:
            # meta-label: did the primary's call make money (stop hit -> 0)
            label = int(ret * s > 0 and touch != adverse)
        out.append(
            {
                "t0_idx": int(t0),
                "t1_idx": int(t1),
                "label": int(label),
                "ret": float(ret),
                "trgt": float(trgt),
                "touch": touch,
            }
        )
    df = pl.DataFrame(out)
    if n_double:
        import logging

        logging.getLogger(__name__).warning(
            "triple_barrier: %d double-touch bars resolved pessimistically "
            "(if >1%% of events, barriers are too tight for 1h bars)",
            n_double,
        )
    return df


def concurrency(events: pl.DataFrame, n_bars: int) -> np.ndarray:
    """c[t] = number of label windows [t0, t1] covering bar t."""
    delta = np.zeros(n_bars + 1, dtype=np.int64)
    for t0, t1 in zip(events["t0_idx"].to_numpy(), events["t1_idx"].to_numpy(), strict=True):
        delta[t0] += 1
        delta[t1 + 1] -= 1
    return np.cumsum(delta)[:n_bars]


def sample_weights(
    events: pl.DataFrame,
    close: np.ndarray,
    last_weight: float = 0.75,
    floor_frac: float = 1e-3,
) -> pl.DataFrame:
    """AFML Ch.4: return-attribution weights x time-decay on cumulative
    uniqueness. Newest event decays to exactly 1, oldest to `last_weight`."""
    n_bars = len(close)
    c = concurrency(events, n_bars)
    logc = np.log(close)
    r = np.diff(logc, prepend=logc[0])

    t0s = events["t0_idx"].to_numpy()
    t1s = events["t1_idx"].to_numpy()
    uniq = np.empty(len(events))
    w_raw = np.empty(len(events))
    for i, (t0, t1) in enumerate(zip(t0s, t1s, strict=True)):
        span = slice(t0, t1 + 1)
        cc = np.maximum(c[span], 1)
        uniq[i] = float(np.mean(1.0 / cc))
        w_raw[i] = abs(float(np.sum(r[span] / cc)))
    w = w_raw * len(w_raw) / max(w_raw.sum(), 1e-12)

    # time decay: piecewise-linear in cumulative uniqueness, sorted by t1
    order = np.argsort(t1s, kind="stable")
    x = np.cumsum(uniq[order])
    total = x[-1]
    slope = (
        (1.0 - last_weight) / total
        if last_weight >= 0
        else 1.0 / ((last_weight + 1.0) * total)
    )
    const = 1.0 - slope * total
    d_sorted = np.maximum(const + slope * x, 0.0)
    d = np.empty_like(d_sorted)
    d[order] = d_sorted

    final = w * d
    final = np.maximum(final, floor_frac * final.mean())
    return events.with_columns(
        pl.Series("uniqueness", uniq),
        pl.Series("w_attrib", w),
        pl.Series("w_decay", d),
        pl.Series("sample_weight", final),
    )
