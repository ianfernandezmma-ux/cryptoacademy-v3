# CryptoAcademy v3 — Claude onboarding

BTC/ETH ML trading signals with strict point-in-time (PIT) discipline, built
as Ian's capstone rebuild. v2 died of leakage (hyperparameters tuned on the
reported OOS predictions; same-day news joined to the midnight bar; real
numbers were MCC ~0.35 / Sharpe 0.86, not the published 0.56/3.5+). v3's
architecture exists to make that class of error impossible.

**Read next, in order:** `docs/audit-2026-07-11.md` (full-code audit: 26 fixes
applied, refuted-findings list, statistics verdicts) → `docs/plan-v3.md`
(CURRENT execution plan) → `docs/phase4-handoff.md` (conventions, audit
caveats) → `docs/phase4-plan.md` → `PLAN.md` (original master plan).

## The two iron rules

1. **No information enters a feature before its knowledge timestamp.**
   News: `usable_at = max(published_at, first_seen_at) + buffer` (30 min live,
   4h backfilled). Published sources: as-of join on `published_at_utc`.
   Market bars: decision day D uses the completed bar of D-1. CI enforces this
   (anti-leakage tests + assembly tamper test in `tests/`).
2. **Every evaluated configuration is registered** (`validation/registry.py`,
   JSONL at `data/trials/trials.jsonl`). The distinct-identity count is N for
   the Deflated Sharpe Ratio. Register intent BEFORE evaluating (crashed
   trials count). Never evaluate a config without it landing in the registry.

## Current state (2026-07-10)

- **Phases 4.1–4.3 CLOSED** (triple-verified: independent label reimplementation
  bit-exact; adversarial audits applied; stats pinned to published vectors at
  1e-6). Phase 4.4 nearly closed — see "Pending" below.
- **Best models (purged CV, 5 folds, embargo 22d, all registered):**
  LightGBM full-features MCC 0.065 (24h, barrier m=1.5) / 0.093 (96h, m=1.0);
  momentum-only ≈ 0 (honest baseline); PatchTST 0.020/0.028; Chronos-2
  zero-shot 0.014/0.013 (pretraining-overlap caveat — see handoff).
  Meta-labeling (nested-OOF, audit-fixed): 96h +7.8pp hit rate
  (53.8%→61.6%) at 12.8% coverage; REJECTED at 24h (−4.3pp).
- **Data layer** (all automated, ~60 MB total): 1h klines/funding 2020→now,
  5-min derivatives `metrics` since 2020-09, DVOL, CFTC COT (with publication
  embargo), Coin Metrics on-chain, FRED/ALFRED macro (business-day + DST-aware
  publication clocks), stablecoins, ETF flows (+ vintages), F&G, Wikipedia
  attention, live RSS news with per-article sighting stamps, LLM-scored
  articles (calibrated prompt v2, gazetteer-anonymized), daily risk-regime
  scores (pilot-validated classifier v3).

## Pending — see docs/plan-v3.md (authoritative after the 2026-07-11 audit)

1. **Audit 2026-07-11 APPLIED**: 26 confirmed findings fixed (daily-update now
   refreshes metrics/DVOL/wiki/COT + freshness gate; lockbox cutoff ENFORCED
   in build_training_frame — 2026+ events excluded from all training; news
   era cutover + tone/10 rescale; regime slugs anonymized, PROMPT v4;
   rotation permutation in regime gates; dead-letter scoring; etc.). Read
   `docs/audit-2026-07-11.md` before touching anything it names.
2. **Lockbox reality**: 2026-01-01→07-11 was consumed by 4.2–4.4 selection —
   report it only as a contaminated holdout; the pristine lockbox is
   2026-07-12 → end of Phase 5, untouched by construction.
