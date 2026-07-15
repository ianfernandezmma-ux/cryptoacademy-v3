# Audit round (pre-B3) — Code auditor report

Agent: adversarial code audit of C:\CryptoBot (B0–B2 state) + lab b2_evaluate.
Date: 2026-07-15. Findings marked [demonstrated] were reproduced live.
Cross-checks that PASSED: strategy.yaml config_hash recomputes exactly;
strategy_card numbers match b2_results.json; restore from relocated snapshot
works; both suites green.

## CRITICAL

**C1. `Journal.sql()` "read-only" guard trivially bypassable [demonstrated].**
db.py sql() checked only the first token. Two working bypasses, both executed
and both deleted rows: `SELECT 1; DELETE FROM decision_event` (multi-statement)
and `WITH x AS (SELECT 1) DELETE FROM decision_event` (CTE-prefixed DML).
This is the exact query surface the B4 UI will expose.
Fix: `duckdb.extract_statements`; exactly one statement of type SELECT +
regression tests. **STATUS: FIXED same day (commit e43135e).**

**C2. The documented two-writer-process model is impossible on DuckDB
[demonstrated].** While one process holds a write connection, a second cannot
open the file even read-only (per-file lock, not per-table). During run-cycle
the UI cannot write review notes, status/backup fail; Journal.__init__ has no
connect retry. Fix (decide before B3): ONE writer process; all writes through
short-lived retried connections (tenacity already a dep); UI queues writes
through the engine path. Fix docstring; add two-process test. **STATUS: OPEN
— pre-B3 fix batch.**

## MAJOR

**M1. No cycle transaction exists despite the crash-safety docstring.** Every
insert autocommits; crash mid-cycle → partial rows without `completed` →
rerun re-inserts under fresh UUIDs → duplicates poison trade_outcome. Fix:
`cycle(cycle_id)` context manager (BEGIN → writes → completed → COMMIT,
rollback on exception) + kill-mid-cycle test. OPEN.

**M2. `cycle_id = date#config_hash` defeats idempotency on config change**:
config hotfix mid-day → new cycle_id → bot decides/trades twice in one UTC
day. Fix: gate on the date prefix; journal config changes as events. OPEN.

**M3. Foreign machines write before the instance guard fires [demonstrated]**:
_migrate() runs before _check_writer(); machine B without --take-over applied
a migration before being rejected. Failed opens leak the connection/lock.
Fix: guard first; close conn on raise. OPEN.

**M4. Positional `INSERT INTO t VALUES (…)` everywhere**: first
ALTER TABLE ADD COLUMN breaks or column-misaligns every write helper —
highest-probability future corruption vector. Fix: explicit column lists. OPEN.

**M5. `advance_hypothesis` can erase registry evidence [demonstrated]**:
backward transition to 'proposed' nulled trial_ids and verdict; nonexistent id
no-ops silently. Fix: forbid backward transitions; never null evidence; raise
on rowcount != 1. OPEN.

**M6. "Pinned dependencies" unenforced**: bare `uv sync` re-resolves and
rewrites uv.lock on drift. Fix: `uv sync --locked` in CI and bootstrap.
**STATUS: FIXED same day.**

**M7. Wheel provenance trust-based (no hash)**: tampered/dirty-tree rebuild
indistinguishable from ritual-built wheel; gitleaks can't see inside a zip.
Fix: SHA256 in VENDORED.md, asserted by check_wheel_manifest in CI.
**STATUS: FIXED same day (sha f41a39be…).**

**M8. B2 evaluated an unpinned working tree**: sys.path import of
C:\CryptoBot\src; registry rows record only the lab rev (a0d6135). Nothing
records which CryptoBot commit produced DSR 0.90. Fix: record both repos'
revs at B4 freeze; verify strategies.py/sizing.py unchanged since the B2-run
commit (b44e0f5); future evaluators capture the bot-repo rev + dirty flag in
registry notes. OPEN.

**M9. CI never runs on Windows** for a Windows-only bot (keyring, paths,
DuckDB locking differ). Fix: windows-latest matrix entry. OPEN.

**M10. Journal schema/API gaps B3 hits immediately**: no insert API for
position_snapshot / equity_snapshot / trade_outcome / model_health_event /
review_note / missed_cycle; trade_outcome "rebuilt at cycle end" contradicts
append-only (make it a VIEW or an exempted derived cache with a dedicated
rebuild); missed_cycle.actual_at_utc implies an UPDATE no API performs; no
canonical current-position/cash source (replay fills vs trust snapshot —
pick one). OPEN — this defines part of B3's design.

## MINOR (consolidated)

m1 take-over is non-atomic (two autocommits — wrap in one txn). m2
test_write_api_is_insert_only is name-theater (greps method names; test
behavior). m3 CLI logging contradicts docstring (no StreamHandler; pythonw
sys.stdout None risk; status/restore configure no logging). m4 bootstrap:
`uv python install` lacks --system-certs; no winget pre-check; nothing runs
`pre-commit install` (gitleaks hook dead on fresh machines). m5
setup_secrets: skipping all secrets still exits 0; --force restic regen
breaks backup continuity silently. m6 settings: UI_HOST dead knob in
.env.example; CRYPTOBOT_HOME relocates configs/models too (split HOME from
ROOT or document); instance_guid write racy. m7 inconsistent insert
validation (order/intervention enums, tz-awareness unchecked). m8 dangling
refs (backup.ps1, restore_drill codepath, README rename step for restored
journal). m9 strategy.yaml/card confusions for B4 freeze: fill_rule describes
the B3 model, not what produced backtest_expectation (close-to-close ± fixed
slippage) — B6 must not treat them as the same cost model; high_vol
percentile omits the 365d warmup note; horizon:96h labels a daily-cadence
strategy; sizing constants duplicated in yaml AND code with no consistency
test (add yaml==code test before the freeze). m10 backtest holds constant
WEIGHT between trades (costless implicit daily rebalance) vs a real broker
holding QUANTITY — decide and document before B6 registration. m11 s3 warmup
hardcodes 128; check_wheel "token" substring false-positive potential;
gitleaks-action needs GITLEAKS_LICENSE if repo ever moves to an org;
migration runner assumes no BEGIN/COMMIT inside scripts.

**Test-suite gaps**: C1 payloads (added), two-process locking, crash
mid-cycle, config-change same-day, foreign-machine migration, yaml↔code
constants, settings.py, restore/backup guards, check_wheel_manifest itself,
ewma vs pandas reference.

## Prioritized fix list

1. C1 (DONE) · 2. C2 before any B3 code · 3. M1+M2 (B3 crash story) ·
4. M4 now while the file is small · 5. M7 (DONE) + M6 (DONE) ·
6. M5+M3+m1 journal hardening · 7. M8 provenance at B4 freeze ·
8. M10+m9d before hash-freeze · 9. M9, m3, m4 · 10. minors during B3.

Strategy math (S1/S2/S3, sizing, buffer) and B2 evaluator timing/cost:
audited CLEAN. The rot is concentrated in the journal enforcement layer and
reproducibility plumbing — exactly where B3 builds.
