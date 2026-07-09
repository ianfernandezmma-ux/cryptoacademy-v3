# Phase 4 — Models & Validation: Detailed Plan

Goal: honest, validated models for BTC/ETH at BOTH horizons (24h and 96h),
passing hard statistical gates (DSR > 0.95 with true trial count, PBO < 25%,
beats momentum baseline), plus the supporting machinery: trial registry,
regime classifier, and daily private AI reports.

Agent budget: ≤10 per sub-phase. Agents are spent where they multiply quality
(research with verification, adversarial review, parallel validation) — not on
work the main session does better single-threaded.

---

## 4.1 Labels on real data + validation infrastructure  (~1 week)

The foundation everything else sits on. Nothing here may be wrong.

**Build**
- Generate CUSUM events + triple-barrier labels on real 1h data, both horizons
  (24h = 24 bars, 96h = 96 bars), per asset; calibrate k so total events land
  in the 1,500–3,000 zone; persist `data/labels/labels_{asset}_{horizon}.parquet`
  with (t0, t1, label, ret, trgt, weights).
- `validation/cv.py`: PurgedKFold + Combinatorial Purged CV over label
  intervals (t0, t1) with embargo ≥ horizon; sklearn-compatible splitters.
- `validation/registry.py`: append-only trial registry (every model config,
  every factor candidate, every sweep point → one row). N_trials feeds DSR.
- `validation/stats.py`: Probabilistic & Deflated Sharpe Ratio, PBO via CSCV,
  MinTRL — clean-room, unit-tested against published reference values.
- Label-quality report: class balance, touch-type distribution, uniqueness
  distribution, events per regime/year.

**Agents (plan: 3)** — R1 research: exact DSR/PBO/CSCV formulas + published
worked examples as test vectors; skfolio CPCV semantics to cross-check. R2
(after build) adversarial review of cv.py + stats.py + label generation. R3
independent verification: recompute labels for a sampled window with a naive
reference implementation and diff.

**Gate:** reviewer finds no CRITICAL; label counts sane at both horizons;
DSR/PBO reproduce reference vectors exactly; CV splits pass a leakage
simulation (synthetic autocorrelated data → purged CV score ≈ true OOS,
unpurged K-fold visibly inflated).

## 4.2 Baseline models + feature selection  (~1 week)

**Build**
- Pooled BTC+ETH training frame (matrix ⋈ labels), asset_id categorical,
  NaN-native LightGBM, sample_weight = uniqueness × decay.
- Benchmarks first: (a) always-long, (b) momentum-only LightGBM (price block
  only) — the bar news/derivatives must clear.
- Full-feature LightGBM per horizon; Optuna HPO strictly inside training
  folds; every trial → registry.
- Feature selection: correlation clustering → fold-wise SHAP stability →
  clustered-MDA confirmation; target 40–80 surviving features.
- Per-block ablations (price / derivatives / on-chain / macro / news) — the
  thesis's core empirical table.

**Agents (plan: ≤4)** — parallel ablation verification (2 agents re-running
key configs from clean state), 1 adversarial review of the training loop
(fold hygiene, weight leakage, early-stopping on fold-internal data only),
1 optional research if LightGBM small-sample defaults need updating.

**Gate:** full model beats momentum baseline OOS at ≥1 horizon with purged CV;
ablations reproducible; registry complete (spot-check: N_trials matches Optuna
study sizes).

## 4.3 Regime classifier + news feature integration  (~3-4 days)

**Build**
- Daily LLM regime scorer (35B, grammar-forced): risk_appetite −2..+2 with
  anchored definitions, crypto_stress 0..3, macro_stress 0..3, dominant
  narrative enum; few-shot anchors per the ICAIF'24/Yang lessons.
- Back-classify the GDELT era from headline samples; standalone validation:
  Spearman(crypto_stress, next-7d realized vol) > 0.2, event-study on known
  crises (2020-03, 2021-05, 2022-05/11, 2024-08), regime persistence ≥5 days.
- Scoring prompt recalibration (fix 'regulation' over-assignment) with
  anchored few-shot examples; re-score stored articles.
- Model integration as gating interactions (news_features × regime).

**Agents (plan: ≤3)** — 1 verification of back-classified regimes vs known
history, 1 adversarial review of prompt/aggregation leakage (LLM hindsight),
1 spare.

**Gate:** standalone validation passes BEFORE the feature touches the model;
with-regime model ≥ without-regime model under purged CV.

## 4.4 Meta-labeling + DL challengers + ensemble  (~1 week)

**Build**
- Meta-labeling: primary LightGBM side → side-adjusted triple-barrier →
  small calibrated secondary (Platt; ≤8 features, heavy regularization);
  output = P(win) for sizing. Check per-regime lift, not just pooled AUC.
- DL challengers on the 5090: PatchTST + N-HiTS (neuralforecast), RevIN,
  same CV protocol. Windows-native torch cu128 first; WSL2 only if needed.
- Zero-shot Chronos benchmark row.
- Ensemble: probability averaging LightGBM + best DL; compare.

**Agents (plan: ≤4)** — 1 research (current neuralforecast/torch-Windows
status), 2 parallel training verification, 1 review.

**Gate:** documented comparison table; ensemble kept only if it beats primary
under purged CV at same trial-count accounting.

## 4.5 Validation gauntlet + daily AI reports  (~1 week)

**Build**
- Full CPCV Sharpe distributions; DSR with the REAL registry N; PBO; per-year
  and per-regime breakdown; final ablation table.
- LOCKBOX protocol formalized: 2026-01-01 → present stays untouched until the
  END of Phase 5 (one evaluation, result published whatever it is). Enforced
  by code: training/CV data loader hard-caps at 2025-12-31.
- `daily-report` command: health (task results, data freshness, gap detection)
  + model section (predictions vs realized once live) → 35B writes an English
  report → Telegram + `reports/` archive.
- Optional (budget permitting): overnight LLM factor-mining harness v1 under
  the constrained-DSL protocol, candidates → registry.

**Agents (plan: ≤6)** — 3-vote adversarial verification of the headline
result (each tries to refute: leakage, trial undercounting, cost omissions),
1 reproduction from clean checkout, 1 review of the lockbox enforcement,
1 spare.

**Gate (= Phase 4 exit):** DSR > 0.95 · PBO < 25% · beats momentum baseline ·
survives 3-skeptic refutation panel · lockbox never touched (verified by CI
test) · daily reports running 7 consecutive days.

---

Failure policy at every gate: a failed gate sends work BACK (features, labels,
or honesty about a null result) — never forward to parameter tweaking. A null
result ("news adds nothing over momentum") is a publishable outcome, not a
failure of the project.
