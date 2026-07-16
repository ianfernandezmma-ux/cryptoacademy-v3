# Plan v2 — CryptoBot: Core + Evidence-Backed Sleeves

**Status: ACTIVE (2026-07-16). This is the ONLY plan to follow.** It
supersedes `docs/plan-bot-v1.md` and `docs/plan-v3.md` as the authoritative
execution plan. It does not rewrite them: plan-bot-v1 §§2–9 (architecture,
strategy layer, sizing, rails, journal, engine, paper acceptance, phases
B0–B7) remain **binding engineering law for Track 1** and are incorporated by
reference — read plan-bot-v1 before touching anything it specifies. What v2
adds is the layer above: a research-driven portfolio structure (core +
sleeves), two new pre-registerable research tracks born from the 2026-07-16
deep-research round, and the operations/control-center track.

**How to use this document (Claude, read this first after /clear):** this
file is the map. Section 1 tells you where the project stands; Section 4
tells you what may be worked on and in which track; Section 8 lists the
decisions reserved for Ian. Never start strategy work that is not a
registered trial. Never touch the frozen champion. When in doubt, the three
iron rules (Section 2) win over everything, including this plan.

---

## 1. Where the project stands (2026-07-16)

- **The capstone (CryptoAcademy v3 research program) is PAUSED** since
  2026-07-15, resumable after B7. Its results stand: phases 4.1–4.4 closed,
  best honest edge LightGBM MCC 0.065/0.093 (24h/96h), meta-labeling
  "suggestive, never established", audit 2026-07-11 applied (26 fixes),
  contaminated holdout 2026-01-01→07-11, **pristine lockbox 2026-07-12+**.
- **The bot (Track 1) is in B3** (engine build started 2026-07-16). B2/B2.1
  closed with production config **`S2_DONCH_N20_VT20_YIELD`** (hash
  44ac1075785c): Donchian-20 long-only BTC+ETH spot, 96h horizon, vol target
  0.20, DTB3 cash-yield accounting, 12.6%/yr backtest-implied, maxDD 10.5%,
  DSR 0.90 (PBO 0.52 caveat). Champion **frozen** through the whole paper
  window; shadow set = 6 non-champion B2 identities + benchmarks; paper
  equity 1,000 USDT registered. No mid-window champion switch, ever.
- **Deep research round closed 2026-07-16** — full cited report:
  `docs/research/bot-improvement-research-2026-07-16.md`. It reshapes the
  medium-term structure of the project (Sections 3–4) without touching
  Track 1.
- **Two repos**: `C:\CryptoAcademy` = dirty lab (research, data collection,
  this plan); `C:\CryptoBot` = clean hermetic bot repo (plan-bot-v1 §2).
- **Ops fixes in flight** (separate sessions, 2026-07-16): ETF-flows
  download 403 (farside.co.uk blocked) and a truncated open-interest parquet
  crashing `archive-oi`.

## 2. The three iron rules (unchanged, non-negotiable)

1. **PIT discipline.** No information enters a feature or decision before
   its knowledge timestamp; production decisions record and assert
   `features_max_knowledge_utc <= decided_at_utc`.
2. **Every evaluated configuration is registered BEFORE evaluation.**
   N for any DSR = union of lab registry
   (`C:\CryptoAcademy\data\trials\trials.jsonl`) and bot registry. Crashed
   trials count. This applies to every sleeve trial in Track 2.
3. **Memory informs; only the registry authorizes.** Nothing in production
   changes except through a registered, purged-CV-validated trial.

Plus the environment hard rule: **local AI runs only while Ian's switch is
on** (`cryptoacademy ai on/off`, flag `data/local_ai.on`; nothing may create
that file automatically).

## 3. Research foundation (what the 2026-07-16 deep research established)

Verified against primary sources (BIS WP 1087; CMU carry-trade paper; NBER
w24877/RFS; JFQA CTREND 2025). Full citations and caveats in the report.

- **A. Funding-rate carry** (long spot + short perp, delta-neutral) is the
  best-documented gross return source in crypto (~7%/yr avg 2019–2024,
  spikes >40%; 16–22%/yr gross in the CMU Binance sample). On Binance the
  funding rate is **known one period in advance** — a cleanly PIT signal.
  BUT: all headline numbers are gross-of-cost; entry/exit costs dominate at
  retail size; liquidation cascades are documented (10% carry rise → short
  liquidations ≈22% of OI within a month); the premium **compressed
  structurally post-ETF (Jan 2024)**. Realistic net expectation:
  low-to-mid single digits p.a., episodic. It is a *conditional harvest*,
  not a constant yield.
