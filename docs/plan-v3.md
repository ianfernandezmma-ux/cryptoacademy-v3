# Plan v3 — from audited pipeline to published result (2026-07-11)

Supersedes the "Pending" list in CLAUDE.md and refines docs/phase4-plan.md
§4.4–4.5 using the 2026-07-11 full-code audit (docs/audit-2026-07-11.md) and
three sourced research passes (validation statistics, crypto-signal evidence,
production robustness). The goal is unchanged: the most robust, honest daily
prediction quality achievable — never higher numbers via tricks.

## Guiding verdicts from research (with sources in the audit archive)

1. MCC 0.065/0.093 sits exactly in the honest published band for daily BTC/ETH
   classifiers (Jaquart et al. 52.9–54.1% accuracy). Declare this the expected
   operating band; add a "too-good" tripwire (any config with MCC > ~0.15 at
   24h triggers a leakage investigation, not a celebration).
2. The route from ~54% raw accuracy to deployable quality is CONFIDENCE
   FILTERING (coverage-vs-hit-rate curves), not chasing pooled accuracy.
3. CPCV and anchored walk-forward are complements — report both in 4.5.
4. DSR needs per-selection-decision trial families and dual-N reporting
   (raw registry N + clustered effective N); PBO only within homogeneous
   families on a common grid (dovetails with caveat F2).
5. Expect DSR non-rejection at these effect sizes (MinTRL math) and frame the
   4.5 headline as robustness/effect-size stability, not significance.
6. Equal-weight OOF probability averaging is the only ensemble worth testing
   at N≈2,500 (trained stacking overfits); gate on error decorrelation first.
7. Seed noise ≈ signal at MCC~0.07: 5-seed ensembles for BOTH the production
   signal and reported metrics (one registered identity, seeds noted).
8. Monthly expanding-window retrain is the evidence-backed cadence; new models
   enter as shadow challengers, never directly as champion.

## Batch A — close Phase 4.3/4.4 (GPU/pipeline days, runnable now)

Order matters; each step unblocks the next.

1. **Labels v2 (audit L1)**: reindex the hourly grid (null rows at the 15
   gaps) in `labels/generate`, making the documented NaN-gap discipline
   operative; add calendar densification before rolling daily features and
   EWM warmup masks (matrix v2). Regenerate labels + variants; re-run the
   clean-room bit-exact verification on a sampled window; register the
   label/matrix version bump as a trial dimension.
2. **`backfill-regime`** over the full 2,383-day GDELT series with the v4
   anonymized-slug prompt (v3 pilot rows are re-scored automatically).
   ~6.5 years × ~1 LLM call/day ≈ hours on the 35B.
3. **`validate-regime`** on the full series — gates now use the
   autocorrelation-honest rotation permutation. A gate failure sends regime
   back, not forward.
4. **News-block re-ablation + with/without-regime comparison** (formal close
   of 4.3 gate 2) via `evaluate_config(..., phase="4.4")` — now under the
   lockbox cutoff, with the era-consistent news scales. Numbers will differ
   from the handoff's (cutoff + tone rescale + matrix v2): document the
   version break explicitly in the comparison table. A null is publishable.
5. **Re-anchor 4.2 selections under the cutoff**: re-run baselines, the two
   per-horizon winning configs, and the block ablations on pre-2026 data
   (cheap: LightGBM on ~2.3k events). If the winner changes, the new winner
   stands — the old one was selected on contaminated folds. F2 discipline:
   barrier_mult is chosen per-variant on Phase-5 return streams, not by
   cross-variant MCC; until then report per-variant results side by side.
6. **Ensemble check** (protocol item): correlation of LightGBM vs PatchTST
   OOF probabilities; if decorrelated enough, equal-weight average under the
   same purged CV, registered. Keep only if it beats the primary honestly.
7. **5-seed reporting**: extend `evaluate_config` with a seed-set option;
   headline numbers become seed-averaged with dispersion (mean ± sd across
   seeds AND across folds). One registered identity per seed-set run.

## Batch B — Phase 4.5, the tribunal (after A)

- CPCV Sharpe distributions + **anchored walk-forward pass** side by side.
- **DSR with dual N** per horizon family (selection-decision definition
  written BEFORE computing; registry query documented in the report).
