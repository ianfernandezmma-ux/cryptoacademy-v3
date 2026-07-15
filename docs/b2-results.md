# B2 Results — one-shot evaluation of the pre-registered grid

**Run: 2026-07-15, single execution** per the frozen protocol
(`docs/b2-preregistration.md`, committed before the run at `bad51da`).
Pre-run adversarial review: no blockers; two hardening guards applied before
execution (parquet sort assertion; engine same-bar alignment tests — all
green, no numbers changed). Raw output: `data/b2/b2_results.json`.
All 7 identities registered as intent before evaluation (registry phase
`bot-b2`); union registry N = **229** distinct identities.

## Champion (frozen rule: max DSR subject to constraints)

**S2_DONCH_N20** — Donchian 20-day-high entry / 10-day-low exit, gated by the
200d SMA, inside the 12%-vol-target sizing layer.
Registry: intent `d493d33c8223`, result `8d581f5d0cd9`, config_hash
**`c0fbd4d88776`**.

| Metric (net, 2021-01-01 → 2026-07-11) | Value |
|---|---|
| Sharpe (ann.) | **1.01** |
| DSR (N=229, var across candidates) | **0.90** |
| PSR vs 0 | 0.99 |
| Ann. return / vol | 5.9% / 5.9% |
| Max drawdown | **6.8%** (BTC B&H: 76.6%) |
| Cost drag | 0.5%/yr (fees+slippage, conservative model) |
| Round trips | 10.9/yr (both assets), hit rate 43% |
| Avg. weighted exposure | 5.8% of capital |

## Full grid (all 7 eligible under constraints a–c)

| Config | Sharpe | DSR | MaxDD | Drag/yr | RT/yr | Hit |
|---|---|---|---|---|---|---|
| S1_SMA100_HOLD | 0.68 | 0.69 | 12.6% | 0.8% | 15.6 | 22% |
| S1_SMA200_HOLD | 0.77 | 0.76 | 8.0% | 0.4% | 7.6 | 29% |
| S2_DONCH_N10 | 0.68 | 0.69 | 6.8% | 0.9% | 21.3 | 37% |
| **S2_DONCH_N20** | **1.01** | **0.90** | **6.8%** | 0.5% | 10.9 | 43% |
| S3_EWMAC | 0.88 | 0.83 | 7.3% | 0.3% | 3.8 | 38% |
| S2_DONCH_N5_FAST (24h) | 0.55 | 0.57 | 7.6% | 1.7% | 42.5 | 37% |
| COMBO (equal-weight S2×2+S3) | 0.96 | 0.88 | 6.0% | 0.5% | 4.2 | 48% |

Benchmarks (same window, same cost model): **VT_5050 Sharpe 0.51 / maxDD
21.2%**; BH_BTC 0.54 / 76.6%; BH_5050 0.61 / 76.2%; cash 0.

Per-year Sharpe (champion): 2021 +1.64 · 2022 **−1.14** · 2023 +1.26 ·
2024 +1.69 · 2025 −0.08 · 2026H1 0.00 (flat all half — gate red / no
breakouts; being in cash through 2026H1 chop is the design working).

## Honest caveats — read before believing anything above

1. **PBO = 0.52** (CSCV, 16 blocks, 12,870 partitions): the in-sample winner
   among the 7 candidates falls below the out-of-sample median about half the
   time. The candidates are highly correlated variants, so their *ranking* is
   substantially noise. Concretely: the evidence that N20 specifically beats
   N10/EWMAC/COMBO is weak; the evidence that the *family* (gated trend at
   96h, vol-targeted) beats VT_5050 on risk-adjusted terms is the meaningful
   part (every variant did, with a third of the drawdown). The champion was
   selected by the ex-ante rule, not by this run's ranking looking pretty.
2. **DSR 0.90 < 0.95**: not statistically established against the 229-trial
   search. Consistent with pre-registered expectations (§8 honest band was
   SR 0.2–0.8; realized 1.01 is *above* it → treat with suspicion, expect
   regression in paper). B6's tracking gate (paper ≈ simulation), not this
   backtest, is what can be certified.
3. **Return level is modest by design**: ~5.9%/yr at 5.8% average exposure.
   This is a drawdown-controlled strategy, not a get-rich bot. Raw B&H earned
   more (31–39%/yr) with −76% drawdowns; the bot's entire claim is the
   risk-adjusted difference (Sharpe 1.01 vs 0.51–0.61, maxDD 6.8% vs 76%).
4. **24h question (pre-registered default: no)**: S2_N5_FAST survives the
   cost model better than feared (drag 1.7%/yr thanks to buffers+gate) but is
   the worst candidate (Sharpe 0.55, DSR 0.57) and adds nothing over slower
   variants. Verdict: **not selected; 24h stays out of v1**. Its eligibility
   flag is a curiosity, not a mandate.
5. Diagnostic footnotes (from the pre-run review): hit rates are computed on
   post-buffer held weights, gross of costs, open-at-window-end counts as a
   completed trip; BH_5050's monthly rebalance cost is charged same-day (bp
   noise, diagnostic only); the "fewer parameters" tie-break is a config-size
   proxy (unused — DSR had no ties).
6. 2022 was negative for every candidate (−0.7 to −1.9 Sharpe): the gates cut
   the bear's damage (maxDD single-digit vs −76% B&H) but did not produce
   profits in it. A long-only bot loses small in bears at best.

## What happens next (per plan-bot-v1)

- `configs/strategy.yaml` in the bot repo is frozen to the champion
  (S1-200 gate + S2 N20/exit-10; S3/S2_N10/COMBO disabled; 24h excluded),
  referencing `config_hash c0fbd4d88776` and trial `8d581f5d0cd9`.
- B3 builds the engine around exactly this config; B4 hash-freezes it; the
  B5/B6 paper phase — with its pre-registered gates and the pristine
  2026-07-12+ window — is the actual test. Nothing in this document is
  evidence of skill; it is the registered starting point.
