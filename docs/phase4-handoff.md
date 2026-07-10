# Phase 4.1–4.3 Handoff → Phase 4.4 (Meta-labeling + DL challengers + ensemble)

Audience: agents working on Phase 4.4. Everything below is verified, committed
and tested (repo: C:\CryptoAcademy, 82+ tests green, CI on push). Read this
FIRST; read the referenced modules before touching them.

## Project one-liner

BTC/ETH ML trading signals with strict point-in-time discipline. v2 of this
project died of leakage (tuning on reported OOS, same-day news in features);
v3's entire architecture exists to make that impossible. The one rule: no
information enters a feature before its knowledge timestamp, and every tested
configuration is registered.

## What exists and is certified

### 4.1 — Labels + validation infrastructure (gate CLOSED)
- `labels/core.py`: CUSUM event filter + triple-barrier labeling + AFML sample
  weights. Verified bit-exact by an independent clean-room reimplementation
  (485/485 sampled events). Conventions: sigma = EWM (adjust=False, biased) of
  24h log returns on the hourly grid, span 100d, min 30d; touch scan starts
  t0+1; barrier-price fills; pessimistic double-touch tie-break; end-of-data
  and NaN-gap windows DROPPED.
- `labels/generate.py`: k calibrated on SURVIVING events (k=1.5 -> ~2,500
  events per horizon pooled BTC+ETH). Default barrier_mult=1.5; variants
  m∈{1.0, 2.0} in suffixed parquets (`labels_{asset}_{h}_m10/_m20.parquet`),
  SAME event sampling (guarded at load).
- `validation/cv.py`: PurgedKFold + CombinatorialPurgedCV (N=6,k=2 -> 15
  splits, 5 paths, path_map with real invariants tested). Embargo 22d.
  A leakage simulation test proves purging kills a nearest-neighbor cheat
  (~88% shuffled-KFold -> ~55% purged).
- `validation/stats.py`: PSR/DSR/E[maxSR]/MinTRL/PBO-CSCV pinned against 7
  published vectors at 1e-6 (Bailey & López de Prado papers, pypbo,
  rubenbriones). Conventions: per-period SR, RAW kurtosis (Normal=3),
  sqrt(T-1), DSR denominator uses observed SR.
- `validation/registry.py`: append-only JSONL trial registry. Identity =
  hash(phase+model+horizon+config); register_trial BEFORE evaluation (crashes
  count); re-runs of the same identity dedupe. `n_trials(phase=..., ...)` is
  the N for DSR. NEVER evaluate a config without it landing here.

### 4.2 — Baselines + sweep + selection + ablations (gate CLOSED)
- `models/dataset.py`: pooled BTC+ETH training frame — labels asof-joined
  backward to the PIT feature matrix (event during day D sees features known
  at D 00:00). 108 features. asset_id is bookkeeping, NOT a feature.
- `models/train.py`: `evaluate_config` = purged-CV evaluation, registers
  intent first, logs metrics after; fixed 0.5 threshold; no early stopping
  (deliberate — fold-internal validation is a leak surface).
- `models/sweep.py`: Optuna sweep (params × barrier_mult), SHAP-stability
  selection, block ablations.
- **Results on healed data** (data/trials/phase42_report.json):
  - 24h: best purged-CV MCC 0.065 (m=1.5). Signal driver: DERIVATIVES
    (funding/OI/positioning) — alone 0.045; without them ~0.
  - 96h: best MCC 0.093 (m=1.0), acc ~54%. Signal driver: mixed, derivatives
    0.055 alone; macro 0.028-0.049.
  - Momentum-only baseline: MCC ≈ 0 both horizons (honest null).
  - News block: ≈ 0 — DATA NOT YET AVAILABLE (see pending). Do not interpret.
- **Audit verdicts (both adversarial reviews)**: no hard train/test leakage.
  Standing caveats: (F1) any score obtained with SHAP-selected features on the
  same folds is selection-biased — tagged `INLOOP`, report full-feature score
  beside it; (F2) MCC/mean_ret are NOT comparable across barrier_mult variants
  (label difficulty and touch returns shift mechanically) — cross-variant
  comparison only on Phase-5 return streams; (F3) sample weights are computed
  full-sample (proven non-inflating, but recompute per-fold before headline
  numbers — REGISTERED as a pending trial dimension `weights: per-fold`).

### 4.3 — News/LLM layer calibrated + regime classifier (gate: part 1 CLOSED,
### part 2 pending GDELT completion)
- `news/anonymize.py`: gazetteer entity anonymization (~110 entities,
  role-preserving descriptors). Measured: hindsight gap on famous events 0.25
  sentiment raw -> 0.00 anonymized; year-stripping alone was useless (7%).
  Applied to ALL scoring (live + backfill) for distribution consistency.
- `news/scoring.py`: SYSTEM_PROMPT v2, calibrated on a 40-article gold set:
  event-type accuracy 55% -> 92.5%, regulation precision 0.30 -> 1.00.
  Prompt changes REQUIRE re-measuring against the gold set (scratchpad
  run_eval.py/gold.json). Scores carry model="qwen3.6:35b-a3b|v2". The
  pre-v2 corpus (1,530 rows) was wiped; hourly task re-scores.