- **PBO-CSCV within homogeneous families** on a common time grid.
- **Per-fold sample weights (F3)**: recompute attribution/decay/uniqueness
  inside each training fold after purging — strict Kapoor-Narayanan closure —
  before any headline number.
- **SPA / Romano-Wolf** dependence-aware comparison vs the momentum baseline
  (the final model family is small and heavily dependent; BH-FDR only as a
  secondary lens).
- **Beta calibration** of the meta-model on nested-OOF predictions before
  threshold selection; reliability curves and Brier score become standard
  outputs. The meta-labeling claim stays downgraded to "suggestive" until
  Phase-5 return streams (see audit): +5.4pp pooled, t≈1.85.
- **Coverage-vs-hit-rate curves** as the primary deliverable per horizon
  (confidence filtering is where deployable quality lives).
- **Per-regime breakdown** with coverage counts, not pooled headlines.
- **Pre-registered lockbox protocol** (docs/lockbox-protocol.md): exact
  configs (registry IDs) to be evaluated, metrics, and publication commitment
  BEFORE 4.5 results exist. Lockbox reality after the audit: 2026-01-01→07-11
  is a *contaminated holdout* (selection touched it) — reported with that
  caveat; the pristine lockbox runs 2026-07-12 → Phase-5 end, untouched by
  construction (cutoff enforced in code since today).
- **daily-report command** (35B → Telegram): health (task results, freshness,
  gap detection — the gate built today feeds it), rolling 30/90d hit rates
  WITH binomial confidence bands, reliability curve drift, prediction-PSI.

## Batch C — operations hardening (parallel, small pieces)

From the production-robustness research; each item small enough for an
odd hour:

1. Prediction-score PSI (30d window vs training reference) with Yurdakul
   chi-square critical values — Tier-1 daily signal, alert only on 3
   consecutive breaches.
2. Monthly adversarial validation (LightGBM train-window vs trailing 60d;
   AUC > 0.6 persistent → investigate via its feature importances). No
   per-feature daily KS anywhere.
3. Champion/challenger shadow table in DuckDB: every candidate scores the
   daily row; promotion rules pre-registered in trials.jsonl before the
   comparison window opens (operational extension of iron rule 2).
4. Monthly expanding-window retrain clock + event-triggered override; every
   retrain registered; new model = challenger first.
5. Hash manifests for every artifact the champion depends on (extend the
   GDELT manifest pattern; skip DVC — Windows friction, no payoff at 60 MB).
6. Nightly `news.duckdb` backup to OneDrive (first_seen stamps are
   physically unrecoverable).
7. One-page monitoring runbook: every alert maps to an action and a
   persistence rule; written no-action rules protect the honest-metrics
   culture from noise-chasing.

## Batch D — Phase 5 (unchanged in essence, sharpened acceptance)

- Realistic backtest: t+1 open execution, full costs (fees + slippage +
  funding), ¼-Kelly cap — **net-of-cost acceptance criteria pre-registered**
  (published 52–56% daily edges are routinely consumed by costs).
- Adaptive-conformal act-rate gating for the daily signal (keeps the
  meta-gate's coverage stable across regimes).
- Paper trading ≥ 60 days with the shadow table as the ledger.
- ONE lockbox opening at the end: pristine window 2026-07-12+, contaminated
  window 2026-01-01→07-11 reported beside it with its caveat. Both published
  whatever they say.

## Batch E — Phase 6 web (per existing site plan v2; unchanged)

The daily JSON contract gains: signal + calibrated P(win) + act/no-act gate +
coverage context + data-freshness stamp from the health gate.

## Decisions Ian owns (everything else proceeds autonomously)

1. **Lockbox policy** — recommended: Option A above (cutoff + re-anchored
   selection + dual-window reporting). Alternative: declare 2026-H1 dead and
   never evaluate it. Both honest; A keeps more information.
2. **Farside**: add curl_cffi (browser impersonation) if 403s persist after
   today's retry+alert fix — new dependency, his call.
3. **Labels v2 timing**: batch A step 1 changes labels near 15 gaps and
   invalidates the bit-exact certificate until re-verified — approve the
   regeneration window.
