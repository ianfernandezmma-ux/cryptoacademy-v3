"""Backtest-overfitting statistics (Bailey & López de Prado).

- PSR: probability the true Sharpe exceeds a benchmark, adjusted for
  non-normality and track length.
- DSR: PSR against the expected maximum Sharpe of N unskilled trials — the
  deflation for having searched. N comes from validation.registry.
- PBO via CSCV: probability that the in-sample winner underperforms the
  median out of sample.
- MinTRL: track length needed before a Sharpe is statistically trustworthy.

Conventions: Sharpe ratios are PER-PERIOD (not annualized); kurtosis is RAW
(normal = 3); T = number of returns. Implemented with stdlib NormalDist —
no scipy dependency.
"""

from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist

import numpy as np

_N01 = NormalDist()
EULER_GAMMA = 0.5772156649015329


def sharpe(returns: np.ndarray) -> float:
    sd = returns.std(ddof=1)
    return float(returns.mean() / sd) if sd > 0 else 0.0


def _moments(returns: np.ndarray) -> tuple[float, float]:
    """(skewness, raw kurtosis) with simple (biased) estimators, as in the
    reference implementations."""
    x = returns - returns.mean()
    m2 = float(np.mean(x**2))
    if m2 == 0:
        return 0.0, 3.0
    skew = float(np.mean(x**3)) / m2**1.5
    kurt = float(np.mean(x**4)) / m2**2
    return skew, kurt


def psr(
    sr: float, t: int, skew: float = 0.0, kurt: float = 3.0, sr_benchmark: float = 0.0
) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_benchmark)."""
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4.0 * sr**2, 1e-12))
    z = (sr - sr_benchmark) * math.sqrt(t - 1) / denom
    return _N01.cdf(z)


def expected_max_sharpe(n_trials: int, var_trials: float) -> float:
    """E[max SR] of n_trials unskilled strategies whose trial Sharpes have
    variance var_trials (per-period)."""
    if n_trials <= 1:
        return 0.0
    e = math.e
    z1 = _N01.inv_cdf(1 - 1.0 / n_trials)
    z2 = _N01.inv_cdf(1 - 1.0 / (n_trials * e))
    return math.sqrt(var_trials) * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def dsr(
    sr: float,
    t: int,
    n_trials: int,
    var_trials: float,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    """Deflated Sharpe Ratio: PSR against the expected max of the search."""
    sr0 = expected_max_sharpe(n_trials, var_trials)
    return psr(sr, t, skew, kurt, sr_benchmark=sr0)


def dsr_from_returns(returns: np.ndarray, n_trials: int, var_trials: float) -> float:
    skew, kurt = _moments(returns)
    return dsr(sharpe(returns), len(returns), n_trials, var_trials, skew, kurt)


def min_track_record_length(
    sr: float, sr_benchmark: float, skew: float, kurt: float, confidence: float = 0.95
) -> float:
    """Observations needed so that PSR(sr_benchmark) >= confidence."""
    if sr <= sr_benchmark:
        return float("inf")
    z = _N01.inv_cdf(confidence)
    bracket = max(1 - skew * sr + (kurt - 1) / 4.0 * sr**2, 0.0)
    return 1 + bracket * (z / (sr - sr_benchmark)) ** 2


def pbo_cscv(returns_matrix: np.ndarray, n_blocks: int = 16) -> dict:
    """Probability of Backtest Overfitting via CSCV (Bailey et al. 2017).

    returns_matrix: T x N (rows = time, columns = one return series per trial).
    Splits rows into n_blocks contiguous blocks; for every C(n_blocks, n/2)
    IS/OOS partition: pick the IS-best trial, find its OOS relative rank
    omega in (0,1), logit lambda = ln(omega/(1-omega)). PBO = share of
    partitions with lambda <= 0 (IS winner at or below OOS median).
    """
    t, n = returns_matrix.shape
    if n < 2:
        raise ValueError("PBO needs at least 2 trials")
    if n_blocks % 2:
        raise ValueError("n_blocks must be even (CSCV symmetry requires it)")
    if t < 2 * n_blocks:
        raise ValueError(f"T={t} too small for n_blocks={n_blocks} (need >= {2 * n_blocks})")
    blocks = np.array_split(np.arange(t), n_blocks)
    half = n_blocks // 2
    logits = []
    for is_combo in combinations(range(n_blocks), half):
        is_rows = np.concatenate([blocks[b] for b in is_combo])
        oos_rows = np.concatenate(
            [blocks[b] for b in range(n_blocks) if b not in is_combo]
        )
        is_sr = np.apply_along_axis(sharpe, 0, returns_matrix[is_rows])
        oos_sr = np.apply_along_axis(sharpe, 0, returns_matrix[oos_rows])
        star = int(np.argmax(is_sr))
        # OOS relative midrank of the IS winner (ties split, not bottomed —
        # strict < would push tied duplicates to rank 1 and inflate PBO)
        below = (oos_sr < oos_sr[star]).sum()
        ties = (oos_sr == oos_sr[star]).sum()  # includes the winner itself
        rank = below + 0.5 * (ties - 1) + 1
        omega = rank / (n + 1)
        logits.append(math.log(omega / (1 - omega)))
    logits_arr = np.array(logits)
    return {
        "pbo": float((logits_arr <= 0).mean()),
        "n_partitions": len(logits_arr),
        "mean_logit": float(logits_arr.mean()),
    }
