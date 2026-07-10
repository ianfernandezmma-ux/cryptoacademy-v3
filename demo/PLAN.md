# CryptoAcademy Demo v3 — Site Improvement Plan

> Written 2026-07-10, while the GDELT backfill/scoring runs. Source analyzed:
> `Presentation2105/Demo/Thesis_v2Demo.zip` from the old repo
> (`ianfernandezmma-ux/cryptoacademy-thesis`), copied here into `demo/legacy/`
> for reference. This plan is the blueprint for the Phase 6 website (PLAN.md
> Fase 6), designed so the site can be scaffolded NOW and wired to real
> pipeline artifacts as Phases 4.5/5 deliver them.

---

## 1. What the old demo is (inventory)

A Claude Design export, never productionized:

| File | Content |
|---|---|
| `index.html` + `landing.jsx` | Landing: giant CRYPTO/ACADEMY hero split by a floating 3D coin PNG, fake market ticker, "How it works" 4-step cards, footer. 3 themes (Eclipse dark-green / Tidewater teal / Bone cream). |
| `courses.html` + `courses.jsx` | Curriculum page: 10 TA modules in 2 tiers, 3 copy tones (academic/mix/premium), deep-dives, enroll band with invented cohort seats ("142/180"). |
| `ml-model.html` + `ml-model.jsx` | Model dashboard: BTC/ETH prediction cards (bias/confidence/size/risk flags — all invented), empty equity-curve frame ("AWAITING BACKTEST OUTPUT"), 6 metric tiles ("Pending"), illustrative feature-importance table, disclaimer. |
| `daily-reports.html` + `daily-reports.jsx` | Daily brief host page: today's report as a "document cover" (fake PDF metadata, fixed TOC of 8 sections), 7-day archive of fake cards. |
| `canvas.html` + `design-canvas.jsx` | Figma-ish canvas wrapper to view all artboards. Design tool, not a product page. |

Runtime: React 18 UMD **development builds** + Babel standalone from unpkg,
JSX compiled in the browser, all styling inline `style={{}}` objects, fixed
1440px design width, no routing, no build step, no deploy.

---

## 2. Audit — what is wrong with it

### 2.1 Fabricated data (the v2 disease, again)
The single worst problem. The demo hardcodes invented numbers presented as
live outputs:

- Ticker: BTC $67,420.18 +2.31%, "Model bias: long 72%", "Sentiment:
  risk-on +0.41", "Signals issued: 14 today".
- Prediction cards: LONG 72%/64% confidence, "1.2 × R" position size,
  invented risk flags, "Updated 14:23 UTC".
- "Live cohort · Fall 2026 · 142/180 seats", "Model online" footer badge,
  fake archive with "Cycle 135–142", fake PDF filenames.
- Feature importances "illustrative", domains hand-assigned.

v2 died because published numbers didn't survive scrutiny (MCC 0.56 published
vs 0.34 real; `predict_stub.py` relabeling a stale prediction as fresh daily).
A demo that fabricates model output — even "illustratively" — repeats the
same crime in the storefront. **The v3 site must render only real pipeline
artifacts, and show explicit empty/pending states otherwise.** (To its
credit, the old demo already does this in places: "Pending" metric tiles,
"AWAITING BACKTEST OUTPUT", "Feed offline", "Output · Illustrative" tags.
That instinct becomes a hard rule in v3.)

### 2.2 Not a real website
- React dev builds + in-browser Babel: seconds of compile on load, console
  warnings, unusable for a public deploy; unpkg CDN is a single point of
  failure (and blocked by the TLS proxy in some environments).
- No routing (5 disconnected .html files), no build, no minification, no
  caching strategy, no 404, no sitemap/robots, no analytics.
- All styles inline per-element: no reuse, huge JSX, impossible to theme
  globally (3 themes exist but subpages hardcode `THEMES.greenDark`).

### 2.3 Not responsive
Fixed 1440px artboard thinking: 196px hero font, 5-column flex rows,
`padding: '92px 56px'` everywhere, no media queries, no `clamp()`. Unusable
on mobile — where most of a demo's audience will open it.

### 2.4 Weak positioning
The demo sells a **course** (enroll CTAs everywhere, invented seats) and
treats the model as a side tool. The actually differentiated asset of v3 is
the **research integrity**: point-in-time discipline, registered trials,
purged CV, deflated Sharpe, honest nulls, predictions timestamped BEFORE
outcomes. No competitor demo can show that. The site should lead with it.

