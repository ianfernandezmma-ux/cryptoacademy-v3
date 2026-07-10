# Site data contract v1

Artifacts the pipeline writes into `demo/site/public/data/`. Enforced twice:
pydantic models at write time (`cryptoacademy site-export`, milestone M2) and
zod at site build time. Shared rules:

- Every artifact has `schema_version` (int), `generated_at` (UTC ISO-8601,
  `Z` suffix), `commit_sha` (short sha of the commit that produced the
  inputs; the publishing commit is implicit in git history).
- Example fixtures carry `"_fixture": true`; the production build fails if
  any loaded artifact contains that key.
- Absent artifact or `null` field ⇒ the UI renders Pending. Writers must
  never invent a value to fill a field.
- All floats raw (no pre-rounded strings); the UI owns formatting.

## latest.json — today's model output

```jsonc
{
  "schema_version": 1,
  "generated_at": "2026-07-10T06:58:12Z",
  "commit_sha": "abc1234",
  "model_version": "lgbm-full+meta@<git describe>",
  "signals": [
    {
      "asset": "BTC",              // "BTC" | "ETH"
      "horizon_h": 96,             // 24 | 96
      "p_up": 0.57,                // base model P(up), [0,1]
      "direction": "UP",           // "UP" | "DOWN"  (sign of p_up - 0.5)
      "meta_gate": {
        "pass": true,              // meta-label layer clears the trade
        "p_meta": 0.63,            // meta model probability
        "coverage_pct": 12.8       // historical share of days cleared
      },
      "regime": "risk_on",         // "risk_on" | "risk_off" | null (pending)
      "features_asof": "2026-07-09T23:59:59Z"  // last bar CLOSE used (D-1, PIT rule)
    }
  ]
}
```

Note: at 24h `meta_gate` is `null` — the meta layer was **rejected** at 24h
(−4.3pp); the site says so rather than hiding the horizon.

## metrics.json — honest research metrics

```jsonc
{
  "schema_version": 1,
  "generated_at": "...",
  "commit_sha": "...",
  "cv_scheme": "Purged 5-fold, embargo 22d, all trials registered",
  "n_trials_registry": 0,          // real distinct-identity count from data/trials/trials.jsonl
  "lockbox_note": "Data from 2026-01-01 onward is sealed until Phase 5.",
  "horizons": [
    {
      "horizon_h": 96,
      "label_spec": "triple-barrier m=1.0",
      "mcc": 0.093,
      "baseline_momentum_mcc": 0.0,
      "meta": { "hit_rate_base": 0.538, "hit_rate_gated": 0.616, "uplift_pp": 7.8, "coverage_pct": 12.8 },
      "dsr": null,                  // Phase 4.5
      "pbo": null                   // Phase 4.5
    }
  ],
  "challengers": [
    { "name": "PatchTST", "mcc_24h": 0.020, "mcc_96h": 0.028 },
    { "name": "Chronos-2 zero-shot", "mcc_24h": 0.014, "mcc_96h": 0.013,
      "caveat": "pretraining-overlap caveat — see methodology" }
  ]
}
```

## track-record.json — append-only prediction log

```jsonc
{
  "schema_version": 1,
  "generated_at": "...",
  "rows": [
    {
      "id": "2026-07-10_BTC_96",
      "published_at": "2026-07-10T07:00:03Z",
      "publish_sha": "abc1234",     // commit that added this row (pre-outcome)
      "asset": "BTC", "horizon_h": 96,
      "p_up": 0.57, "direction": "UP", "gate_pass": true,
      "outcome": null,               // filled LATER, in a separate commit:
      "resolved_at": null,           //   "hit" | "miss" | "barrier_timeout"
      "resolve_sha": null
    }
  ]
}
```

The two-commit publish→resolve pattern is the integrity mechanism: the UI
links both shas so anyone can verify the prediction predates the outcome.

## report-YYYY-MM-DD.json + briefs-index.json — daily brief

```jsonc
{
  "schema_version": 1,
  "generated_at": "...", "commit_sha": "...",
  "date": "2026-07-10",
  "llm": { "model": "qwen3.6:35b-a3b", "prompt_version": "report-v1" },
  "sections": [
    { "id": "market_overview", "title_en": "Market overview",
      "title_es": "Visión de mercado", "body_en": "...", "body_es": "..." }
    // btc_analysis, eth_analysis, sentiment, risk_flags, signals, watchlist, methodology_notes
  ]
}
```

`briefs-index.json`: `{ "dates": ["2026-07-10", ...] }` newest-first.

## features.json — per-retrain importances

```jsonc
{ "schema_version": 1, "generated_at": "...", "commit_sha": "...",
  "model_version": "...",
  "features": [ { "name": "funding_z_168h", "block": "derivatives", "gain": 412.7 } ] }
```

## equity.json — Phase 5 only

Shape TBD with the Phase 5 backtest design (series + costs model + DSR
context). The site ships the chart frame with a Pending state until then.
