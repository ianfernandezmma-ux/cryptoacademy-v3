# CryptoAcademy Site — Plan v2 (research-backed)

> 2026-07-11. Supersedes §4–§9 of `PLAN.md` (v1 stays as the audit/history and
> data-contract reference; the contract in `contracts/site-data.md` remains
> valid). Produced from four parallel research agents (product framing, UX of
> probabilistic signals, 2026 static-site architecture, education content
> strategy) — findings credited inline. Ian's pivot stands: **a functional
> product for crypto beginners, not a research showcase.**

---

## 1. The frame (what we are building and why it wins)

**One sentence:** *Today's crypto market, explained in plain language — with an
honest signal that usually says "not today."*

Three research facts anchor the frame:

1. **The niche is empty.** Education libraries (Coinbase Learn, Binance
   Academy) refuse to say anything about *today*; analytics platforms
   (Glassnode, Santiment) speak only to professionals. The one product that
   owned the beginner middle — Milk Road, a plain-English daily brief — hit
   250k subscribers and an acquisition in 10 months. Nobody combines a daily
   plain-language read WITH a verifiable signal.
2. **Honesty is a moat, not a handicap.** The signal category baseline is
   fraud (~68% of free Telegram signal groups lose money; page-one Google is
   80–96% win-rate claims). Every scam-detection guide lists exactly what we
   have natively: timestamped calls published before the outcome, visible
   losses, no inflated win rates. Competitors cannot copy "NO-TRADE most days"
   without destroying their engagement-driven business model.
3. **NO-TRADE is protection, and beginners need protection.** ~84% of retail
   crypto traders lose money in year one, overtrading being the leading
   cause. A signal that clears only ~13% of days directly attacks the thing
   that kills its own audience. That is the story.

**Value hierarchy** (leads → supports): the **daily experience** (brief +
signal state, one artifact) → the **honesty/verification story** → **Learn**
as the retention and depth layer.

**Known objection to preempt** (HN-quant reflex: "anyone who could predict
wouldn't publish"): the site says plainly that the edge is small, this is a
public capstone, and the point is the *method*. Disarms skeptics, reassures
novices.

## 2. Information architecture

```
/            Today  — THE product: signal verdict cards + today's brief
             highlights + "today's numbers explained" panel. Home and
             "Today's signal" merge into one page with two depths.
/brief       Archive + /brief/YYYY-MM-DD permalinks (ES/EN).
/signals     Track record — every published call, outcomes stamped,
             misses included, two-commit git proof per row.
/learn       3 tracks + glossary + progress (localStorage).
/trust       "How it works" as a VERIFICATION TOOL, not an essay:
             git-timestamp proof, real metrics with one-line explanations,
             "why small honest numbers beat big fake ones", changelog.
```

## 3. The signal card v2 (the core component)

Ordered anatomy (UX research blueprint — gate first, frequency framing,
uncertainty always visible):

1. **Gate verdict first** (mono micro-label): `SIGNAL CLEARED` / `NO TRADE
   TODAY` — the rarest, most decision-relevant fact leads.
2. **Direction + verbal anchor**: "Leaning up" (fixed published bands:
   50–55 coin-flip · 55–60 leaning · 60–70 favored · >70 strongly favored).
3. **Frequency-framed number + icon array**: "On 100 days that looked like
   today, price was higher after 4 days on **57**" — 100-dot array, 57 lit
   in accent. Natural frequencies beat percentages for low-numeracy readers
   (Gigerenzer); icon arrays make uncertainty physically visible (538's 2020
   redesign).
4. **Honest counterweight, same visual weight**: "…and lower on 43. A small
   edge, not a prediction." (Numeric uncertainty barely dents trust — van
   der Bles/Spiegelhalter; hedging and hiding do.)
5. **Horizon + pre-committed resolution rule**: "Resolves in 96h, measured
   against the 23:00 UTC close" (Kalshi/Polymarket settlement pattern).
6. **"What does this mean?" expander** (progressive disclosure, NN/g).
7. **Track-record chip**: "Past cleared signals: 61 of 100 correct" →
   links /signals.
8. **Provenance strip**: `UPDATED 07:00 UTC · DATA THROUGH D-1 23:00 ·
   MODEL v<x> · <sha>`.
9. **Persistent risk line** (not dismissable).

**NO-TRADE day design** (the differentiator): same card, same position, same
size — never a diminished empty state. Verdict "SIT OUT — today didn't clear
the bar", one-line reason ("edge too small vs costs"), scarcity-as-quality
framing ("the filter clears ~13 of 100 days — rare is the point"), and the
freed attention promotes the brief + one Learn lesson (WHOOP rest-day
pattern; anti-Robinhood).

**Copy/design bans (site policy):** no countdown-to-buy timers, no urgency
copy, no testimonials, no celebration animation on signals (streaks/confetti
live in Learn only), no naked probability without verbal anchor + complement,
no win-rate headline without coverage + misses beside it, named author,
disclaimer on every model-output surface. Fixture banner stays until real
data lands.