### 2.5 No data layer
The old pipeline had a JSON contract (`contracts/schemas.py`:
`validate_prediction_snapshot` — probability, direction, scorecard.mcc,
features_used…) and a "JSON is the source of truth" site builder, but the
demo is not wired to anything. The new site must be born wired: every number
on screen traceable to a JSON artifact produced (and committed) by the
pipeline.

### 2.6 Accessibility / SEO / i18n
- `<button>` without action, links `href="#signin"` dead, no focus states,
  glow-on-dark contrast issues in muted text (`#5a5d54` on `#080a09` ≈ 3.2:1).
- No meta description, no OpenGraph/Twitter cards, no favicon, title only on
  index.
- English only; PLAN.md Fase 6 requires the daily summary ES/EN.

---

## 3. What to KEEP from the old demo

The visual identity is genuinely good — this is the part worth migrating:

1. **Design tokens.** The Eclipse theme (bg `#080a09`, accent `#a8ee71`,
   panel `rgba(255,255,255,0.025)`, line `rgba(255,255,255,0.07)`) +
   Space Grotesk display / JetBrains Mono data. Bone cream as light theme.
   Port `THEMES` verbatim into CSS custom properties.
2. **Design language.** Mono uppercase micro-labels with letter-spacing,
   hairline dividers, dot-grid backdrops, radial accent glows, kicker + huge
   balanced headline section heads, dashed-border footnote rows, status
   bands of key/value cells. Distinctive and consistent.
3. **Information architecture** (with one addition): Landing / Model /
   Daily Brief are the right pages. Add **Track Record** (the killer page,
   see §6.4). Courses survives as static content, de-faked.
4. **Honest placeholder states** ("Pending", "AWAITING BACKTEST OUTPUT",
   "Feed offline") — formalized as first-class UI states driven by data
   presence, not hand-placed.
5. **The disclaimer block** — keep, strengthen (thesis project, not
   financial advice), render on every model-output page.
6. **Component naming/structure** (Nav, SectionHead, StatusBand, Step,
   PredictionCard, ArchiveCard…) maps 1:1 to the new component library.

---

## 4. Vision — what "the perfect site" is

**A public, verifiable, honest window into a real ML trading pipeline.**
One sentence pitch on the hero:

> "A machine-learning trading signal for BTC & ETH — with every prediction
> published before the outcome, every trial registered, and every metric
> deflated. Honest numbers only."

Three product surfaces:

1. **The signal** — today's model output per asset (probability, bias,
   meta-label gate, regime context), refreshed by the daily pipeline.
2. **The daily brief** — the LLM-written (qwen3.6:35b) morning report,
   ES/EN, archived forever.
3. **The proof** — the track record: an append-only, git-timestamped log of
   every published prediction and its later outcome, plus the honest
   research metrics (MCC per horizon, DSR with real registry N, coverage of
   the meta layer, calibration curve). This page is the thesis defense made
   permanent.

The site is 100% static. The pipeline writes JSON; CI builds and deploys;
git history is the integrity proof.

---

## 5. Architecture & stack

```
demo/
├── PLAN.md                  ← this file
├── README.md                ← folder guide
├── legacy/                  ← old v2 demo, reference only (never deployed)
├── contracts/               ← JSON data contract + examples (checked in)
│   ├── site-data.md         ← contract spec (source of truth for shapes)
│   └── examples/*.json      ← valid examples used as fixtures in site tests
└── site/                    ← the actual web app (built at milestone M0)
    ├── index.html
    ├── src/
    │   ├── main.tsx         ← router + theme provider
    │   ├── tokens.css       ← THEMES ported to CSS custom properties
    │   ├── components/      ← Nav, SectionHead, StatusBand, SignalCard,
    │   │                      MetricTile, EquityChart, CalibrationChart,
    │   │                      PredictionTable, BriefDoc, Pending, Footer
    │   ├── pages/           ← Home, Model, Brief, TrackRecord, Method, Courses
    │   └── lib/data.ts      ← typed loaders + zod validation of /data JSONs
    ├── public/data/         ← pipeline-written JSON artifacts (see §7)
    └── tests/               ← contract fixtures render without fabrication
```

