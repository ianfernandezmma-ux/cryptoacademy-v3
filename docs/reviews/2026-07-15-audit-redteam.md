# Audit round (pre-B3) — Project red-team report

Agent: project-level red team (strategy, operations, owner-fit). Date:
2026-07-15. No market-data evaluation.

## F1 [CRITICAL] — B6 verdict INCONCLUSIVE by construction
§8's rule (max(6mo, time-to-30-RT) capped 18mo) vs champion 10.9 RT/yr →
~16 RTs expected at the capped date; <90-exposed-days trigger also live
(2026H1 = zero). 18 months of solo discipline toward a pre-determined
"entry quality untested". Certifiable within the window: G1 ops + G2
tracking (accrue daily). Fix — legitimate ONLY before B6 registration:
1. Split the verdict: PASS-OPS = G1+G2 hard gates; performance (G3/G4, RTs,
   hit rate) becomes a reported appendix with CIs, never a gate.
2. Pre-registered month-6 interim checkpoint grading G1+G2 only
   (deterministic, performance-blind).
3. Shadow set from day 1: all 6 non-champion B2 identities + benchmarks as
   is_shadow strategies, hash-frozen at B4; family-pooled diagnostics with
   cluster-aware CIs; pre-commit NO mid-window champion switch. **This makes
   B3 a multi-config engine — decide before B3, cheap now, clock-reset
   later.**

## F2 [MAJOR] — Pristine window consumed by calendar
Several load-bearing registrations still open (G2 formula, schema-contract
pin) while B3–B5 take months. Commit B3 and B6 target start dates in
writing; restate "no peeking at post-cutoff champion performance".

## Section 2 — The effort/return equation
5.9% = the real risk-adjusted product expressed at a timid scale plus a
0%-cash assumption. Paths: (a) continue as-is → operator pre-disappointed,
most likely failure is quiet death at month 9; **(b) RECOMMENDED: one
bounded registered round (B2.1) on scale + accounting** (cash-yield
convention; frozen champion re-evaluated at VT 15% and 18% — two identities,
one run, rails re-derived; days of work, directly answers the objection);
(c) scope expansion (assets/futures) → natural post-B7 v2, doing it now
makes the project unfinishable.

## F3 [MAJOR] — Trial registry un-backed-up
data/trials/trials.jsonl (DSR denominator for every claim, not
re-downloadable) lived gitignored on one disk. **STATUS: FIXED same day —
committed to the lab repo (b8bb3fd).**

## F4 [MAJOR] — Vacation reality vs G1 missed-cycle budget
A planned 2-week absence = ~14 missed cycles >48h → blows the gate or bends
the taxonomy. Add a planned-outage category (declared in advance in the
journal; pre-registered position policy, e.g., flatten-before-absence >72h
as a mechanical rail; G2 reconstruction rule for gaps — champion inputs are
re-downloadable so the shadow curve is reconstructible). Or remove the
cause (F5).

## F5 [MAJOR] — The gaming PC is the wrong host
The two-repo/wheel/bootstrap design already makes the bot turnkey for a
~€150 always-on mini-PC: eliminates vacation/reboot/hibernate misses, the
shared-IP stagger, GPU-household coupling, and the electricity absurdity
(gaming rig 24/7 ≈ €100–200/yr > expected paper-notional profit; mini-PC
~10W). Instance-GUID/take-over machinery exists. Decide before B4 registers
tasks. Noted NOT a hole: the bot's decision path does not depend on lab
collectors (klines-only staleness is correct).

## F6 [MINOR] — Record locality
Copy frozen protocol docs into C:\CryptoBot\docs at B4 freeze; encode tag in
wheel filename/version at each promotion; mark README B4-isms; add heartbeat
provider email as secondary alert channel.

## F7 [MAJOR] — Stopping rule for improvement rounds (adopt verbatim)
1. Exactly ONE amendment round ("B2.1") before B3, pre-registered on one
   page within 14 days, scope closed to: vol-target scaling (≤2 pre-stated
   levels), cash-yield accounting convention, and the B6/§8 amendments (F1,
   F4). No new families, no parameter re-search, no re-ranking of the 7.
2. B3 start date committed in writing at B2.1 close; slips only for
   confirmed defects.
3. Thereafter improvement ideas → hypothesis table → the existing quarterly
   channel. Only triggers for another pre-B6 round: confirmed protocol
   violation or reproducible code defect. "Results feel low" is a
   non-trigger — used once, spent.
4. One adversarial batch per phase; findings fixed or rejected in writing;
   a second batch requires the first to have produced a CRITICAL.

## F8 [MAJOR] — Operator boredom is the top-line risk
Realistic B6: "no position, no action" digests for 300+ days/yr, 18 months,
solo. Mitigations: F1's month-6 milestone + decidable verdict; the shadow
set (digest shows a living family + benchmarks); calendarized rituals;
pre-write the month-9 sentence: "flat is the design working — the 2022
column is why."

## F9 [MAJOR] — Review record lived in session transcripts
Export all adversarial reviews to docs/reviews/ (this file series is that
fix). Any future review that changes the plan gets a file, not a chat log.

## F10 [MAJOR] — No document states the intended capital
Paper starting equity + eventual live band are nowhere. Blocks: evaluating
"5.9% is too low", min-notional/lot-size fidelity at small equity (must be
registered before B6), the host/electricity arithmetic, and the whole
Section-2 debate. One paragraph from Ian fixes it; write before B2.1.

## F11 [MINOR] — Out-of-scope-but-note
Spain taxes IF ever live (savings income 19–28%, FIFO, Modelo 721 >€50k on
foreign exchanges; 10.9 RT/yr has no deferral benefit — name it in the B7
beyond-paper checklist). Binance access/geo-shifts under MiCA and Vision
availability: runbook contingency line — "market data unreachable >72h →
blind-flatten rail; fallback data source is a REGISTERED change, not an
emergency hack." Monitoring costs trivial; host electricity is the real
number (F5).

## Priority order before resuming B3
1. Registry backup (DONE). 2. Ian writes the capital band. 3. The single
B2.1 amendment round under the F7 rule (VT scaling ≤2 levels + cash-yield
convention + B6 amendments: PASS-OPS split, month-6 checkpoint, shadow set,
outage taxonomy, G2 reconstruction rule) with B3 start date committed at
close. 4. Decide the host (mini-PC recommended) before B4. 5. Reviews
exported (THIS) + protocol docs into the bot repo at B4 freeze. 6. Adopt
the stopping rule in writing (plan v1.3 changelog).

Then build B3 — as a multi-config engine (champion + hash-frozen shadows),
the only item that changes what B3 is.