## 4. Learn (education strategy)

- **3 tracks, ~24 lessons, text-first, one voice** (Zerodha Varsity model):
  - **T1 · How crypto markets work** (8 new): what moves price; spot/perps/
    funding; volatility; sentiment (F&G, positioning); on-chain & macro;
    why most traders lose; what an edge really is; honest evaluation.
  - **T2 · Reading charts** (the 10 legacy TA modules, lightly edited) + a
    one-paragraph honesty note per module ("indicators describe, they don't
    predict — our momentum-only model scores ~zero") linking T1·8.
  - **T3 · Using the daily signal responsibly** (6 new): how the signal is
    built; reading the card; 1% position sizing; no-signal days are the
    point; drawdown math; your own rules checklist.
- **Glossary, 60–80 terms, ES+EN**, auto-linked from briefs and lessons —
  the SEO/LLM-citation play (original-data pages + glossaries still earn
  citations in 2026; generic "what is Bitcoin" content doesn't).
- **"Today's numbers explained" panel** on Home: templated value-bucket
  explainers (funding, F&G, regime, signal state) rendered against live
  pipeline numbers, linking to lessons. Pre-written buckets, zero generative
  content, zero marginal maintenance.
- **Mechanics:** localStorage checkmarks + per-track progress bar + one
  5-question quiz per track (static JSON). No accounts, no certificates.
  Streaks only here, never on signals.

## 5. Architecture (2026 verdict: keep the stack, add prerender)

- **Keep Vite + React 18 + TS.** Upgrade react-router-dom 6 → **React Router
  v7 framework mode**, `ssr:false` + async `prerender` globbing briefs/
  lessons → real HTML per route on GitHub Pages (SEO + no 404-hack; deep
  links return 200). Cheapest path (~1–2 days); Astro documented as fallback
  only if the site grows to thousands of MDX pages.
- **i18n:** path-prefixed `/es/…` routes + hreflang + x-default, prerendered
  both. Hand-rolled typed dictionary (2 locales); Paraglide later if strings
  multiply. Brief JSON is already bilingual.
- **Deploy:** custom GitHub Actions workflow (`deploy-pages`) triggered by
  the pipeline's daily JSON push (paths filter) — not cron (cron is
  best-effort and auto-disables). Public repo ⇒ Actions minutes free.
  Import data JSONs at build time (hashed) — Pages can't set cache headers.
- **Charts:** hand-rolled SVG (calibration, scorecard) themed by existing
  CSS tokens; visx primitives only if chart count grows. No Recharts.
- **Quality gates:** zod v4 validation of every data JSON at build time
  (malformed artifact ⇒ failed deploy, never a broken page); Lighthouse CI
  (`treosh/lighthouse-ci-action`, budgets on home/brief/lesson); 3–5
  Playwright smoke tests on the built output (signal renders, deep-link 200,
  /es/ renders, SVG present).

## 6. Integrity rules (carried from v1, unchanged)

1. No number on screen without a JSON artifact behind it; `"_fixture": true`
   fails the production build.
2. Predictions publish before outcomes, in separate commits; UI links both.
3. The lockbox (2026-01-01+) applies to the site.
4. Pending is a designed state, not an error.
5. Disclaimers on every model-output page.

## 7. Milestones v2

| # | Deliverable | Depends on |
|---|---|---|
| **W0** | RR7 framework-mode upgrade + prerender all routes + Actions deploy + zod build gate | nothing — start now |
| **W1** | Signal card v2 (gate-first, icon array, frequency copy, NO-TRADE hero) + merged Home (signal + brief highlights + numbers-explained panel skeleton) | W0 |
| **W2** | `/es/` i18n + glossary (first ~40 terms) + Learn IA: track pages, progress, T3 lessons 1–2, T2 legacy port | W0 |
| **W3** | `/signals` track record + `/trust` verification page + `site-export` CLI (pydantic mirror, atomic writes) wired to daily task; two-commit publish→resolve | W1; Phase 4.4 close for final numbers |
| **W4** | Remaining T1/T3 lessons + quizzes + Lighthouse/Playwright CI + SEO/OG/hreflang polish | W2 |
| **W5** | Brief pages on real `daily-report` output; calibration chart live after ≥50 resolved calls; equity after Phase 5 | Phase 4.5 / 5 |

**Now-vs-blocked:** W0–W2 and most of W4 are buildable today with fixtures,
while GDELT/scoring finish. W3's real numbers and W5 land as pipeline phases
close. The site never waits on research; research never bends for the site.

## 8. Success criteria (v1's, plus)

- Zero fabricated values reachable in production (build-enforced).
- Real prerendered HTML per route; Lighthouse ≥95 across the board; deep
  links 200.
- Every metric traceable to artifact + commit in <60s.
- A beginner can answer, from the card alone: what's the lean, how sure,
  when does it resolve, what should I do (usually: nothing), and where do I
  learn more.
- ES and EN first-class (routes, hreflang, briefs, glossary).
