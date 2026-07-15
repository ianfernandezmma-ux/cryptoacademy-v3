# Audit round synthesis — pre-B3 checkpoint (2026-07-15)

Five auditors (code, return levers, strategy scout, methodology, project
red-team) ran after B2 closed, under the hard rule "no new backtests on
project data". Full reports live beside this file. This synthesis is the
single prioritized action plan.

## Headline conclusions

1. **The strategy work stands; the numbers need honest bands.** The robust,
   replicated result is FAMILY-level: every gated-trend variant beat the
   vol-targeted benchmark with ~⅓ the drawdown and ~3× the return/maxDD.
   Quote "Sharpe ≈ 1.0" only with its 90% CI [0.32, 1.71] and both rf
   conventions (excess-of-cash ≈ 0.45–0.6); quote "DSR ≈ 0.8–0.95, not
   established". N20-vs-siblings is noise (0.13 SE) — champion stays N20 by
   the frozen rule; the selection-rule improvement (family-then-variant) is
   a B2.5 pre-registration.
2. **5.9%/yr is a scale-and-accounting artifact, not strategy weakness**:
   ~102%/yr on deployed capital; 94% of capital idle at a simulated 0%;
   sizing ≈ 1/10 Kelly. Honest improvement stack: cash yield (+3.5–4%/yr,
   ~0 DD) → vol target 20–24% (+4–5.5%/yr, DD ×~2, rails re-registered) →
   gated-asset budget reallocation (+0.5–1%/yr). Honest combined
   expectation: **~10–13%/yr at ~11–13% maxDD**. The 30%+/yr ambition is
   not available from spot long-only BTC+ETH at any defensible risk — that
   is a v2 mandate conversation (futures/shorts/more assets).
3. **The paper phase §8 was pre-committed to INCONCLUSIVE** (P(≥30 RT in 18
   months) ≈ 0.15% at the champion's 10.9 RT/yr). Fix before B6
   registration: PASS-OPS verdict = G1+G2 only; performance = reported
   appendix with CIs; month-6 ops checkpoint; shadow set (6 registered
   variants + benchmarks) from day 1 → **B3 must be a multi-config engine**.
4. **The journal enforcement layer had 2 demonstrated CRITICALs** (sql()
   bypass — FIXED same day; two-writer model impossible on DuckDB — OPEN,
   single-writer redesign is the first pre-B3 work item) plus a fix batch
   (M1 cycle transaction, M2 idempotency gate, M4 column lists, M5/M3/m1
   hardening, M9 Windows CI, M10 schema/API gaps). Strategy math and the B2
   evaluator audited clean.
5. **Process fixes**: registry backed up into git (DONE, b8bb3fd); reviews
   exported to docs/reviews/ (DONE, this series); stopping rule adopted
   (below); capital band and host decision belong to Ian.

## The stopping rule (adopted, red-team F7)

Exactly ONE amendment round ("**B2.1**") before B3, pre-registered on one
page, scope closed to: (a) vol-target scaling of the frozen champion at ≤2
pre-stated levels; (b) the cash-yield accounting convention; (c) the B6/§8
amendments (PASS-OPS split, month-6 checkpoint, shadow set, planned-outage
taxonomy, G2 reconstruction rule, expected-verdict arithmetic printed).
No new families, no parameter re-search, no re-ranking of the 7. B3's start
date is committed at B2.1 close. Thereafter, ideas → hypothesis table →
quarterly channel; only confirmed violations/defects reopen evaluation.
"Results feel low" was used once as a trigger and is spent. The B2.5
hypothesis list (strategy scout: Donchian ladder, ETHBTC tilt, funding
tilt, trailing exits, MVRV gate, DVOL gate — 11 trials, N→240) waits for
the quarterly channel unless Ian explicitly charters it as part of B2.1's
successor after paper starts.

## Prioritized actions

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Registry into git | Claude | **DONE** (b8bb3fd) |
| 2 | sql() parser guard + regression tests | Claude | **DONE** (e43135e) |
| 3 | uv sync --locked; wheel SHA256 pinned+verified | Claude | **DONE** |
| 4 | Reviews exported to docs/reviews/ | Claude | **DONE** (this) |
| 5 | **Ian: capital band** (paper starting equity + eventual live band) | **Ian** | pending |
| 6 | **Ian: vol-target level** for B2.1 (12 stay / 20 / 24) + cash-yield convention approval | **Ian** | pending |
| 7 | **Ian: host decision** (mini-PC ~€150 recommended vs gaming PC + outage taxonomy) | **Ian** | pending (before B4) |
| 8 | B2.1 amendment round (one page, one registered run: champion at the chosen VT levels + yield convention; B6 amendments) | Claude after 5–6 | pending |
| 9 | Pre-B3 code fix batch: C2 single-writer redesign, M1 cycle transaction, M2 date-prefix gate, M4 column lists, M5/M3/m1, M8 provenance, M9 Windows CI, M10 schema APIs, yaml↔code consistency test, bootstrap m4/m5, logging m3 | Claude | pending |
| 10 | B3 (multi-config engine) with start date committed at B2.1 close | Claude | pending |

## Standing caveats carried forward
Survivorship of the 2025-chosen BTC/ETH pair on all backtest-era numbers;
year-cluster CI includes zero at regime granularity; backtest holds weights
(costless implicit rebalance) vs broker holding quantities — reconcile in
B3 and note in the B6 registration; fill_rule in strategy.yaml describes
the B3 paper model, not the B2 cost model that produced
backtest_expectation.
