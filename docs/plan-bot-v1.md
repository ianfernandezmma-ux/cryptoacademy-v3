# Plan: CryptoBot v1 — Personal Automated Paper-Trading Bot

**Status: FINAL v1.2** (2026-07-15) — draft v1.0 was adversarially reviewed by
three independent agents (statistics/overfitting, security/operations,
economics/coherence); all confirmed findings are integrated below (changelog
in §11). v1.2 updates the local-AI policy per Ian: the local AI is allowed to
run — **but only while Ian's manual switch is on** (`cryptoacademy ai on/off`,
never auto-started, so it can't interrupt gaming). The bot's *decisions* still
never depend on the AI being on.
**Supersedes** `docs/plan-v3.md` as the active execution plan while the
capstone is paused (Ian's decision, 2026-07-15). The capstone (Phase 6 web)
resumes only after this bot is complete and stable.

Synthesized from six research agents (video analysis, strategy evidence,
framework survey, memory-system design, risk layer, repo architecture) plus
three adversarial reviews. This is engineering and research methodology — not
investment advice. The bot is **paper trading only**; any step beyond paper
is a separate future decision by Ian, outside this plan's scope.

---

## 1. Vision and non-negotiable principles

**Goal:** a fully automated paper-trading bot — Binance spot, **long-only**,
**BTC + ETH**, decisions at the **96h swing horizon** (~daily decision cycle)
— that Ian operates from a local web UI without touching code, whose central
pillar is **memory**: an append-only journal of every decision that makes the
bot auditable, attributable, and improvable *through the registry*, never
through self-mutation.

**Why 96h only (v1):** the plan's own cost arithmetic kills 24h — at
~0.30–0.40% per round trip and the trade frequency a daily-horizon strategy
implies, friction consumes more than any honest estimate of the edge (24h is
also where meta-labeling was REJECTED, −4.3pp). "Does anything survive at
24h net of costs" remains a B2 research question whose **default answer is
no**; 24h re-enters production only via a registered trial that demonstrably
beats the §5 cost model. Single-horizon also eliminates the two-horizon
netting problem entirely.

**The three iron rules (v3's two, plus one new):**

1. **PIT discipline extends to production.** No information enters a decision
   before its knowledge timestamp. Every decision event records
   `features_max_knowledge_utc` and asserts it `<= decided_at_utc`. Execution
   is simulated at prices strictly *after* the decision timestamp. Clock
   integrity is checked (Binance server time, §5) because the assertion is
   only as good as the clock.
2. **Every evaluated configuration is registered** before evaluation. This
   includes: every strategy parameter set, the combination rule, every future
   challenger, and the paper period itself. **N for any DSR = the union of
   the lab registry (`C:\CryptoAcademy\data\trials\trials.jsonl`, all v3
   phases) and the bot registry**, dual-N convention (raw + clustered) as in
   plan-v3. The bot's registry lives at `data/trials/trials.jsonl` inside the
   bot repo and is append-merged with the lab's for any statistic.
3. **Memory informs; only the registry authorizes.** The journal generates
   hypotheses and monitors health. No parameter, threshold, model, or rule
   changes in production except through a registered trial validated under
   purged CV. The bot never modifies itself. (The rigorous version of the
   "bots lose because they have no memory" thesis — and the explicit
   rejection of the video's self-mutating "learnings file".)

**Honest expectations (pre-committed):** measured edge is small (LightGBM MCC
0.093 at 96h; momentum baseline ≈ 0). Sizing assumes honest net SR
**0.2–0.5**; a good outcome is beating a vol-targeted benchmark on
risk-adjusted terms, mostly by losing less in bear regimes. Any result
projecting net Sharpe > 2 is treated as a bug until proven otherwise. An
honest null ("no skill beyond vol-targeted beta") is an acceptable, reportable
outcome. Base rates: >80% of measured retail traders lose net of costs.
(Review note F13: the draft quoted friction and Sharpe bands with mixed
units; B2 recomputes the friction table with defined units — costs per round
trip, trades counted as flat-to-flat episodes net of buffers — and restates
the expectation band from it. Until then, 0.2–0.5 net SR is the only number
used anywhere.)

**Video verdict (Miles Deutscher, PBBSMSyU674):** one genuinely valuable
insight — persistent memory/feedback loop — adopted in rigorous form (ledger
+ attribution + registered retraining). Rejected: LLM as live decision brain;
conversational ad-hoc backtesting outside the registry; per-trade
auto-learned rules (N=1 overfitting); unverifiable profit claims. Adopted
operational nuggets: paper-first, small-size scaling, key hygiene.

---

## 2. Architecture: two folders

### 2.1 The dirty lab — `C:\CryptoAcademy`

Stays what it is: research, data collection (scheduled tasks keep running —
forward-only archives must not lose data), experiments, docs, explanatory
material for Ian. Claude's workspace.

### 2.2 The clean bot repo — `C:\CryptoBot` (new private GitHub repo `cryptobot`)

Hermetic and portable: **clone + `bootstrap.ps1` = running bot on any Windows
PC.** No secrets, no data, no research clutter in git.

```
cryptobot/
├── pyproject.toml            # ALL deps pinned; uv-managed; NO torch/GPU deps
├── uv.lock                   # committed — reproducibility contract
├── README.md                 # runbook: install, operate, MOVE-TO-NEW-PC
│                             #   (step 1: decommission old machine), recover
├── .gitignore                # data/, .env, *.duckdb, logs/, .venv/, dist/
├── .env.example              # NON-secret config (mode, UI port, proxy, paths)
├── bootstrap.ps1             # idempotent one-shot setup (§2.4)
├── .pre-commit-config.yaml   # gitleaks + ruff
├── .github/workflows/ci.yml  # pytest + ruff + gitleaks (repo AND unpacked
│                             #   wheel contents + manifest allowlist)
├── libs/
│   ├── cryptoacademy-X.Y.Z-py3-none-any.whl   # frozen research code (§2.3)
│   └── VENDORED.md           # source tag + commit SHA + build date
├── configs/strategy.yaml     # assets, horizon, S1–S2 params, combination
│                             #   rule, risk limits, per-feed max_age clocks
│                             #   (mirrors registered trial configs)
├── models/                   # frozen LightGBM boosters + model_card.json
│                             #   (training window, CV metrics, feature list,
│                             #    input-schema contract version, config_hash)
├── src/cryptobot/
│   ├── cli.py                # typer: init-db | run-cycle | serve-ui | status |
│   │                         #        backup | restore --target | test-telegram
│   ├── settings.py           # CRYPTOBOT_HOME override; truststore; explicit
│   │                         #   proxy config; keyring reads; UTF-8 file logging
│   │                         #   (pythonw-safe: no bare print in task context)
│   ├── engine/
│   │   ├── cycle.py          # run-cycle = fetch → validate → decide → orders
│   │   │                     #   → journal, ONE process, ONE transaction (§7)
│   │   ├── strategies.py     # S1–S2 (pure functions of the feature frame)
│   │   ├── sizing.py         # vol targeting, caps, buffers (§4)
│   │   ├── risk.py           # rails: kill switches, staleness, sanity (§5)
│   │   └── broker.py         # PaperBroker (shadow ledger vs live public prices)
│   ├── datafeeds/
│   │   ├── fetch.py          # daily pull of ONLY re-downloadable public feeds
│   │   │                     #   (REST klines for live edge; Vision = backfill)
│   │   └── contract.py       # validates every frame against the wheel's
│   │                         #   input-schema contract; violation → NO-OP+page
│   ├── journal/              # db.py, schema.sql, migrations/, backup.py
│   ├── notify/telegram.py    # digest + pages; INBOUND commands allowlisted
│   │                         #   by Telegram user ID (§5)
│   └── webui/app.py          # NiceGUI, 127.0.0.1, session token + Origin
│                             #   allowlist (§7); hosts the Telegram poller
├── scripts/register_tasks.ps1  # Task Scheduler folder "CryptoBot" (user-level)
├── tests/                    # test_no_gpu.py, test_pit_decision.py,
│                             #   test_journal_appendonly.py, test_kill_switch.py,
│                             #   test_crash_mid_cycle.py, test_schema_contract.py,
│                             #   test_golden_days.py, test_telegram_allowlist.py,
│                             #   test_weekend_staleness.py, test_two_writers.py
└── data/                     # GITIGNORED: market cache, journal.duckdb,
                              #   trials.jsonl, logs
```

### 2.3 Dependency strategy: committed wheel

The bot depends on `cryptoacademy` (feature pipeline, PIT joins, validation)
as a **wheel built at a tagged commit and committed to `libs/`**: hermetic
portability (no second GitHub auth through the TLS proxy on a fresh PC),
immutability, churn isolation. **Build from `git archive` of the tag** (clean
tree — never the working directory), and CI unzips the wheel, runs gitleaks
on its contents, and asserts a file-manifest allowlist (review m3: a binary
wheel otherwise bypasses secret scanning).

**Prerequisites in CryptoAcademy (Phase B0):**
1. `config.py`: honor `CRYPTOACADEMY_HOME` before the `__file__`-derived
   `PROJECT_ROOT` (today a wheel install breaks paths silently).
2. `pyproject.toml`: move `torch`, `chronos-forecasting`, `shap`, `optuna`
   to a `train` extra; guard module-level torch imports.
3. **Export an input-schema contract** (review M5): column names, dtypes,
   units, timezone, nullability for every feature block the frozen pipeline
   consumes, versioned, shipped inside the wheel. The bot validates every
   fetched frame against it at runtime (violation → NO-OP + page) and CI runs
   a **golden-day regression test**: for ~5 pinned historical dates, the
   bot's fetched-and-assembled feature vectors must match lab-computed
   vectors within 1e-9. This is the defense against silent drift between the
   bot's `fetch.py`, the evolving lab collectors, and the frozen wheel.
4. Promotion ritual: `git tag bot-YYYY.MM.N` → `uv build` (from git archive)
   → copy wheel → `VENDORED.md` → `uv lock` in cryptobot → commit.

### 2.4 Bootstrap and portability

`bootstrap.ps1`: preflight (winget uv, `uv python install 3.12`) → `uv venv;
uv sync --system-certs` → interactive secrets via `keyring` into Windows
Credential Manager (Telegram token/chat-id, allowlisted Telegram user ID,
restic password; **no Binance production keys — paper needs none**) →
**restic-password escrow gate**: the password is displayed once with a forced
acknowledgment ("stored in password manager / on paper") before bootstrap
continues (review C3: otherwise every disaster the backup exists for also
destroys the only key) → `.env` from example (explicit proxy settings — the
scheduled, non-interactive session may not inherit per-user proxy discovery)
→ `cryptobot init-db` → `cryptobot fetch-data --backfill` (~400 days of
public feeds) → `register_tasks.ps1` → smoke test **run from the scheduled
context, not an interactive shell** (review m1) → print UI URL.

**Machine identity (review M4):** every journal event records an instance
GUID. On startup the bot compares its GUID with the journal's last writer and
**refuses to run** (page + halt) on mismatch without an explicit
`--take-over` handshake that journals the migration. Runbook step 1 for
moving: unregister the "CryptoBot" task folder on the old machine. Restic
host tags are per-machine. This prevents two live bots double-journaling
into one backup repository.

### 2.5 Production data constraint (fails closed)

The v1 production model/strategies may only use **re-downloadable public
feeds**: Binance klines/funding (REST for the live edge, Vision archives for
backfill only — Vision publishes too late for an 08:45 decision), derivatives
metrics with history, DVOL, FRED/ALFRED, Coin Metrics community, F&G, ETF
flows. **Excluded from v1 production:** news/LLM-scored features — for three
reasons that survive the new AI-switch policy: (a) `news.duckdb` with its
per-article sighting stamps is lab-local and cannot be re-downloaded on a
second PC; (b) the bot's decisions must never depend on the AI switch being
on (Ian may keep it off for days while gaming — a decision pipeline that
starves without the GPU is not unattended); (c) the S5 contamination finding
below. Also excluded: forward-only archives (Binance OI >30d, Deribit
snapshots — cannot be re-downloaded on a second PC, becoming a hidden hard
dependency on the lab). **Enforcement is a CI/promotion-time check that
diffs the model card's feature list against the allowed blocks and fails
closed** (review m5/F4: this check exists precisely because the first thing
it would have caught is real — see S5 below). News features remain available
for *research* in the lab.

---

## 3. Strategy layer (pre-registered, evaluated once)

Rule-based, explainable, deliberately lean. Trend/TSMOM is the only family
with multi-team, partially net-of-cost evidence in crypto; its edge has
decayed post-2021 and expectations are set accordingly.

| ID | Family | Logic (fixed parameter sets) | Status |
|----|--------|------------------------------|--------|
| S1 | Regime gate (foundation, not alpha) | Long-eligible only when close > {100d, 200d} SMA; entries only when green | **v1** |
| S2 | Donchian breakout trend | Enter on N-day high close, N ∈ {10, 20}; exit on N/2-day low or ATR trail | **v1** |
| S3 | EWMAC momentum (Carver lineage) | 8/32 + 32/128 EWMA crossovers, long-only clip, vol-scaled, banded rebalance | **v1 only if** it survives post-buffer cost math in B2 (frequencies must be reported net of §4 buffers) |
| S4 | Funding washout overlay | thresholds on funding deciles | **CUT from v1** — "few episodes/yr" cannot be validated inside the paper window (research-only) |
| S5 | Meta-labeled trend | LightGBM P(win) gate on S2 | **CUT from v1** — the existing meta-model is verifiably trained on news-block features (`models/meta.py:84`) and is unpromotable under §2.5. A §2.5-compliant retrain is a NEW registered trial with no guaranteed uplift (the +7.8pp is officially "suggestive" and news-contaminated). Candidate for the first quarterly evaluation, not for v1. |

Excluded with reasons: 24h horizon (§1), dip-buying/MIN (failed 2022–24
OOS), seasonality (non-robust), shorting/leverage (out of mandate), ML
picking direction (never).

**Combination rule — frozen ex ante (review F2):** the rule for combining
S1/S2(/S3) into one signal scalar is committed and registered **before any
B2 evaluation runs**, as a formula with no performance input: equal risk
weight across the families that individually pass a pre-stated,
performance-blind inclusion criterion (e.g., post-buffer turnover within
bounds), or inverse-correlation-cluster weights computed mechanically from
the signal correlation matrix only. The combined configuration is itself one
registered identity, evaluated once. If more than one weighting is ever
computed, each counts toward N. "Handcrafting after seeing the CV results"
is recognized as an unregistered optimizer and is forbidden.

**Definitions (review F1/F2):** a **closed round trip** = one flat-to-flat
episode per asset; banded rebalances within an episode are orders, not round
trips, and are excluded from hit-rate statistics. B2 reports expected round
trips/yr **net of §4 buffers** per config; those numbers — not the draft's
gross table — feed the §8 sample-size rule. (The draft's "365 acted
trades/yr" framing was wrong for this bot by 4–10×; realistic 96h trend
figures are ~8–20 round trips across both assets per 6 months, since BTC/ETH
are ~0.8-correlated and S1 gates out large regime stretches.)

**Protocol:** register all parameter sets + the combination rule (≈8–12
identities) in the bot registry **before** evaluation → evaluate once under
purged CV, net of the §5 cost model, on history **up to the lockbox cutoff
(2026-07-11)** → DSR with N = lab ∪ bot registries (iron rule 2) → champion
= the pre-registered selection rule's output (best DSR subject to
cost-survival), frozen. **B2 exit reports the champion's DSR and PSR
explicitly** so no later claim can retro-inflate backtest significance
(review F12). The pristine lockbox (2026-07-12+) is consumed by the paper
test only — see §8 and the freeze rules in §9/B3–B5.

---

## 4. Position sizing (defaults, pre-registered)

- **Portfolio vol target: 12% annualized** (range 10–15) ≈ quarter-to-half
  Kelly for honest net SR 0.2–0.5. Never above half-Kelly under any config.
- Per-asset weight: `signal_scalar × vol_target × risk_weight / σ_i`,
  σ = 30d EWMA of daily returns, floored at 20% annualized; risk_weight
  50/50. **When S1 gates one asset red, the other keeps its 50% budget —
  under-deployment is accepted** (conservative; consistent with "flat in
  bear is a feature") (review F13-coherence).
- Expected consequence: typical deployed exposure ~20–40% of capital
  (BTC-ETH correlation ~0.8 ≈ 1.2 effective assets). Correct, not shy.
- Caps: per-asset 50% equity; gross soft 80% / hard 100% (spot, no
  leverage). Carver overlay against vol-estimate breakdown.
- No-trade buffer: trade only if |target − current| > 10% of target AND
  notional ≥ 1% of equity. Signal deadband: expected move must clear ~2×
  round-trip cost.

## 5. Risk rails, cost model, and control channel

| Rail | Trigger → action |
|------|------------------|
| Hard kill | −20% DD from HWM → flatten, halt, page; restart only after written manual review |
| Soft de-risk | −10% DD → halve vol target; restore within 5% of HWM |
| Daily loss | −2.5%/day → pause entries 48h + page; −5%/day → kill-switch event |
| Consecutive losses | 8 → alert + review note; 12 → pause entries pending review (never auto-kill on streaks) |
| Stale data | **Per-feed staleness clocks** (review M1): each feature block declares `max_age` against its *expected publication calendar* (business-day and DST-aware — FRED/COT/ETF flows are legitimately >24h old every weekend; the lab's publication-clock logic ships in the wheel). Market bars: newest completed 1h bar >2h late → NO-OP. Any required block past its own clock → NO-OP (hold) + alert. Blind >72h → flatten + halt. Fail SAFE = no new risk. A simulated-Saturday test is in CI. |
| Data validity | NaN/schema-contract check (§2.3); bar close ±25% of prior → quarantine + NO-OP; degenerate model output → alert |
| Clock integrity | At cycle start compare local clock vs Binance `/api/v3/time`; drift >60s → NO-OP + alert; measured drift journaled every cycle (review m4 — the PIT assertion is only as good as the clock) |
| Order sanity | ≤25% equity/order; ±2% price band; deterministic idempotent client IDs; ≤8 orders/day; daily ledger↔broker reconciliation, mismatch → halt |
| Dead-man's switch | **External** (review C1): run-cycle pings a hosted heartbeat endpoint (healthchecks.io-class) on success; the *external service* alerts Telegram/email after >26h of silence. The local watchdog task remains for fast in-session paging, but the machine-off/hibernate/update-reboot scenarios — the dominant ones on a gaming PC — are only detectable from outside. One HTTPS GET; ping URL in keyring. |
| Missed cycles | Every scheduled decision that ran >X h late or not at all is journaled as a `missed_cycle` event (derivable from cycle_ids vs calendar); scheduled-vs-actual decision time recorded on every decision; a **missed-cycle budget is part of G1** (≤2/month, none >48h, all with clean catch-up) (review M8) |
| Manual override | Persistent pause flag (file, survives restarts), checked at top of every cycle. Telegram `/pause /flatten /resume /status`: **inbound commands accepted only from the allowlisted Telegram user ID; all others dropped and logged** (review C2); `/resume` and `/flatten` require a typed confirmation phrase; the poller is hosted by the always-on UI process AND run-cycle drains pending updates at cycle start, so a command sent while nothing listened still takes effect before the next trade. Test: command from non-allowlisted ID → ignored + logged. |

**Paper fill model (defines "net" everywhere, deliberately conservative):**
decision on completed data as of the cycle timestamp → fill at the next-1h-bar
open after the decision timestamp, at the *worse* of reference/next-open; fee
0.10%/side (no BNB discount assumed); slippage +5 bp/side BTC, +10 bp/side
ETH, doubled when 30d vol > its 80th percentile (**percentile window fixed:
expanding from 2020-01-01 through the cycle date, definition frozen now** —
review F14); all-or-nothing fills. Round trip ≈ 0.30% BTC / 0.40% ETH. Never
maker fees, never mid-price, never same-bar fills. Paper needs **no API
keys** (public endpoints + shadow ledger; Binance spot testnet rejected:
unrealistic liquidity, broken sandbox routing).

**Time semantics (review F12-coherence):** all data, journal timestamps, and
PIT assertions are UTC. "Daily" = the UTC day; the decision cycle targets
07:00 UTC (≈09:00 CEST / 08:00 CET — local trigger time drifts with DST, the
data semantics do not). The lab's DailyUpdate (08:30 local) and the bot's
cycle are staggered ≥1h with jittered generous-backoff retries (shared
IP/proxy/rate limits — review m2).

## 6. Memory: the journal (the pillar)

Append-only, event-sourced, DuckDB (`data/journal.duckdb`) + monthly Parquet
feature snapshots. Full DDL in the memory-design report; core tables:
`decision_event` (one row per asset×cycle **including skips/holds**, with
feature-snapshot hash, `model_id`, `config_hash` — same identity system as
the registries —, dual timestamps, `is_shadow`, action + machine
reason-code, instance GUID, clock drift, scheduled-vs-actual time),
`order_event` (state transitions; TCA benchmark-price *columns* kept for the
live future, TCA **reporting cut from v1** — on simulated fills it can only
recover the parameters we typed in), `fill_event` (fill vs reference, fee/
slippage model + params), `position_snapshot`, `equity_snapshot` (with
same-period benchmark returns), derived `trade_outcome` (rebuilt at
cycle-end: net returns, predicted-vs-realized → calibration data),
`model_health_event`, `review_note`, `hypothesis` (status reaches 'tested'
**only** via `trial_ids` pointing at registry entries — schema-enforced),
`missed_cycle`, `intervention_event` (every manual pause/flatten/resume),
`restore_drill`, `migration_event`.

**Write-concurrency policy (review M9):** exactly two writer processes with
disjoint tables and disjoint schedules — (1) `run-cycle` (daily, single
DuckDB transaction per cycle: decisions, orders, fills, snapshots, health
metrics, trade_outcome rebuild, ending with a `cycle_complete` event); (2)
the UI/poller process (`review_note`, `intervention_event`; pause flag is a
*file*, not a DB row). Backup exports from a read-only connection at a fixed
time that never overlaps run-cycle, with retry; a failed export pages (a
silent backup gap is an incident). A two-concurrent-writers test is in CI.

**Crash safety (review M3):** `cycle_id = UTC date × config_hash`; run-cycle's
first action is "if `cycle_complete` exists for cycle_id → exit 0"; all
writes for a cycle commit atomically. A kill-mid-cycle tamper test (process
killed between decision and order writes; rerun must converge to exactly one
decision row) is a **B3 exit criterion**.

**Guarantees:** no UPDATE/DELETE in app code (corrections are compensating
events); PIT assertion on every decision write; `schema_migrations` +
forward-only migrations + read-time upcasters; nightly
`EXPORT DATABASE (FORMAT PARQUET)` + JSONL event mirror; **quarterly restore
drill on a non-source target** — `restore` requires explicit `--target`,
refuses the live journal path, and the drill restores to temp + compares
row-counts/hashes, journaled as `restore_drill` (reviews C3, m6).

**The learning loop, v1 (leaner than the draft — reviews F5/F6/F9):**

- **The champion is FROZEN for the entire paper window. No monthly refits.**
  Refits broke the frozen-wheel portability story, made G2 an
  apples-to-oranges comparison, created an unattended model-swap risk with
  no output gate, and were the single biggest item in the owner's labor
  bill. Model staleness over 6–12 months is itself information; the drift
  monitors report it.
- **No challenger machinery in v1.** There is no champion track record to
  challenge yet. The `is_shadow` flag stays in the schema; the machinery is
  built when the first challenger is actually registered (earliest: first
  quarterly evaluation). Every future challenger counts toward N; promotion
  criteria (2-quarter shadow, paired-daily-return comparison with HAC SE,
  mechanical outlier rule: "difference survives deleting the challenger's 2
  best days") are pre-registered then, per the draft's champion/challenger
  design.
- **LLM journal roles are switch-gated, never load-bearing.** Plain-English
  "why this trade fired / was skipped" is **derived mechanically from the
  structured ledger** for the UI — always available, no AI needed. The LLM
  reviewer (narrate weekly summaries, tag closed trades with the error
  taxonomy, propose hypotheses — never parameters, never evaluation results)
  runs **only while Ian's AI switch is on** (`ai on`): pending review work
  queues and executes when the switch is next enabled, and skips silently
  otherwise. It writes via the UI process's writer channel only. The bot's
  decision path has zero dependency on any of this.
- **Hypothesis hygiene (review F10):** each hypothesis is tagged with the
  observation window that generated it; any validating CV must exclude that
  window (enforceable from `hypothesis` provenance).
- Drift/health monitors (computed inside run-cycle): PSI on top-k features +
  score distribution (warn 0.1 / alarm 0.25; **one recalibration allowed at
  a single pre-scheduled date after the burn-in quarter, journaled** —
  review F14), rolling Brier/ECE vs CV baseline (reported with CIs), CUSUM
  on daily net PnL, binomial control chart on the rolling hit rate,
  operational freshness. Alarms → investigate or pre-registered de-risk
  (size → 0 allowed); **never auto-retrain**.

**Sample-size reality (corrected — review F1):** at realistic 96h-trend
frequencies (~8–20 round trips per 6 months across both assets), hit-rate
CIs are ±15–20pp — the journal cannot rank alpha, period. What it *can*
teach quickly: cost drag (near-deterministic), plumbing bugs, gross
calibration failure, catastrophic regime breaks. Hypothesis confirmation
always happens on the multi-year research history in the lab.

## 7. Execution engine, UI, operations

- **Build-thin custom engine** (~1.5–2.5k LOC incl. tests) over adopting
  freqtrade/Nautilus/Jesse/Hummingbot: at ~1 decision/day, spot, long-only,
  2 assets, paper-only, frameworks solve absent problems while breaking PIT
  auditability at the external-signal join. Public REST endpoints (ccxt or
  httpx) as the data/price primitive. **Documented fallback:** freqtrade in
  hybrid mode if scope ever grows to many pairs, partial-fill realism,
  shorts/futures, or live execution.
- **One daily task, not two (review M2):** `run-cycle` performs fetch →
  contract-validate → decide → simulate → journal sequentially in one
  process ("run when missed" ON, "wake computer" OFF). This kills the
  FetchData/Decide catch-up race that would otherwise guarantee a NO-OP on
  exactly the wake-after-absence days when the position most needs
  re-evaluation. A catch-up run after a gap ≥2 days journals a distinct
  `gap_resume` event and pages before acting.
- **UI: NiceGUI**, single always-on process (at-logon task, pythonw),
  hard-coded 127.0.0.1 — hardened per review M6: **per-boot random session
  token in the printed URL, strict Host/Origin allowlist, NiceGUI
  `storage_secret` set, all state-changing actions authenticated POST/WS**
  (loopback is not a boundary against DNS-rebinding or other local processes
  on a gaming PC). Views: positions & exposure vs target, today's decision +
  reasons, equity vs benchmarks, drawdown, journal browser, health/drift
  panel, alert log, pause/flatten (typed confirmation). Hosts the Telegram
  poller (§5). Bot never blocks on the UI being down.
- **Ops:** user-level Task Scheduler folder "CryptoBot": RunCycle (daily),
  WebUI (at-logon), JournalBackup (nightly, non-overlapping), LocalWatchdog
  (in-session paging only — the external dead-man's switch is the real
  silence detector). Services/NSSM rejected (SYSTEM can't read per-user
  DPAPI secrets). All logging to UTF-8 files (pythonw has no stdout). B4
  exit criterion: `status` + `test-telegram` pass **from the scheduled
  context**.
- **GPU/local-AI rule (updated 2026-07-15):** the local AI never *starts on
  its own* — it runs only while Ian's manual switch is on
  (`cryptoacademy ai on [--hours N]` / `ai off` / `ai status`, flag file
  `data/local_ai.on`; the future bot UI gets the same toggle). The bot's
  *decision path* remains GPU-free by construction: inference is LightGBM on
  CPU, torch is not installed in the bot venv (`test_no_gpu.py` asserts
  `find_spec("torch") is None` and that no *decision-path* import reaches
  `cryptoacademy.models.dl`/`chronos_bench`), and every Ollama call goes
  through `ensure_local_ai_allowed` — which honors the switch and fails
  closed. The bot never creates the flag file itself; only Ian's explicit
  action does. So a running game can never be interrupted, and turning the
  switch off mid-batch stops AI work at the next gate check.
- **Secrets:** Windows Credential Manager via keyring (Telegram token +
  allowlisted user ID, heartbeat ping URL, restic password — escrowed per
  §2.4). `.env` = non-secrets only (including explicit proxy). gitleaks
  pre-commit + CI incl. wheel contents. Git Credential Manager +
  fine-grained PAT (retire PAT-in-URL pushes in the new repo).
- **Backups:** journal never in git. Nightly restic (7z-AES fallback) to
  cloud/second disk, client-side encrypted, per-machine host tags,
  keep-daily 30 / keep-monthly 12; snapshot via DuckDB export, not raw copy;
  failed export pages; quarterly restore drill per §6.
- **GitHub:** private, 2FA/passkey, thin branch protection (no force-push,
  CI required), Dependabot security-only (version bumps grouped, quarterly).

## 8. Paper-trading acceptance (pre-registered BEFORE the clock starts)

Registered in the bot registry as its own entry, thresholds and formulas
included, **before B6 day 1**. Honest framing: 6–18 months cannot prove a
small edge (MinTRL for SR 1.0 ≈ 2.5–3 years). The paper phase certifies
**(a) plumbing, (b) consistency with a matched simulation, (c)
non-inferiority to benchmarks** — it is **not evidence of skill**, and the
B7 report template prints this sentence next to the verdict, together with
the pre-computed null false-pass rate (below).

- **Evaluation date is FIXED at registration (reviews F1/F4):** computed
  from the champion's B2 post-buffer expected round-trip rate as
  `max(6 months, expected time to 30 round trips)`, capped at 18 months,
  written into the registry entry as a calendar date. Gates are computed
  once, on that date, on the full window. No early stop for success, no
  extension for a cleaner tail. (60 RTs was arithmetically unreachable for
  the favored strategies; 30 is the pre-registered floor, and the verdict
  vocabulary below handles falling short.)
- **Three verdicts, not two (review F3):** **PASS** (G-battery below),
  **FAIL/STOP** (kill switch fired; net Sharpe < 0 over the full window;
  costs > 50% of gross P&L), and **INCONCLUSIVE** (fewer than 30 round trips
  or < 90 exposed days at the evaluation date — e.g., the bot was correctly
  flat through a bear). INCONCLUSIVE is reported as "rails and gate behavior
  certified; entry quality untested"; a flat-in-bear window explicitly
  counts as evidence *for* rail correctness (no false entries below the
  SMA), nothing more. Extension beyond the registered date only via the cap
  rule above.
- **Benchmarks — computed as shadow strategies inside the same engine**
  (review F8): `is_shadow` journal rows, §4's exact sizing code with
  signal ≡ 1, frozen and hash-registered at B6 day 1, accruing daily. They
  cannot be recomputed differently later. Set: cash; buy-and-hold BTC;
  **vol-targeted 50/50 at the same 12% target, same σ estimator, same
  floors/buffers/caps/fill model — the primary skill benchmark.**
- **Gates:**
  - **G1 — Operations (hard):** pre-registered incident taxonomy and
    handled/unhandled rubric written before B6; incidents classified at
    occurrence time in the journal, immutably (review F4). Budgeted
    allowances: `missed_cycle` ≤2/month, none >48h, all with clean
    catch-up. Zero unhandled incidents over the **whole window** (not a
    trailing sub-window).
  - **G2 — Tracking (hard, the test 6 months CAN do — reviews F3/F6):**
    run the frozen engine + champion over the same paper window as a
    simulation on recorded inputs; paper equity must track the simulation
    within pre-registered bounds (daily tracking error and cumulative
    divergence limits). This certifies "the deployed thing is the
    registered thing" with high power.
  - **G3 — Non-inferiority (reported with CI, decision-informing):** net
    Sharpe vs the vol-targeted 50/50 shadow benchmark, with Lo (2002) SE at
    the actual window length, one-sided lower bound stated; max DD ratio
    reported. At this sample size this is low-powered — it informs Ian's B7
    judgment; it is not decidable-by-noise theater.
  - **G4 — Direction (reported):** α point estimate vs the shadow benchmark
    (sign + CI). A coin flip under the null and labeled as such.
  - **Null calibration (review F7):** before B6 day 1, run a no-skill null
    simulation (permuted signal timing / bootstrapped benchmark returns)
    and publish the family-wise false-pass probability of the full battery
    in the registry entry, printed in the B7 report next to the verdict.
- **Metrics reported** (all net, all pre-specified): total return, realized
  vol vs target, Sharpe, Sortino, max DD, hit rate (pooled across assets,
  exact binomial CI), profit factor, turnover + cost share of gross P&L,
  time in market, up/down capture, regime-conditional table using the
  *mechanical* BTC-vs-200d-SMA rule (never the bot's own gate parameters as
  grader), execution-time drift distribution, PSR vs 0 on the paper window,
  DSR with union-N for any joint backtest+paper claim. Timing regressions
  (Treynor–Mazuy etc.) are **cut from v1 gates** — no power at this sample —
  and appear only as raw numbers in the B7 appendix.
- **Discretion handling (review F9):** every manual intervention is an
  `intervention_event`; the engine keeps simulating the untouched strategy
  in shadow; **gates grade the no-discretion shadow curve**, and any
  material as-traded vs shadow gap is itself reported. Mechanical rails are
  part of the strategy and grade normally.
- **Beyond paper (out of v1 scope):** would require PASS → Ian's explicit
  decision → ≥3 months at ≤5–10% of intended capital, identical gates +
  execution tracking error <10 bp/trade vs paper. Any decision-path change
  resets the clock and registers as a new trial.

**Owner effort (review F9-coherence):** the standing ritual set is
deliberately minimal — read (or ignore) the daily digest; respond to pages;
**one ~30–60 min monthly health review in the UI** (drift panel,
reconciliation, equity vs benchmarks); quarterly: restore drill + grouped
dependency bumps + structural evaluation *only if* hypotheses actually
accumulated. ≈3–4 h/month. Weekly reviews, LLM sessions, refit rituals: cut.

## 9. Execution phases

- **B0 — Lab prerequisites (CryptoAcademy):** `CRYPTOACADEMY_HOME` override;
  `train` extra + import guards; **input-schema contract module**; tag +
  wheel from git archive. *Exit: wheel installs in a fresh venv; importing
  features/validation pulls no torch; contract validates lab-built frames.*
- **B1 — Clean repo skeleton (C:\CryptoBot):** repo + CI (incl. wheel-scan)
  + pre-commit + bootstrap.ps1 (with escrow gate) + settings/keyring +
  journal schema & migrations + core tests (no-GPU incl. Ollama-module
  assertion, append-only, PIT, allowlist, weekend staleness, two-writers).
  *Exit: bootstrap end-to-end on this PC; CI green.*
- **B2 — Strategy research (in the lab):** implement S1–S3 as pure
  functions; **freeze and register the combination rule and the champion
  selection rule FIRST**; register ≈8–12 identities; evaluate once, purged
  CV, net of §5 costs, history ≤ 2026-07-11; report round trips/yr net of
  buffers per config (these numbers set the §8 evaluation date); DSR/PSR
  with union-N in the freeze note; champion frozen; `strategy.yaml` + model
  card written; **§2.5 promotion check passes (fails closed)**. 24h
  cost-survival question answered (default: no). *Exit: champion registered,
  frozen, honestly written up — nulls included.*
- **B3 — Engine:** run-cycle (fetch→validate→decide→simulate→journal, one
  transaction), rails, PaperBroker, reconciliation. **Dry cycles use
  pre-cutoff days ONLY** (review F5 — engineers must not see lockbox-era
  signals before the clock starts). *Exit: kill-mid-cycle tamper test
  passes; golden-day test passes; all rails demonstrably fire in tests;
  dry-cycle reproduction on pre-cutoff days.*
- **B4 — UI + ops:** NiceGUI (hardened), Telegram (allowlisted), external
  dead-man's switch, scheduled tasks, backups. **At B4 exit:
  `strategy.yaml` + model files + cost model are hash-frozen; the hash goes
  into the paper-period registry entry; from here on only a pre-registered
  whitelist of plumbing changes (scheduling, logging, alert routing, UI —
  nothing reachable from the decision path) is allowed, enforced by the
  hash; any decision-path change registers as a new trial and resets the
  B6 clock** (review F5). *Exit: smoke tests from the scheduled context;
  Ian operates the bot for a day without touching code.*
- **B5 — Burn-in (≈1 month):** live-paper at size ×0. Scope limited to
  **plumbing** (the whitelist); performance-shaped observations may generate
  journaled hypotheses but no changes. *Exit: 2 consecutive clean weeks.*
- **B6 — Paper phase:** §8 registered (evaluation date, gates, formulas,
  null false-pass rate, benchmark hashes) → hands off. Champion frozen
  throughout; quarterly structural evaluations may *register* future
  challengers but nothing touches the running config.
- **B7 — Review & decision:** report against §8 on the registered date, with
  the three-verdict vocabulary and the null-calibration number printed next
  to the outcome. Pass → Ian decides next step; fail/inconclusive →
  published post-mortem; everything further goes through the registry.
  (Capstone semi-automation resumes only after this.)

**Sequencing:** B1 ∥ B2; B3 needs both; B5's clock starts only when B4's
freeze is in place — rushing to paper with flaky plumbing wastes the
pristine window.

## 10. Deferred / out of scope for v1

24h horizon (registered-trial re-entry only), S4 funding overlay, S5
meta-labeling (requires §2.5-compliant retrain as a new trial), challenger
machinery (schema-ready, built when first needed), monthly refits,
LLM roles in the decision path (journal LLM roles are switch-gated per §6),
TCA reporting (columns kept), timing-regression gates,
stocks/multi-market (architecture stays asset-agnostic; revisit after B7),
live money (separate future decision), futures/shorting/leverage, intraday,
news features in production, auto-retraining of any kind, capstone Phase 6
(paused), any UI exposure beyond localhost.

## 11. Adversarial review changelog (draft v1.0 → final v1.1)

Three independent reviewers (statistics, security/ops, economics/coherence)
produced 14 + 15 + 14 findings; the confirmed ones changed the plan as
follows. Full reports are preserved in the session transcript.

**Cut for v1** (coherence review): 24h horizon (fatal by own cost math; also
deletes the unsolved two-horizon netting problem); S5 meta-labeling
(verified news-contaminated at `meta.py:84` — unpromotable under §2.5); S4
(unvalidatable within the window); challenger machinery (no champion to
challenge yet); monthly refits (portability break + G2 confounder +
unattended-swap risk + labor); scheduled LLM roles; TCA reporting; timing
regressions as gates. Owner ritual set reduced to ~3–4 h/month.

**Statistical repairs** (stats review): combination rule frozen ex ante and
registered (was an unregistered post-hoc optimizer); fixed evaluation date
from champion turnover (60-RT floor was unreachable — replaced by 30-RT
floor + INCONCLUSIVE verdict); G2 redefined as high-powered
paper-vs-simulation tracking (was a vacuous-or-impossible Sharpe band); G1
incidents pre-taxonomized and classified at occurrence, whole-window (was
self-graded optional stopping); benchmarks run as hash-frozen shadow
strategies (were re-computable dials); gates grade the no-discretion shadow
curve; null false-pass rate of the battery computed and published; DSR N =
union of lab + bot registries; hypothesis validation excludes its generating
window; B3 dry-runs restricted to pre-cutoff days + B4 hash-freeze +
plumbing whitelist (lockbox was protected against algorithms but not against
engineers watching the burn-in); the wrong "365 trades/yr" arithmetic
corrected throughout.

**Operational repairs** (security review): external dead-man's switch (local
watchdog dies with the machine it watches); Telegram inbound commands
allowlisted by user ID + named poller + cycle-start drain (were
globally-addressable unauthenticated controls); restic password escrow +
non-source restore drills (key previously lived only on the machine the
backup must survive); per-feed publication-calendar staleness clocks (naive
24h rule would NO-OP every weekend or get loosened into uselessness); single
sequential run-cycle task (fetch/decide race guaranteed wake-day NO-OPs);
transactional cycles with `cycle_id` + kill-mid-cycle test (crash recovery
was unspecified against an append-only schema); instance GUID + take-over
handshake (two-PC double-journaling); input-schema contract + golden-day CI
test (silent drift between bot fetchers, lab collectors, and the frozen
wheel); UI session token + Origin allowlist (loopback is not a boundary);
two-writer policy with disjoint tables/schedules; clock-drift check; missed-
cycle budget inside G1; wheel built from git archive + wheel-content
scanning; explicit proxy config + scheduled-context smoke tests; restore
`--target` guard.

**v1.1 → v1.2 (Ian's correction, 2026-07-15):** the local-AI policy is a
manual on/off switch, not a prohibition. The old pain was the AI *starting by
itself* and killing game performance; the fix is that it runs only while
Ian's switch (`cryptoacademy ai on/off`, flag `data/local_ai.on`, optional
auto-off hours) is enabled — implemented in `localai.py` + CLI, CI-guaranteed
by the updated `test_localai_gate.py`, and the NewsScoring scheduled task is
re-enabled (it no-ops while the switch is off). Plan deltas: §2.5's news
exclusion re-justified on portability + decision-independence grounds (not on
a "never" rule); §6 LLM journal roles switch-gated instead of cut; §7 GPU
rule reworded (decision path stays CPU/torch-free; Ollama calls gated by the
switch).