**Stack decision:** Vite + React 18 + TypeScript + CSS custom properties
(no Tailwind — the design language is token-driven and bespoke; inline styles
get extracted to co-located CSS modules). Recharts or lightweight hand-rolled
SVG (the old demo's SVG axis frame is already 80% of a chart component) for
equity/calibration. `zod` for runtime validation of data JSONs — a malformed
artifact must fail the build, not render garbage.

- React Router in hash-less static mode with prerendered routes (or
  `vite-plugin-ssg`) so GitHub Pages serves real HTML per page (SEO).
- Deploy: GitHub Pages via Actions (free, keeps everything in the repo whose
  git history IS the integrity proof). Vercel optional later for previews.
- i18n: minimal dictionary module (ES/EN toggle persisted in localStorage);
  brief content arrives already bilingual from the pipeline.
- No backend, no client-side price polling in v1 (a "live" ticker invites
  fabrication-adjacent decoration; if added later, label it "exchange feed,
  not model input").

---

## 6. Page-by-page spec

### 6.1 Home (`/`)
Keep the theatrical hero (coin, split CRYPTO/ACADEMY, animations) — it's the
brand moment — but every number below it becomes real:

- **Status band** (replaces fake ticker): `Model` LightGBM + meta v<hash> ·
  `Last run` <generated_at from latest.json> · `Signal today` gated/pass ·
  `Brief` published/pending · `Track record` N predictions since <date>.
  Each cell links to its page.
- **"How it works"** 4 steps, rewritten for the real pipeline: 1) Data with
  PIT discipline → 2) Model + meta-label gate → 3) Daily brief 07:00 UTC →
  4) Published-then-scored track record.
- **Honesty strip** (new, small): "v2 of this project published inflated
  numbers. v3 exists so that can't happen again. Read how →" links to
  Method. Disarming, memorable, unique.

### 6.2 Model (`/model`)
The old dashboard layout survives almost intact, but driven by
`latest.json`:

- **SignalCard per asset**: direction probability (not "confidence"),
  meta-label gate state (TRADE / NO-TRADE with coverage context: "the meta
  layer only clears ~13% of days at 96h — most days are NO-TRADE and that is
  the honest answer"), horizon (24h/96h tabs), regime badge (risk-on/off from
  classifier v3), `generated_at` + git commit short-sha of the artifact.
