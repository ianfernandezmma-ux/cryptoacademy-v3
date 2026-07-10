# demo/ — CryptoAcademy public site (Phase 6, planned early)

This folder holds everything related to the public website ("the demo").

- **`PLAN.md`** — the improvement plan: audit of the old v2 demo, what to
  keep, the target architecture, page specs, the JSON data contract, and
  build milestones. **Read this first.**
- **`legacy/`** — the old demo extracted from
  `cryptoacademy-thesis/Presentation2105/Demo/Thesis_v2Demo.zip`. Reference
  only (design tokens, layout language). Never deployed. Open
  `legacy/index.html` in a browser to see it (needs internet: unpkg CDN).
- **`contracts/`** — the site data contract (`site-data.md`) and valid
  example artifacts (`examples/*.json`, all marked `"_fixture": true` so
  they can never ship to production).
- **`site/`** — the Vite + React + TS app (M0+M1 built 2026-07-10).
  Product-oriented per Ian's pivot: Home / Today's Signal / Daily Brief /
  Learn, plain-language signals for crypto beginners, no research metrics
  in the UI. Run: `cd demo/site && npm install && npm run dev` (port 5173,
  also in `.claude/launch.json` as `demo-site`). Sample data lives in
  `site/public/data/` marked `"_fixture": true` and is banner-labeled in
  the UI until the pipeline writes real artifacts (M2).

## Ground rule

The site renders **only** real pipeline artifacts. No number appears on
screen without a JSON file behind it; missing data renders a designed
Pending state. See PLAN.md §8.
