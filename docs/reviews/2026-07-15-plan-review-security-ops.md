# Plan v1.0 adversarial review — Security / operations lens

Agent: security & operational-robustness reviewer of draft plan-bot-v1.md.
Date: 2026-07-15. All confirmed findings integrated into plan v1.1 (§11).
Condensed export of the full finding list.

## CRITICAL
**C1** Watchdog lives inside the machine it monitors — machine-off/
hibernate/update-reboot silences watchdog and bot together. Fix: external
dead-man's switch (healthchecks.io-class); local watchdog for fast
in-session paging only. → Adopted.

**C2** Telegram inbound commands unauthenticated (bots globally addressable
— anyone finding the username could /flatten) and no named poller process
(commands silently swallowed while UI down). Fix: allowlist by Telegram user
ID, drop+log others; typed confirmation for /resume /flatten; poller in the
always-on UI process AND run-cycle drains pending updates at cycle start;
test non-allowlisted rejection. → Adopted.

**C3** Backup encryption key stored only on the machine being backed up
(DPAPI is per-user-per-machine): every disaster the backup exists for
destroys the key; the new-PC restore story unexecutable. Fix: forced
out-of-band escrow at bootstrap (refuse to proceed without acknowledgment);
restore drills on a non-source machine with only the escrowed password.
→ Adopted.

## MAJOR
**M1** Naive 24h staleness rail vs real publication calendars → bot NO-OPs
every weekend (FRED/COT/ETF legitimately >24h stale) or rail gets loosened
into uselessness; Binance Vision publishes too late for the live edge. Fix:
per-feed max_age against expected publication clocks (lab's DST-aware logic
ships in the wheel); REST for live edge, Vision backfill-only; simulated-
Saturday CI test. → Adopted.

**M2** FetchData/Decide as separate catch-up tasks race on wake-after-absence
days → guaranteed NO-OP exactly when the position most needs re-evaluation.
Fix: one sequential run-cycle task; gap-resume event + page. → Adopted.

**M3** Decide cycle not transactional/idempotent: crash between decision and
order writes → rerun appends duplicate decisions or reconciliation halts.
Fix: cycle_id (UTC date × config_hash), one transaction ending with
cycle_complete, first action "if complete → exit 0"; kill-mid-cycle tamper
test as B3 exit criterion. → Adopted.

**M4** Dual-machine story allows two live bots double-journaling into one
restic repo → ledger unreconstructable. Fix: instance GUID on every event;
refuse-run on writer mismatch without --take-over handshake (journaled);
decommission-old-machine as runbook step 1; per-machine restic host tags.
→ Adopted.

**M5** Frozen wheel + bot fetch.py + evolving lab collectors = three
implementations of one data contract drifting silently → plausible-but-wrong
features with all health checks green. Fix: wheel exports an input-schema
contract validated at runtime (violation → NO-OP + page); golden-day
regression test in CI; model card pins contract version. → Adopted.

**M6** NiceGUI on localhost with no auth is not a boundary: DNS-rebinding
from malicious websites and other local processes on a gaming PC can hit
127.0.0.1 endpoints. Fix: per-boot session token in URL, strict Host/Origin
allowlist, storage_secret, state-changing actions authenticated. → Adopted.

**M7** Monthly mechanical refit = unattended model swap with no output gate
(corrupt cache → degenerate booster silently replaces champion). →
Superseded: refits cut from v1 entirely (coherence review); two-phase gate
design preserved for any future refit.

**M8** Machine-off periods = unmanaged risk, and G1 doesn't count them; a
19:30 catch-up decision fills 11h from the fill model's assumption. Fix:
missed_cycle events; missed-cycle budget inside G1 (≤2/mo, none >48h);
scheduled-vs-actual time recorded per decision; drift distribution reported.
→ Adopted.

**M9** "Single writer" contradicted by the plan's own process list (Decide,
health metrics, trade_outcome rebuild, backup EXPORT, Telegram poller, LLM
tagging — all writers on one DuckDB). Fix: two writers with disjoint
tables/schedules + retry policy + concurrency test. → Adopted in v1.1;
**NOTE: the B3-code audit (2026-07-15) demonstrated even two processes are
impossible on DuckDB (per-file lock) — superseded by the single-writer
redesign in the pre-B3 fix batch.**

## MINOR
m1 scheduled-context assumptions (keyring/proxy/pythonw stdout): explicit
proxy in .env, UTF-8 file logging, B4 exit = smoke tests from the scheduled
context. m2 lab DailyUpdate vs bot fetch on one IP/proxy: stagger ≥1h +
jittered backoff. m3 committed wheel bypasses gitleaks: build from git
archive; CI unzips + scans + manifest allowlist. m4 clock integrity: compare
vs Binance server time each cycle, >60s drift → NO-OP; journal drift.
m5 forward-only-archive sync is a fork, not an option: v1 features
exclusively re-downloadable, promotion check fails closed. m6 restore can
clobber the live journal: --target required, refuses live path, drill =
restore to temp + compare. GPU rule: no violation found; harden test to
assert no import path reaches news.scoring/news.regime.

**Verdict:** "Not operationally ready as drafted — the gaps cluster around
everything that happens when nobody is watching." All fixes adopted as plan
amendments before B3/B4.
