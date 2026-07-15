# Plan v1.0 adversarial review — Statistics / overfitting lens

Agent: statistics reviewer of draft plan-bot-v1.md. Date: 2026-07-15.
All confirmed findings were integrated into plan v1.1 (§11 changelog).
This export preserves the full finding list (condensed from the original).

**F1 [CRITICAL]** Sample-size arithmetic inconsistent: §8's ≥60 round trips
unreachable for the favored strategies (S5 ≈ 2–18 RT/6mo; S2 ≈ 15–35);
"365 acted trades/yr" wrong by 4–10×; perverse incentive to select
high-turnover champions so the test can end. Fix: define round trip
(flat-to-flat, rebalances excluded); evaluation date from champion's
post-buffer rate at registration; fix the arithmetic. → Adopted (30-RT
floor + fixed date + INCONCLUSIVE branch).

**F2 [CRITICAL]** Handcrafted combination weights after seeing CV results =
unregistered optimizer with unbounded trial count. Fix: freeze the
combination rule ex ante (performance-blind), register it as one identity;
every weighting computed counts toward N. → Adopted (B2 froze equal-weight
+ turnover-based inclusion before evaluation).

**F3 [CRITICAL]** G2 undefined (which SE? which expectation? one- or
two-sided?): wide-SE reading vacuous (SE(ann SR) ≈ 1.4–1.5 at T=0.5y),
CV-fold-SE reading near-impossible; anchor = max-over-configs is
upward-biased. Fix: exact formula pre-registered — shrunk expectation from a
walk-forward simulation matching the deployed procedure, Lo(2002) SE at
actual T, one-sided lower bound; pooled exact binomial for hit rate.
→ Adopted (G2 redefined as paper-vs-simulation tracking).

**F4 [CRITICAL]** Flexible duration + "final 3 months" G1 + self-graded
incidents = optional stopping. Fix: calendar evaluation date registered at
B6 day 1; no early stop/extension except by pre-registered rule; incident
taxonomy + rubric written before B6, classified at occurrence, immutable.
→ Adopted.

**F5 [MAJOR]** Lockbox protected against algorithms but not engineers:
B3 dry-runs on post-cutoff days, B5 burn-in reactions to performance-shaped
observations. Fix: B3 dry cycles pre-cutoff only; hash-freeze at B4 exit;
plumbing whitelist; decision-path change = new trial + clock reset.
→ Adopted.

**F6 [MAJOR]** Monthly refits: hidden human veto on bad-looking refits =
monthly selection events; G2 compares refitting bot vs static-model
expectation. Fix: fully mechanical refit policy or none. → Adopted (refits
CUT from v1 entirely; champion frozen).

**F7 [MAJOR]** Composite gate battery passes a no-skill bot with ~15–25%
probability; nobody computed it. Fix: null simulation before B6; publish
family-wise false-pass rate next to the verdict; relabel PASS as
"non-inferiority + plumbing certified". → Adopted.

**F8 [MAJOR]** VT_5050 benchmark under-specified (σ estimator, floor,
buffer, caps, fill model) = post-hoc dial. Fix: benchmark as shadow strategy
in the same engine, hash-frozen at B6 day 1. → Adopted.

**F9 [MAJOR]** Discretionary pause/flatten contaminates the track record.
Fix: intervention events first-class; gates grade the no-discretion shadow
curve; gap reported. → Adopted.

**F10 [MAJOR]** Quarterly hypotheses validated on the data that generated
them. Fix: hypothesis tagged with observation window; validating CV excludes
it; mechanical outlier clause; HAC-SE paired shadow comparison. → Adopted.

**F11 [MAJOR]** "Full registry N" ambiguous (bot vs lab registry). Fix:
N = union of both registries, dual-N convention; S5 threshold grid
enumerated. → Adopted.

**F12 [MINOR]** B2 exit must report champion DSR/PSR explicitly so backtest
significance can't be retro-claimed. → Adopted.

**F13 [MINOR]** Friction table units inconsistent (one-way vs RT); Sharpe
band (0.7–1.2 vs 0.2–0.5) contradictory across sections. Fix: one number
(0.2–0.5) used everywhere; recompute friction with defined units. → Adopted.

**F14 [MINOR]** Monitor recalibration mid-test interacts with G1; slippage
percentile window undefined. Fix: frozen expanding-window definition; single
pre-scheduled recalibration date. → Adopted.

**Verdict:** architecture of discipline strong; statistical acceptance layer
was where it would leak. All fixes = one page of pre-registrations added
before B2/B6. "Without them, this plan will be killed the same way v2 was —
not by a bug, but by a series of individually reasonable, unregistered human
choices."