- **B. Trend/momentum is validated on two independent axes** — time-series
  (NBER/RFS) and cross-sectional (JFQA CTREND: 3,000+ coins, survives
  transaction costs, persists in big liquid coins). This **validates the
  existing champion class** and supports expanding to a long-only
  top-quantile momentum sleeve over top-N liquid Binance pairs. Transfer
  caveat: CTREND is long-short; the long-only retail version is OUR
  hypothesis to test, not the paper's result.
- **Refuted:** attention proxies (Google/Twitter) as return predictors — do
  not use.
- **Null result that matters:** NO claim about bot frameworks, practitioner
  communities, or YouTube channels survived verification. The ecosystem's
  profitability claims are unverifiable or affiliate-driven; scam anatomy is
  documented in the report (NASAA/CFTC). Consequence: we keep building on
  our own validated codebase; no framework migration; educational sources
  are leads only.

## 4. Target structure: one portfolio, three tracks

The end state this plan builds toward: a paper portfolio of **independent,
individually pre-registered sleeves** sharing the risk budget:

```
PORTFOLIO (paper, vol-targeted risk budget)
├── CORE  — S2_DONCH_N20_VT20_YIELD (frozen champion; Track 1, running)
├── SLEEVE-CARRY  — funding-rate carry BTC/ETH        (Track 2, C1: research)
└── SLEEVE-XSMOM  — long-only top-N cross-sectional momentum (Track 2, C2)
```

Sleeves reach production ONLY through the registered-challenger path
(plan-bot-v1 §6): earliest integration is a quarterly structural evaluation
as `is_shadow` challengers, and nothing touches the running config before
B7. If a sleeve requires futures (carry does), activating it is additionally
gated on Ian's explicit account decision (Section 8).

**Track 1 — BOT (build & paper-trade the core).** Exactly plan-bot-v1
B3→B7. Nothing in this plan modifies it: engine (B3, multi-config for the
shadow set), UI+ops (B4, hash-freeze), burn-in (B5), paper window (B6, gates
G1/G2 hard per v1.3 amendments), review (B7). Any decision-path change =
new trial + clock reset.

**Track 2 — SLEEVE RESEARCH (in the lab, parallel, GPU-free).**

- **C1 — Carry measurement (first, cheapest, no new infrastructure).**
  Question: what was the actual net-of-cost funding carry on Binance
  BTC/ETH at our size and fee tier, 2020→now, and how often does it clear a
  hurdle — with special weight on the post-2024-ETF regime?
  Method: pre-register the measurement spec BEFORE computing — fee model
  (spot + futures legs, entry AND exit, taker-first assumption, our actual
  tier), slippage assumption, holding/exit rule family, threshold grid as
  registered identities. Data: our own funding history (collected since
  2020) + 5-min derivatives metrics. Deliverable: a measurement report and
  a **go/no-go**: GO = a pre-stated fraction of rolling post-2024 windows
  clears the net hurdle → C1b designs the sleeve trial (entry threshold on
  next-period funding net of round-trip costs, margin-buffer rule sized
  against the BIS liquidation evidence, liquidation-stress test on
  historical funding spikes). NO-GO = published null; carry shelved with
  numbers, not vibes.
- **C2 — Cross-sectional momentum over top-N liquid alts.**
  Question: does a long-only top-quantile trend sleeve over the top-20/50
  liquid Binance USDT pairs beat the 2-asset core on risk-adjusted,
  net-of-cost terms? Method: (i) **PIT-safe universe construction first** —
  monthly top-N by rolling median dollar volume, built from Binance Vision
  archives, delisted pairs INCLUDED as of their time (survivorship is the
  known killer of this hypothesis class); (ii) data backfill for the
  universe (same pipeline, ~top-50 USDT pairs, 1h klines); (iii) register
  the signal family (Donchian/EWMAC ranks, top-quantile, vol-targeted, same
  §4/§5 sizing-and-cost machinery as the core) as identities; evaluate once
  under purged CV, history ≤ 2026-07-11 only (lockbox untouched); DSR with
  union-N. Benchmarks: the frozen core + vol-targeted 50/50.
- **C3 — Integration path.** Sleeves that pass C1b/C2 become registered
  shadow challengers at the first quarterly evaluation (they accrue paper
  track record without touching the core); combination weights across
  core+sleeves are frozen ex ante by a performance-blind rule (plan-bot-v1
  §3 combination discipline applies unchanged). Correlation between sleeves
  and core is measured in shadow BEFORE any capital-weight decision.