- `news/regime.py`: daily risk-regime scorer (risk_appetite -2..+2,
  crypto_stress/macro_stress 0..3, narrative, confidence) over GDELT URL-slug
  pseudo-headlines. PILOT-VALIDATED on COVID window: stress 3 fired 3 days
  before Black Thursday, nailed Mar 12 at conf 0.95, calm January stayed
  0/+1. Load-bearing detail: crypto/macro headline split (15+7) — naive top-k
  missed Black Thursday entirely. Consume via `smoothed_regime_features()`
  (3-day median + delta, keyed decision_day = D+1).
- `validation/regime_gates.py`: standalone quality gates (Spearman stress vs
  FORWARD 7d realized vol with permutation test, event-study drawdowns,
  persistence, AUC), self-validated (oracle passes / noise fails / constant
  degenerates cleanly).

## LLM runtime facts (local, Ollama)
- qwen3.6:35b-a3b: scorer + regime + reasoning. ALWAYS think:false +
  temperature 0 + format=json_schema for structured calls (thinking mode
  returns an empty response field). ~93 tok/s; one big model resident at a
  time (a second silently pushes inference to CPU).
- qwen3-embedding:4b for dedup (threshold 0.87). qwen3.6:27b for coding.
- English-first policy everywhere (user decision).

## Environment gotchas (will bite you)
- TLS-intercepting proxy: every uv command needs `--system-certs`; every
  script needs `import truststore; truststore.inject_into_ssl()` (config.py
  does it globally for package code).
- DuckDB single-writer: the collector (10 min) and scorer (hourly) take the
  news.duckdb lock. Hold connections briefly; retry connect (up to
  30x20s observed necessary); read_only when possible.
- Windows console: set PYTHONIOENCODING=utf-8 for scripts printing non-ASCII.
- Scheduled tasks (Task Scheduler, folder CryptoAcademy): NewsCollector 10min,
  NewsScoring 1h, GdeltHarvester 1h, OpenInterestArchiver 1h, DailyUpdate
  08:30, OptionsChainSnapshot 08:05. They fight for the venv/exe — uv sync
  fails while one runs (retry).
- Registry discipline: use evaluate_config or register/log manually for EVERY
  evaluated configuration, including DL and meta-label trials (phase="4.4").

### Regime standalone validation — verdict on the available window (313 days, 2020-01..2020-11)
Run 2026-07-10 via `validate-regime` (forward-outcome gates, permutation-tested):
- RAW daily scores: persistence FAILS (mean run 1.9d — the classifier
  flip-flops), Spearman FAILS. Confirms the pilot's instruction: consume
  SMOOTHED (3-day median), never raw.
- SMOOTHED scores: persistence PASS (3.8d runs, clean diagonal transition
  matrix), event-study PASS (dd risk-off > risk-on), extreme-flag AUC 0.70
  (crypto_stress>=2 ranks top-decile forward-vol days well — supports the
  gate/conditioning use, which is what the literature recommends anyway).
  Linear Spearman rho 0.096 (p=0.045) — BELOW the 0.2 gate on this window.
- Honest reading: the ordinal level is weakly linear in forward vol over a
  single-year window dominated by one crisis; the EXTREME flag carries the
  value. 4.4 must (a) re-run gates on the full 2020-2026 series when GDELT
  completes, (b) feed the model the smoothed ordinals + the stress>=2 flag +
  interactions, and let the with/without-regime comparison decide — a null
  is acceptable.

## Pending items 4.4 inherits
1. **GDELT backfill in progress** (~313/2,370 days done; hourly task; ~2-3
   days to completion). Until then: news-block ablation is unfinished
   business, and regime history covers only the harvested window. When GDELT
   completes: run `backfill-regime` (resumable), re-run news ablation, run
   the with-regime vs without-regime gated comparison — that comparison is
   the FORMAL CLOSE of 4.3's gate 2, executed within 4.4.
2. Article re-scoring with v2 in progress via hourly task (~1,530 articles).
3. Per-fold sample weights (F3) — implement before Phase 4.5 headline runs.
4. Lockbox reminder: data from 2026-01-01 is NOT lockboxed yet in code — the
   4.5 loader must enforce it; 4.4 should avoid optimizing anything against
   2026 data specifically.

## Phase 4.4 scope (from docs/phase4-plan.md)
- Meta-labeling: primary LightGBM side -> side-adjusted triple-barrier
  (labels/core.py supports side=) -> small calibrated secondary (Platt, ≤8
  features, heavy regularization); check per-regime lift, not pooled AUC.
- DL challengers on the RTX 5090: PatchTST + N-HiTS (neuralforecast), RevIN,
  same purged-CV protocol, same registry. Windows-native torch cu128 first;
  WSL2 fallback (user must install — B-block item).
- Zero-shot Chronos benchmark row.
- Ensemble (probability averaging) — keep only if it beats the primary under
  purged CV at honest trial accounting.
- Gate: documented comparison table; every trial registered; DL beats nothing
  is an acceptable (publishable) outcome.