3. **Batch A (runnable now, GPU day)**: labels v2 (hourly-grid reindex; needs
   Ian's OK) → backfill-regime (v4, full series) → validate-regime →
   news-block re-ablation + with/without-regime (4.3 gate-2 close) →
   re-anchor 4.2 selections under the cutoff → ensemble check → 5-seed
   reporting. Then Batch B = Phase 4.5 tribunal per plan-v3.
4. **Meta-labeling claim downgraded**: pooled uplift +5.4pp, t≈1.85 — cite as
   suggestive, never as established, until Phase-5 return streams.
5. Phase 5 (backtest realista + paper, net-of-cost acceptance pre-registered)
   and Phase 6 (web) per plan-v3 batches D/E.

## Layout

```
configs/            assets.yaml (single code path for BTC+ETH), feeds.yaml
src/cryptoacademy/
  cli.py            ALL entry points (scheduled tasks call these too)
  config.py         paths, PIT buffers, truststore injection (TLS proxy!)
  data/             ingestion: binance_vision, altdata (metrics/DVOL/wiki/COT),
                    macro_onchain (CoinMetrics/FRED/stablecoins/ETF), fng, OI
  news/             store (bitemporal DuckDB), pit (usable_at rules), collector,
                    gdelt (harvester), scoring (LLM v2 + anonymize), regime
  features/         resample, price, derivatives, volatility, news (dual-era),
                    matrix (assembly = THE one place time discipline applies)
  labels/           core (CUSUM/triple-barrier/weights), generate (+variants)
  models/           dataset, train (evaluate_config), sweep, meta, dl, chronos
  validation/       cv (PurgedKFold/CPCV), stats (PSR/DSR/PBO), registry,
                    regime_gates
tests/              100+ tests; the anti-leakage ones are sacred
docs/               phase4-handoff.md, phase4-plan.md, research/ briefs
data/ (gitignored)  raw parquet, news.duckdb, labels, features, trials
```

## Commands

```powershell
.venv\Scripts\python.exe -m pytest -q            # full suite
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m cryptoacademy --help # status, collect, backfills,
    # generate-labels, build-matrix, train-baselines, run-sweep, run-meta,
    # run-patchtst, run-chronos, backfill-regime, validate-regime, daily-update
```

Scheduled tasks (Task Scheduler folder "CryptoAcademy"): NewsCollector 10min,
NewsScoring/GdeltHarvester/OpenInterestArchiver hourly, DailyUpdate 08:30,
OptionsChainSnapshot 08:05. They hold the venv exe and the DuckDB lock.

## Environment gotchas (they WILL bite)

- **TLS-intercepting proxy**: `uv ... --system-certs` always; scripts need
  `import truststore; truststore.inject_into_ssl()` (config.py does it — so
  `from cryptoacademy import config` first in ad-hoc scripts).
- **DuckDB single-writer**: collector/scorer hold `data/news.duckdb`; retry
  connects (up to 30×20s observed), hold write connections briefly.
- **Windows console**: `$env:PYTHONIOENCODING="utf-8"` for non-ASCII prints.
- **Local LLMs (Ollama)**: qwen3.6:35b-a3b = scorer/regime/reports — ALWAYS
  `think:false, temperature 0, format=json_schema` for structured calls
  (thinking mode returns empty response). One big model resident at a time.
  qwen3-embedding:4b dedup (threshold 0.87), qwen3.6:27b coding. English-first
  everywhere (user decision; gemma4 was removed).
- **Torch**: 2.13+cu130 native Windows (index pinned in pyproject); set
  `CUBLAS_WORKSPACE_CONFIG=":4096:8"` before training; no torch.compile.
- **git push**: PAT in `.env` (`GITHUB_PAT`), push via
  `git push "https://x-access-token:$pat@github.com/ianfernandezmma-ux/cryptoacademy-v3.git" main`
  and filter the token from any echoed output.

## Working agreement with Ian (established over the project)

- He approves phases; within a phase, do everything you can autonomously and
  leave him only account/GUI tasks with exact instructions. Spanish in chat;
  English in code/docs/reports. Commit + push at every coherent milestone
  (commit messages end with the Claude co-author line). Use background agents
  for research and adversarial review (budget ~10 per sub-phase); apply their
  findings and credit them. Honest nulls are publishable results — never
  massage a number. When a metric looks too good OR suspiciously degenerate
  (e.g. identical across configs), investigate before accepting it.