**Track 3 — OPS & CONTROL CENTER (visibility for Ian).**

- **Control center** (researched 2026-07-16, design approved direction):
  single-file FastAPI + HTMX dashboard in the lab venv, bound to
  `127.0.0.1`, showing: the 6 scheduled tasks (state, last result decoded,
  next run), run history (Windows event log, one-time elevated
  `wevtutil set-log Microsoft-Windows-TaskScheduler/Operational
  /enabled:true`), per-task log tails (`logs/*.log`), enable/disable/run-now
  buttons (via `schtasks`), and the AI switch — **always via the
  `cryptoacademy ai on|off` CLI, never writing the flag file directly**.
  Security floor: Host-header allowlist + secret token + state changes
  POST-only (localhost binding alone does not stop DNS-rebinding/CSRF).
  Durable audit: every CLI task run appends one JSON line to
  `data/runs.jsonl` (task, start, end, exit code, summary) — the event log
  is a ring buffer, our audit trail must not be.
- **Fix batch**: ETF-flows 403 + OI parquet (in flight); writer atomicity
  (temp+rename) everywhere a scheduled task writes parquet.
- The bot repo gets its own NiceGUI UI per plan-bot-v1 §7 — the lab control
  center and the bot UI are separate surfaces on purpose (dirty lab vs
  clean bot).

## 5. Sequencing and priorities

1. **B3 engine** (Track 1) is the critical path — the paper clock cannot
   start without it. Default allocation of effort goes here.
2. **C1 measurement** is the best effort-to-information ratio in the whole
   plan (a day of compute over data we already own) — run it early,
   parallel to B3, as lab work.
3. **Control center** next (Track 3) — small, self-contained, improves
   Ian's trust in everything else.
4. **C2** after C1's spec is frozen (it needs the universe backfill, a
   GPU-free but data-heavy job).
5. Quarterly evaluation (first one: earliest 3 months into B6) is where
   Track 2 results can first touch the bot, as shadow challengers.

## 6. Honest-expectations ledger (pre-committed numbers)

- Core: backtest-implied 12.6%/yr, maxDD 10.5%; honest net SR band 0.2–0.5;
  paper phase certifies plumbing + tracking, **not skill**.
- Carry sleeve: IF it passes C1, expect low-to-mid single digits net p.a.,
  episodic, with real liquidation-cascade tail risk to engineer against.
  Academic 16–22% gross is NOT the expectation.
- XS-momentum sleeve: unknown until C2; the long-short→long-only haircut is
  documented to be large; a null is a publishable outcome.
- Any result projecting net Sharpe > 2 anywhere is treated as a bug until
  proven otherwise.

## 7. What is explicitly out of scope (unchanged from v1 + additions)

Live money (separate future decision by Ian); shorting/leverage as
*directional* bets (the carry sleeve's short perp is a hedge leg, allowed
only through C1b's registered design); 24h horizon (default no); news/LLM
features in production; auto-retraining; attention-proxy signals (refuted
2026-07-16); framework migration (freqtrade/Nautilus/etc. — rejected by
research, custom thin engine stands); market making (no verified retail
evidence; revisit only with new evidence); UI exposure beyond localhost.

## 8. Decisions reserved for Ian

1. **Futures account for the carry sleeve** (paper first; only if C1 = GO).
2. **Approve each phase start** (B-phases and C-phases) — within a phase,
   Claude proceeds autonomously.
3. **Anything touching money, accounts, or external services.**
4. The AI switch, always.

## 9. Document map (read in this order after /clear)

1. `CLAUDE.md` — environment, iron rules, gotchas (TLS proxy, DuckDB locks,
   AI switch, torch/CUDA, push ritual).
2. **This file** — the plan.
3. `docs/plan-bot-v1.md` — binding engineering spec for Track 1 (B0–B7,
   §§2–9) and the adversarial-review changelog.
4. `docs/research/bot-improvement-research-2026-07-16.md` — the evidence
   base for Track 2, with citations and caveats.
5. `docs/reviews/2026-07-15-audit-synthesis.md` — pre-B3 fix batch.
6. `docs/audit-2026-07-11.md`, `docs/phase4-handoff.md`, `docs/plan-v3.md`
   — capstone context (paused, resumes after B7).

*Registered: this plan supersedes plan-bot-v1 as navigation; it amends no
frozen registration. Champion, gates, and the B6 evaluation date remain
exactly as registered in the bot registry.*
