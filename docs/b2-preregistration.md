# B2 Pre-Registration — CryptoBot v1 strategy evaluation

**Status: FROZEN 2026-07-15, BEFORE any evaluation ran.** Committed to git
before `scripts/b2_evaluate.py` produced a single number. Per plan-bot-v1 §3
and reviewer findings F2/F3 (statistics review): the combination rule, the
champion-selection rule, the cost model, and every candidate configuration
are fixed here, ex ante. Any deviation discovered later is a protocol
violation, not a tweak.

## 1. Data & timing

- Source: Binance spot 1h klines (lab archive), BTC + ETH, resampled to
  **daily UTC bars** (day D = 00:00–24:00 UTC).
- History: 2020-01-01 → **2026-07-11 inclusive** (lockbox cutoff; 2026-07-12+
  is the paper era and is not touched).
- Warm-up: indicators may consume 2020; **scored returns run 2021-01-01 →
  2026-07-11** (T ≈ 2018 daily observations).
- Decision at close of day D uses data ≤ close(D) only. Position `w(D)`
  earns `r(D+1) = close(D+1)/close(D) − 1`. Turnover costs are charged in
  `r(D+1)` on `|w(D) − w(D−1)|`. No same-bar execution.
- Annualization: √365 (24/7 market). Sharpe reported annualized; PSR/DSR
  computed on per-period (daily) values.

## 2. Cost model (defines "net" for every number in B2)

Per side: fee 0.10% + slippage 5 bp (BTC) / 10 bp (ETH); slippage **doubled**
on days where the asset's 30d EWMA vol exceeds the 80th percentile of its own
expanding history (expanding from 2020-01-01, ≥365d warm-up; definition
frozen). No BNB discount, no maker fills, all-or-nothing.

## 3. Sizing layer (identical for every candidate and benchmark)

- σ_asset = EWMA(span 30d) std of daily returns, annualized ×√365,
  **floored at 20%**.
- `w_target = scalar × 0.12 × risk_weight / σ_asset`, risk_weight = 0.5/0.5
  BTC/ETH. When a gate zeroes one asset the other KEEPS 0.5 (under-deploy).
- Caps: per-asset 0.50; portfolio gross soft cap 0.80 (proportional
  scale-down). Spot long-only: no leverage, no shorts.
- No-trade buffer: trade only if `|w_target − w_current| ≥ max(0.10 ×
  w_target, 0.01)`; otherwise hold current weight.

## 4. Candidate configurations (7 identities, registered before evaluation)

`scalar_asset(D) ∈ [0,1]` per asset per day; all entries gated where stated.

| # | id | horizon | Definition |
|---|----|---------|------------|
| 1 | S1_SMA100_HOLD | 96h | scalar = 1 if close(D) > SMA100(D) else 0 |
| 2 | S1_SMA200_HOLD | 96h | scalar = 1 if close(D) > SMA200(D) else 0 |
| 3 | S2_DONCH_N10 | 96h | Enter when close(D) ≥ max(close[D−10…D−1]); exit when close(D) ≤ min(close[D−5…D−1]). Gate S1-200: entries only when green; red forces flat. scalar ∈ {0,1} |
| 4 | S2_DONCH_N20 | 96h | Same with N=20 / exit 10 |
| 5 | S3_EWMAC | 96h | Carver EWMAC: forecasts 8/32 (scalar 5.3) and 32/128 (scalar 2.65) on daily closes, vol-normalized by EWMA(36) std of daily price changes, each capped ±20, averaged; scalar = clip(avg/10, 0, 1) × S1-200 gate |
| 6 | S2_DONCH_N5_FAST | 24h | N=5 / exit 2, S1-200 gate. **This is the pre-registered answer to "does anything survive at 24h-cadence": default expectation NO (fee death)** |
| 7 | COMBO | 96h | Per-asset scalar = equal-weight mean of the scalars of the *included families* (see rule below) |

**Combination rule (frozen, performance-blind):** the COMBO averages the
per-asset scalars of families {S2_N10, S2_N20, S3_EWMAC}. A family is
included iff its **modeled annual cost drag ≤ 10%/yr** (post-buffer annual
turnover × per-round-trip cost, from the same single run — a turnover
quantity, never a PnL ranking). S1 configs and the 24h config are never in
the COMBO. No weight search: equal weights, one computation. If zero
families qualify, COMBO = S1_SMA200_HOLD.

## 5. Benchmarks (same engine, same costs; not selection candidates)

CASH (0%); BH_BTC (buy-and-hold BTC, w=1); BH_5050 (0.5/0.5, monthly
rebalance, costs charged); **VT_5050 (scalar ≡ 1 both assets through the §3
sizing layer — the primary skill benchmark)**.

## 6. Champion-selection rule (frozen)

Among candidates 1–7, the champion is the config with the **highest DSR**,
computed with:
- N = distinct `config_hash` count in the **union** of the lab registry
  (`data/trials/trials.jsonl`, all phases) and these B2 registrations;
- `var_trials` = cross-sectional variance of the per-period Sharpes of the
  7 candidates (single computation);
subject to ALL constraints: (a) modeled annual cost drag ≤ 10%/yr;
(b) max drawdown ≤ 40%; (c) net Sharpe ≥ VT_5050's net Sharpe.

Tie-break (in order): fewer parameters, lower turnover. **If no candidate
passes (a)–(c): champion = NONE**, the honest null is reported, and the
decision returns to Ian — no relaxation of constraints, no re-runs.

Additional reported diagnostics (not selection inputs): PSR vs 0, PBO via
CSCV (16 blocks) across the 7 candidate daily-return series, per-year table,
round trips/yr net of buffers (round trip = flat-to-flat episode per asset on
the scalar), cost share of gross PnL, and each candidate vs VT_5050.

## 7. Registration & one-shot protocol

1. This document is committed FIRST.
2. `scripts/b2_evaluate.py` registers all 7 identities (phase `bot-b2`) via
   `validation.registry.register_trial` — intent before evaluation.
3. The evaluation runs ONCE and logs metrics per identity via `log_trial`.
4. Results go to `docs/b2-results.md` + `data/b2/b2_results.json` verbatim —
   including nulls. Re-runs are permitted only for code DEFECTS confirmed by
   the pre-run adversarial review protocol (a lookahead/off-by-one bug found
   BEFORE results are read), and every re-run is registered and noted.
5. Strategy code (`cryptobot.engine.strategies` / `sizing`) is reviewed
   adversarially for lookahead BEFORE the run (plan review F5 discipline).

## 8. Expectations (written before results, for the record)

Honest net-SR band for the winner: **0.2–0.8**. The 24h config is expected
to FAIL on costs. S1-only configs are expected to have the best DD control
and possibly the best DSR (fewest moving parts). It is entirely possible
that NOTHING beats VT_5050 — that outcome ships as-is.
