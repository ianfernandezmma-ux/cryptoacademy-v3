# GDELT GKG dataset — completion record (2026-07-11)

The historical GDELT backfill (PLAN.md Fase 2 / phase-4.4 blocker) completed
on 2026-07-11. This documents what is on disk so nobody re-audits it from
scratch.

## What it is

Crypto-filtered rows from GDELT GKG 2.0 15-minute files (96/day), harvested
by `news/gdelt.py` (keyword byte-filter: BTC/ETH/crypto terms; see
`KEYWORDS`). One parquet per UTC day at
`data/raw/gdelt/YYYY/gkg_YYYYMMDD.parquet`. The 15-min `file_time` is the
PIT bound: GDELT saw the URL by then, independent of the publisher's claim.

## Inventory (verified 2026-07-11)

- **2,383 day-files, 2020-01-01 → 2026-07-10, zero missing days**, 198 MB.
- **2,128,061 rows** total. Per year (rows / BTC-tagged / ETH-tagged):
  2020: 121k/115k/9k · 2021: 286k/268k/22k · 2022: 263k/241k/22k ·
  2023: 493k/460k/33k · 2024: 560k/532k/34k · 2025: 262k/247k/21k ·
  2026 (→jul): 142k/135k/9k.
- **Integrity**: every parquet read back successfully after the parallel
  drain + one mid-run Windows reboot (sweep script:
  `data/_overnight/gdelt_verify.py`). Atomic .tmp-rename writes held up.
- **17 empty days, all one contiguous block: 2025-06-15 → 2025-07-01.**
  Verified against the source on 2026-07-11: GDELT's own archive returns
  404 for that window (200 immediately after) — a genuine GDELT outage,
  not a harvest defect. Do not retry; the 0-row parquets are correct and
  intentional (file existence = day done).
- **Machine-readable manifest**: `data/raw/gdelt/MANIFEST.json` (per-day
  row/byte counts, per-year stats, empty/missing lists). Regenerate after
  any re-harvest.

## Maintenance

- The hourly `GdeltHarvester` scheduled task keeps appending new days
  (day-granular, resumable, safe to interrupt).
- **Never run two harvesters at once** (same .tmp path per day). The
  scheduled task must be disabled while a manual/parallel drain runs.
- Backup snapshot: `OneDrive/CryptoAcademy-backups/
  gdelt-2020-2026_verified-20260711.zip` (192 MB). GDELT is re-downloadable,
  so the backup is convenience (a full re-harvest ≈ 2 h with 24 threads).

## Downstream

Unblocks: `backfill-regime` on full history → `validate-regime` →
news-block ablation re-run → with/without-regime comparison (formal close
of Phase 4.3 gate 2 → 4.4 close).
