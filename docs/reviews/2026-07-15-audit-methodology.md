# Audit round (pre-B3) — B2 methodology audit

Agent: statistical methodology auditor. Date: 2026-07-15. All derived numbers
recomputed from logged b2_results.json only; no new trials.

## Findings

**F1 [MAJOR] — PBO 0.52 nearly uninformative here.** With 7 near-duplicate
variants (mean logit 0.065 ≈ 0), PBO→0.5 is the mechanical outcome for any
set of equally-good near-clones; it says "N20-vs-siblings is noise" (true)
and NOTHING about family-vs-benchmark (VT_5050 was not a CSCV column).
Technical caveats: 16 non-contiguous recombined blocks destroy the
multi-month autocorrelation trend rules live on (downward-biases OOS trend
Sharpes); n=7 rank grid is coarse. Also: with N and var identical across
candidates, max-DSR was effectively argmax Sharpe over near-duplicates —
champion–COMBO gap = 0.13 SE. Selection between N20 and COMBO was decided by
noise, by construction. NOTHING may change retroactively (swapping to COMBO
now would be post-hoc selection); N20 stays champion through B3–B6; a B2.5
pre-registration may freeze family-then-median-variant selection as a
registered rule change; the paper engine can shadow-run all 7 + COMBO (data
collection, not selection).

**F2 [MAJOR] — DSR (N, var) pairing internally inconsistent; net bias
optimistic.** N=229 from a search that mostly produced MCC-metric ML trials;
var=7.8e-05 from 7 near-clones (too narrow for a 229-wide search). E[max]
scales with sqrt(var) — the var lever dominates. Sensitivity grid
(champion, T=2018): N=229 at var×1 → 0.900; ×2 → 0.793; ×4 → 0.562. Clustered
guidance (K≈3 families, cluster-level var) lands ~0.91–0.96; honest reading:
**"DSR ≈ 0.8–0.95, not established"** — quote the band, not 0.90.

**F3 [MAJOR] — No uncertainty quantification on the point estimates.**
Skipping purged CV was defensible (no fitted parameters), skipping CIs was
not. Recomputed: analytic iid 90% CI for champion annualized Sharpe =
**[0.32, 1.71]** (daily-SR SE 0.022 via PSR denominator, skew 0.63, kurt
21.3). Year-cluster view (1.64, −1.14, 1.26, 1.69, −0.08): mean 0.67, sd
1.24, t=1.21, df=4 → 90% CI **[−0.51, +1.86]** — at regime granularity the
evidence does not exclude zero. Champion-vs-VT_5050 was a point-estimate
inequality (naive z≈0.85; paired z incomputable because **daily return
vectors were not saved — artifact gap, fix next round**: persist net-daily
vectors + held-weight matrices per candidate and benchmark).

**F4 [MAJOR] — Sharpe 1.01 flattered by the rf=0 convention.** ~94% cash at
0%. Excess-of-cash Sharpes: rf 2.5% → 0.59 (VT_5050 0.30); rf 3.3% → 0.45
(0.24); rf 4.5% → 0.25 (0.14). The RELATIVE claim survives every scenario;
the absolute 1.01 does not survive the standard convention. Cash-sweep is a
first-order product decision. Print both conventions from now on. Also:
communicate the vol target as "~12% while deployed; realized whole-period
vol will be roughly half or less" — else the plan §8 realized-vol-vs-target
metric will look like failure when it is the design.

**F5 [MINOR] — Sharpe-vs-Sharpe vs VT_5050 acceptable but incomplete.**
Flatness DEFLATES the full-series Sharpe (SR_full ≈ sqrt(f_active)×SR_active)
and inflates kurtosis (21.3 is largely zero-inflation — PSR/DSR absorb it).
Real issue: spot long-only cannot lever 5.9% vol to 12%, so the Sharpe edge
is not monetizable into return — champion absolute return (5.9%) is BELOW
VT_5050's (6.2%). On return/maxDD the whole family wins decisively
(0.79–0.89 vs 0.29). B2.5: pre-register Sharpe AND a DD-normalized criterion;
report active-day Sharpe as diagnostic.

**F6 [CRITICAL] — Plan §8 paper design pre-committed to INCONCLUSIVE.**
Champion rate 10.85 RT/yr → expected time to 30 RTs = 2.76y → 18-month cap
binds → expected ~16.3 RTs → **P(≥30 RTs in 18 months) ≈ 0.15%** (Poisson;
regime clustering worse — 2026H1 produced zero). G3/G4 dead on arrival;
G1 (ops) and G2 (tracking) unaffected and remain the real tests. MinTRL for
SR 1.01 vs 0: 2.6 years; vs VT_5050: ~10 years. Fixes (all pre-B6, hence
legitimate): print the expected-verdict arithmetic in the B6 registration;
pool shadow-candidate RTs as non-gate diagnostic; set expectations now —
modal B7 outcome is "rails certified, edge untested". Do NOT lower the
30-RT floor (gaming).

**F7 [MINOR]** — 5.5y ≈ 3 regime episodes ≈ 60 RTs at 43% hit; PnL
concentrated in few winners. BTC/ETH chosen in 2025 knowing they survived —
survivorship inherits into all backtest-era numbers (standing caveat; paper
window free of it). 2022 negative for all candidates is the most credible
line in the results.

**F8 [MINOR]** — var_trials computed as frozen (execution correct; design
flaw). One-shot discipline held; expectations were written down and then
violated upward, which the results doc itself flags — exemplary practice.
VT_5050 hit_rate 1.0 / 2 RTs shows the RT metric is meaningless for
always-in strategies (suppress in comparative tables).

## Verdict

STANDS: the pre-registered one-shot process; the FAMILY-level claim (all 7
beat VT_5050 on Sharpe and by ~3× on return/maxDD; drawdown control 6–8% vs
21%/76% is the robust result); the 24h rejection; 2022 loss reporting; N20
as champion BY THE FROZEN RULE (procedurally unimpeachable, not swappable).

WEAKENED: "Sharpe 1.01" (quote with CI band + both rf conventions);
"DSR 0.90" (quote as 0.8–0.95 band); N20-vs-siblings specificity (0.13 SE);
plan §8 G3/G4 (pre-committed INCONCLUSIVE, ~99.9%).

## B2.5 pre-registration recommendations (10)

1. Save return-stream artifacts (net daily vectors, held-weight matrices,
   exposure flags) per candidate and benchmark. 2. Family-then-variant
   champion rule (max-DSR as tie-break only), registered as a rule-change
   trial. 3. Clustered DSR (correlation clusters; N=K, cluster-level var) +
   legacy number + sensitivity grid. 4. Paired Sharpe-difference test vs
   VT_5050 (Ledoit–Wolf / stationary bootstrap on the differential).
5. Dual Sharpe conventions; freeze the cash-sweep policy. 6. Active-day
   Sharpe + time-in-market as standing diagnostics. 7. Benchmarks as CSCV
   columns or drop PBO for near-duplicate sets (with stated reason).
8. B6 registration prints expected-verdict arithmetic (P(≥30 RTs)) next to
   the false-pass rate; pooled shadow RTs as non-gate diagnostic.
9. Standing survivorship caveat carried into B7. 10. Year-cluster dispersion
   table (mean, sd, t) as a required results block.
