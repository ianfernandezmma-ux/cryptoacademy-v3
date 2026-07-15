# B2 pre-run adversarial review — lookahead / off-by-one audit

Agent: lookahead hunter over cryptobot.engine.strategies/sizing, the
strategy tests, scripts/b2_evaluate.py, and the frozen pre-registration.
Date: 2026-07-15, BEFORE the one-shot run (per protocol §7.5). The reviewer
also verified the actual kline parquets (sort order, duplicates, day
completeness incl. the 15 partial-outage days — every one retains the 23:00
bar so last() = true daily close) and the stats/registry call signatures.

**Bottom line: no BLOCKER; the core timing chain is clean.** Verified clean:
signal timing (scalar[t] from closes[0..t] only); return alignment
port[t] = held[t-1]·r[t] − cost[t-1]; vol sizing PIT; expanding high-vol
quantile PIT; score_mask slicing consistency (net = gross − costs day-by-
day); Donchian windows closes[t-N:t] exactly as pre-registered, both entry
and exit, gate-red semantics correct; warmups; protocol constants (fees,
slippage doubling, DRAG/MAXDD limits, √365, registration-before-evaluation,
one-shot refusal guard); DSR/PSR signatures and n_trials distinct-hash
semantics (a --force-defect re-run of identical configs does NOT inflate N);
PBO matrix alignment.

**[MAJOR-1] Daily close depended on parquet row order**: group_by().last()
takes the last row in FILE order; sorted today, but DailyUpdate appends and
future re-ingestion could interleave — a mid-day price would silently become
the daily close. Fix: .sort("open_time") + assert first day == 2020-01-01
(pins the frozen expanding-hv origin). **APPLIED before the run.**

**[MAJOR-2] No engine-alignment test**: same-bar execution (held[t]·r[t]) in
run_config would pass every strategy-level prefix-invariance test. Fix: a
perfect-placement test (position taken AT the close of the big day earns
nothing; taken the day before earns exactly w·r; costs land next day).
**APPLIED before the run (tests/test_b2_engine.py, 3 tests).**

**[MINOR]** BH_5050 rebalance cost charged same-day + spurious entry-day
rebalance (bp noise, diagnostic benchmark only — footnoted in results).
BH benchmarks omit high-vol slippage doubling (few bp, footnoted).
Round-trip counter: counts on post-buffer held (defensible; stated in
results), open-at-end counts as completed, final index unexamined, hit rate
gross-of-cost — all diagnostics, none feed selection. Tie-break "fewer
parameters" implemented as config-JSON length proxy (unused; DSR had no
ties). RESULTS_MD constant unused (results doc written by hand — done).
Buffer dust <1% can survive a red gate at the held-weight level
(spec-conformant with the frozen §3 formula; scalar-level flat holds).
hv percentile computed on the floored vol series (consistent both sides).

**Accepted-by-design notes:** COMBO inclusion from full-window realized cost
drag (turnover quantity, frozen); last-day trade cost falls outside the
window with its return; ewma_std is adjust=False biased EWM variance
(internally consistent; docstring is the frozen definition).

**Test-gap notes for later:** Donchian boundary pin (added same day),
highvol_flags/load_daily/bh_benchmarks untested, S3 warmup edge, buffer
dust-exit, ewma vs pandas reference.

**Verdict:** "No lookahead, no returns-misalignment, no cost-timing error;
data verified compatible. Apply the two MAJOR guards before the one-shot —
defect prevention, not protocol changes; neither alters any number."
Both applied; suite green; the one-shot then ran once.