- **Performance**: metric tiles fed by `metrics.json` — MCC per horizon,
  hit-rate uplift from meta layer (53.8→61.6% @96h), DSR when Phase 4.5
  computes it, PBO. Every tile shows its provenance ("purged 5-fold CV,
  embargo 22d, N=<registry count> registered trials"). Tiles without data
  render the Pending state.
- **Equity chart frame**: stays "awaiting backtest output" until Phase 5
  writes `equity.json`. The frame component is built now.
- **Feature importance**: real gain importances exported from the trained
  LightGBM at matrix-build time (`features.json`), with feature-block domain
  tags from the real blocks (price/derivatives/volatility/news/regime).
- Disclaimer block at bottom.

### 6.3 Daily Brief (`/brief`, `/brief/YYYY-MM-DD`)
The "document cover" concept is good; make the document real:

- Today: rendered from `report-YYYY-MM-DD.json` (written by the Phase 4.5
  `daily-report` command; sections map to the report schema, not a fake
  PDF). ES/EN toggle. "Generated by qwen3.6:35b from pipeline outputs;
  reviewed by no one — this is a machine artifact" honesty note.
- Archive: real list from `briefs-index.json`, calendar navigation,
  permalinks. No fake "cohort drive".

### 6.4 Track Record (`/track-record`) — NEW, the flagship
The page the old demo was missing and the thesis needs:

- **Prediction log table**: one row per published prediction — date,
  asset, horizon, P(up), gate decision, the git commit sha + timestamp that
  published it, and (once the horizon elapses) the realized outcome and
  hit/miss. Outcomes are filled by a later pipeline run in a separate
  commit — the two-commit pattern is the verifiable-integrity mechanism from
  PLAN.md Fase 6. Link each row to the GitHub commit.
- **Running scorecard**: live hit rate vs the 50% line and vs the CV
  estimate, with binomial CI — showing the CI when N is small instead of
  hiding it is exactly the honesty brand.
- **Calibration curve** once ≥~50 resolved predictions exist (component
  built now, Pending until then).

### 6.5 Methodology (`/method`)
Mostly prose + a few diagrams; content already exists in docs/:

- The two iron rules (PIT knowledge timestamps; every trial registered).
- What v2 got wrong (§1.2 of PLAN.md, told as a story — this is the thesis).
- CV scheme diagram (purged k-fold + embargo), DSR/N explanation, lockbox
  policy ("2026-01-01+ is sealed until Phase 5 ends — including from this
  website").
- Data inventory table (the ~15 sources with their publication-clock rules).

### 6.6 Courses (`/courses`) — de-faked, deprioritized
Keep the 10-module curriculum as static content with the "mix" tone. Remove
seats/cohort/enroll theater; CTA becomes "join the waitlist" (mailto or
form-less). Ship last; it blocks nothing.

---

## 7. Data contract (JSON is the source of truth)

All artifacts written by the pipeline into `demo/site/public/data/`,
validated by zod at build time AND by a pydantic mirror in
`src/cryptoacademy/` at write time (single schema, two enforcement points —
same philosophy as the old `contracts/schemas.py`, which was the right
idea). Full spec in `contracts/site-data.md`; summary:

| Artifact | Writer | Cadence | Key fields |
|---|---|---|---|
| `latest.json` | daily pipeline | daily | per asset×horizon: p_up, direction, meta_gate {pass, coverage_pct}, regime, model_version, generated_at, features_asof, commit_sha |
| `metrics.json` | Phase 4.5 eval run | per close | per horizon: mcc, hit_rate, meta_uplift, dsr, pbo, n_trials_registry, cv_scheme description |
| `track-record.json` | daily pipeline (append) + outcome filler | daily | rows: {published_at, commit_sha, asset, horizon, p_up, gate, outcome?, resolved_at?, resolved_sha?} |
| `report-YYYY-MM-DD.json` + `briefs-index.json` | `daily-report` cmd | daily | sections[] {id, title_en/es, body_en/es}, model_inputs_digest, llm {model, prompt_version} |
| `features.json` | training run | per retrain | [{name, block, gain_importance}] |
| `equity.json` | Phase 5 backtest | per run | series, costs_model, dsr_context — absent until Phase 5 |

**Contract rules:** every artifact carries `schema_version`, `generated_at`
(UTC ISO), and `commit_sha`; the site NEVER computes a financial metric
client-side; absence of an artifact/field ⇒ Pending state, never a default
number; timestamps rendered as-is with "UTC" suffix.

---

## 8. Integrity rules for the site (the demo's iron rules)

1. **No number on screen without a JSON artifact behind it.** Fixtures in
   `contracts/examples/` are used in tests only; the production build fails
   if it would ship example data (guard: examples carry
   `"_fixture": true`, build rejects it).
2. **Predictions publish before outcomes, in separate commits.** The UI
   links both commits. This is the site's headline feature, not a footnote.
3. **The lockbox applies to the site**: nothing derived from post-2026-01-01
   evaluation data appears until Phase 5 opens it.
4. **Pending is a designed state, not an error** — every data-driven
   component has one (the old demo's best instinct, made systematic).
5. **Disclaimers on every page that shows model output.**

---

## 9. Milestones

| # | Deliverable | Depends on | Est. |
|---|---|---|---|
| **M0** | Scaffold `demo/site` (Vite+React+TS), port THEMES→tokens.css, Nav/Footer/SectionHead/StatusBand/Pending components, responsive layout system, deploy pipeline to GitHub Pages with a "under construction, honest since day 1" homepage | nothing — **can start now** | 1 day |
| **M1** | Home + Model pages rendering `contracts/examples/` fixtures in dev, real `metrics.json` (current honest numbers: MCC 0.065/0.093, meta +7.8pp @96h/12.8% cov, PatchTST/Chronos challenger table) in prod. Method page prose. | M0; numbers already exist in docs/phase4-handoff.md | 1–2 days |
| **M2** | Pipeline writer: `cryptoacademy site-export` CLI command (pydantic schemas mirroring the contract, atomic writes like old `atomic_write_json`) producing latest.json + metrics.json + features.json from real artifacts. Wire daily task. | M1; Phase 4.4 close for final numbers | 1 day |
| **M3** | Daily Brief pages consuming `daily-report` output; ES/EN toggle | Phase 4.5 `daily-report` command | 1 day after cmd exists |
| **M4** | Track Record page + two-commit publish/resolve mechanism in the daily pipeline; calibration component | M2 running daily ≥1 week | 1–2 days |
| **M5** | Equity/backtest section, per-regime breakdown | Phase 5 | later |
| **M6** | Courses page de-faked; SEO/OG polish; Lighthouse ≥95 across the board | any time after M1 | 0.5 day |

**Now-vs-blocked:** M0, M1, M6 and the M2 CLI skeleton are buildable today
(while GDELT scores) without touching any pending research gate. M3–M5 land
as their pipeline dependencies close — the site should never wait on
research, and research should never bend for the site.

---

## 10. Success criteria

- Loads real data or shows designed Pending — zero fabricated values
  reachable in a production build (enforced by test + fixture guard).
- Mobile-first responsive; Lighthouse ≥95 perf/a11y/SEO/best-practices.
- Every displayed metric traceable: click → provenance (artifact, commit,
  CV scheme, N).
- A skeptical thesis examiner can verify a prediction's timestamp from the
  page in <60 seconds via the linked commit.
- Deployed publicly with automated daily updates and zero marginal cost.
