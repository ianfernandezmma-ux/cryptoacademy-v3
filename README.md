# CryptoAcademy v3

ML trading signals for BTC/ETH with rigorous point-in-time discipline, a
bitemporal news pipeline scored by local LLMs (RTX 5090), and honest
validation (CPCV + purging/embargo, Deflated Sharpe, PBO, final lockbox).

Full roadmap: [PLAN.md](PLAN.md).

## Why v3

v2's headline results were inflated by (1) hyperparameter tuning on the
reported out-of-sample predictions, (2) same-day news leakage (24h sentiment
aggregates joined to the midnight bar), and (3) in-sample feature/threshold
selection. v3 starts from the honest baseline (MCC ~0.35, holdout Sharpe 0.86)
and enforces point-in-time correctness in CI.

## The one rule

> No information enters a feature before its `usable_at` timestamp, where
> `usable_at = max(published_at, first_seen_at) + buffer`.

`tests/test_pit_leakage.py` encodes the v2 bug as a permanent regression test.

## Quickstart

```powershell
uv sync --all-groups
uv run pytest              # includes the anti-leakage suite
uv run cryptoacademy --help
uv run cryptoacademy status
```

Scheduled tasks (registered via `schtasks`, see `scripts/register_tasks.ps1`):

| Task | Frequency | Command |
|---|---|---|
| News collector | every 10 min | `cryptoacademy collect` |
| Open interest archiver | hourly | `cryptoacademy archive-oi` |

## Secrets

Copy `.env.example` to `.env` and fill in the keys (never committed):
`COINDESK_API_KEY` (developers.coindesk.com), `FRED_API_KEY`
(fred.stlouisfed.org), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (@BotFather),
`GITHUB_PAT` (fine-grained token scoped to this repo).

## Layout

```
configs/          assets.yaml (single code path for all assets), feeds.yaml
src/cryptoacademy/
  news/           bitemporal store, PIT rules, RSS collector
  data/           binance.vision bulk loader, funding, OI archiver, F&G
  notify/         telegram
  cli.py          all entry points
tests/            anti-leakage suite + store/parsing tests
data/ (gitignored)  raw parquet + news.duckdb
```
