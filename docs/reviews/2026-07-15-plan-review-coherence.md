# Plan v1.0 adversarial review — Economics / coherence / owner-fit lens

Agent: coherence reviewer of draft plan-bot-v1.md. Date: 2026-07-15.
All confirmed findings integrated into plan v1.1 (§11). Condensed export.

**F1 [CRITICAL]** 24h horizon dead by the plan's own cost arithmetic
(0.30–0.40% RT × implied frequency > any honest edge; meta-labeling already
REJECTED at 24h) yet carried through vision/schema/metrics. Fix: v1 = 96h
only; 24h re-enters only via a registered trial beating the cost model;
deletes the two-horizon netting problem. → Adopted.

**F2 [CRITICAL]** ≥60-round-trip precondition unreachable under the plan's
own frequency table (gated S2 ≈ 8–20 RT/6mo across both assets; BTC/ETH
~0.8-correlated so two assets don't double independent episodes); "round
trip" undefined for banded rebalancing. Fix: flat-to-flat definition,
rebalances excluded; precondition from the champion's registered rate;
design the verdict for realistic counts. → Adopted (30-RT floor +
INCONCLUSIVE).

**F3 [CRITICAL]** No verdict branch for "the bot was (correctly) flat":
long-only + regime gate in a bear = zero entries; ≥120-exposed-days can fail
in a mixed regime; inconclusive window silently becomes fail-or-judgment.
Fix: pre-registered INCONCLUSIVE-EXTEND branch, capped; flat-in-bear counts
as rail-correctness evidence only. → Adopted.

**F4 [CRITICAL — verified in code]** S5 meta-model is news-contaminated:
`models/meta.py:84` includes the "news" block (news_/gdelt_/evt_/era_llm/
low_news_flag) banned by §2.5; the +7.8pp artifact cannot ship. Fix: cut S5
from v1; a §2.5-compliant retrain is a NEW registered trial; make the
promotion check mechanical (diff model-card features vs allowed blocks,
fail closed). → Adopted.

**F5 [MAJOR]** Monthly refit breaks the frozen-wheel portability story
(refit needs the lab's multi-year pipeline; a fresh PC can run but never
refresh the model), leaves the artifact path unspecified, and contradicts
iron rule 3 as written; G2 would compare a refit stream vs a static-model
backtest. Fix: freeze the champion for the whole paper window — no refits.
→ Adopted.

**F6 [MAJOR]** G2/G3 have ~zero power at 6 months (SE(ann SR) ≈ 1.4;
differential vs a correlated benchmark ≈ coin flip). Fix: hard gates = G1
(ops) + paper-vs-simulation tracking error (the test 6 months CAN do);
G3/G4 demoted to reported estimates with CIs; one pre-registered G2 anchor.
→ Adopted.

**F7 [MAJOR]** Two horizons on one asset had no netting/book model (moot
after F1). → Adopted via F1.

**F8 [MAJOR]** Local watchdog can't detect the dominant silence scenario
(machine off) → external dead-man's switch; missed-cycle taxonomy with
budget. → Adopted (matches security review C1/M8).

**F9 [MAJOR]** Owner effort ~10–15 h/month contradicts the hands-off goal;
ritual decay kills the memory pillar by month 4. Fix: minimum viable ritual
set ≈ 3–4 h/month (daily digest optional; alert-driven triage; monthly 30–60
min health review; quarterly drill + deps + evaluation only if hypotheses
accumulated); refits/challengers/LLM sessions cut. → Adopted.

**F10 [MINOR]** S3's 30–60 trades/yr predates the buffers; report
frequencies net of buffers in B2 (those numbers feed the sample math).
→ Adopted.

**F11 [MINOR]** Expectation numbers disagreed across sections (0.7–1.2 vs
0.2–0.5): one number per champion in the registry. → Adopted (0.2–0.5).

**F12 [MINOR]** "Daily" undefined (CET/CEST vs UTC; DST; lab task ordering).
Fix: everything UTC; cycle targets 07:00 UTC; stagger with lab tasks.
→ Adopted.

**F13 [MINOR]** 50/50 risk split vs one-sided gating unspecified. Fix: keep
50/50, accept under-deployment (conservative reading). → Adopted.

**F14 [MINOR]** TCA decomposition on simulated fills measures the fill model
against itself: keep schema columns, cut reporting from v1. → Adopted.

**Leaner-v1 cut list (all adopted):** 24h horizon; S5 (news-contaminated);
S4 funding overlay (unvalidatable in-window); challenger machinery (no
champion track record yet; schema stays shadow-ready); monthly refits; LLM
journal roles as scheduled work (later re-scoped to switch-gated in v1.2);
TCA reporting; timing regressions as gates; restore drill monthly →
quarterly. Resulting v1: S1+S2 (S3 conditional) at 96h, frozen for the
window, fully railed, ~3–4 h/month, three-verdict acceptance.

**Verdict:** "Not executable as pre-registered [draft]; the discipline
scaffolding is genuinely excellent. Fix F1–F6 before B2 starts — they change
what gets registered." All fixed in v1.1 before B2 ran.
