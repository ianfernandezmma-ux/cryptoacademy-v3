"""Command-line interface. Every scheduled task and manual operation enters
through here, so behavior is identical whether run by hand or by the scheduler."""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import UTC, datetime

import typer
import yaml

from cryptoacademy import config

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _setup_logging(name: str) -> None:
    config.ensure_dirs()
    handler = logging.handlers.TimedRotatingFileHandler(
        config.LOGS_DIR / f"{name}.log", when="midnight", backupCount=14, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


def _load_feeds() -> list[dict]:
    with open(config.CONFIGS_DIR / "feeds.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["feeds"]


@app.command()
def collect() -> None:
    """Run one news-collection pass (scheduled every 10 minutes)."""
    _setup_logging("collector")
    from cryptoacademy.news.collector import collect_once
    from cryptoacademy.news.store import NewsStore
    from cryptoacademy.notify import telegram

    log = logging.getLogger("collect")
    try:
        with NewsStore(config.NEWS_DB_PATH) as store:
            result = collect_once(store, _load_feeds())
        log.info("run complete: %s", result)
        manifest = config.LOGS_DIR / "last_collect_manifest.json"
        manifest.write_text(
            json.dumps({"at": datetime.now(UTC).isoformat(), **result}), encoding="utf-8"
        )
        if result["feeds_failed"] >= len(_load_feeds()) // 2:
            telegram.send(f"⚠️ CryptoAcademy collector: {result['feeds_failed']} feeds failed")
    except Exception as exc:
        log.exception("collector run failed")
        telegram.send(f"🔴 CryptoAcademy collector crashed: {exc}")
        raise


@app.command()
def archive_oi() -> None:
    """Archive Binance open interest (scheduled hourly; Binance keeps only ~30d)."""
    _setup_logging("open_interest")
    from cryptoacademy.data.open_interest import archive_open_interest
    from cryptoacademy.notify import telegram

    log = logging.getLogger("archive_oi")
    failures = []
    for asset, meta in config.load_assets().items():
        try:
            archive_open_interest(asset, meta["perp_symbol"])
        except Exception as exc:  # one asset must not block the other
            log.exception("OI archive failed for %s", asset)
            failures.append(f"{asset}: {exc}")
    if failures:
        telegram.send("🔴 CryptoAcademy OI archiver failed: " + "; ".join(failures))
        raise typer.Exit(1)


@app.command()
def backfill_prices(start: str = "2020-01", interval: str = "1h") -> None:
    """Download full kline + funding history from data.binance.vision."""
    _setup_logging("backfill")
    from cryptoacademy.data.binance_vision import download_funding, download_klines, gap_report

    log = logging.getLogger("backfill")
    for asset, meta in config.load_assets().items():
        for market, symbol in (("spot", meta["spot_symbol"]), ("futures/um", meta["perp_symbol"])):
            df = download_klines(asset, symbol, market, interval=interval, start=start)
            gaps = gap_report(df)
            log.info(
                "%s %s: %d bars, %s -> %s, %d gaps",
                asset, market, len(df), df["open_time"].min(), df["open_time"].max(), len(gaps),
            )
            if len(gaps):
                log.warning("%s %s gaps:\n%s", asset, market, gaps)
        funding = download_funding(asset, meta["perp_symbol"], start=start)
        log.info("%s funding: %d rows", asset, len(funding))


@app.command()
def backfill_altdata() -> None:
    """Binance metrics (OI/long-short/taker, 5-min since 2020-09), Deribit DVOL,
    Wikipedia pageviews, CFTC COT."""
    _setup_logging("backfill")
    from cryptoacademy.data.altdata import (
        download_cot,
        download_dvol,
        download_metrics,
        download_wiki_pageviews,
    )

    log = logging.getLogger("altdata")
    download_wiki_pageviews()
    download_cot()
    for currency in ("BTC", "ETH"):
        download_dvol(currency)
    for asset, meta in config.load_assets().items():
        log.info("downloading %s metrics dumps (this takes a while)...", asset)
        download_metrics(asset, meta["perp_symbol"])


@app.command()
def backfill_gdelt(max_days: int = 30) -> None:
    """Harvest GDELT GKG history (resumable; scheduled hourly until complete).

    Telegram progress notes at ~10% milestones so a multi-day backfill is
    observable without hourly spam.
    """
    _setup_logging("gdelt")
    from cryptoacademy.news.gdelt import harvest
    from cryptoacademy.notify import telegram

    log = logging.getLogger("gdelt")
    try:
        result = harvest(max_days=max_days)
    except Exception as exc:
        log.exception("gdelt harvest failed")
        telegram.send(f"🔴 GDELT harvester crashed: {exc}")
        raise
    if result["processed"] and result.get("done_pct") is not None:
        prev_pct = result["done_pct"] - 100 * result["processed"] / max(
            1, result["processed"] + result["remaining"]
        )
        if result["remaining"] == 0:
            telegram.send("✅ GDELT backfill COMPLETO: historia 2020→hoy lista.")
        elif int(result["done_pct"] // 10) > int(max(prev_pct, 0) // 10):
            telegram.send(
                f"📰 GDELT backfill: {result['done_pct']}% "
                f"({result['remaining']} días pendientes)"
            )
    typer.echo(str(result))


@app.command()
def score_news(limit: int = 500) -> None:
    """Score pending articles with the local LLM (dedup + structured extraction).

    Local AI is OFF by default on this shared gaming machine: this command does
    nothing unless CRYPTOACADEMY_ENABLE_LOCAL_AI=1 is set for the run.
    """
    _setup_logging("scoring")
    from cryptoacademy.localai import ENABLE_ENV, local_ai_enabled

    log = logging.getLogger("score_news")
    if not local_ai_enabled():
        msg = f"score-news skipped: local AI is OFF (set {ENABLE_ENV}=1 to run it)."
        log.warning(msg)
        typer.echo(msg)
        return

    from cryptoacademy.news.scoring import score_pending
    from cryptoacademy.notify import telegram

    try:
        result = score_pending(limit=limit)
        log.info("scoring run: %s", result)
        typer.echo(str(result))
    except Exception as exc:
        log.exception("scoring failed")
        telegram.send(f"🔴 CryptoAcademy scoring crashed: {exc}")
        raise


@app.command()
def backfill_macro() -> None:
    """Coin Metrics on-chain, FRED/ALFRED macro, stablecoins, ETF flows —
    every row with its published_at_utc knowledge timestamp."""
    _setup_logging("backfill")
    from cryptoacademy.data.macro_onchain import backfill_macro_all

    backfill_macro_all()


@app.command()
def snapshot_options_chain() -> None:
    """Daily Deribit option-chain snapshot (forward archive; no free history)."""
    _setup_logging("options")
    from cryptoacademy.data.macro_onchain import snapshot_options
    from cryptoacademy.notify import telegram

    try:
        for currency in ("BTC", "ETH"):
            snapshot_options(currency)
    except Exception as exc:
        telegram.send(f"🔴 options snapshot failed: {exc}")
        raise


@app.command()
def generate_labels() -> None:
    """CUSUM + triple-barrier labels on real data, both horizons (24h, 96h)."""
    _setup_logging("labels")
    import json

    from cryptoacademy.labels.generate import generate_all

    summary = generate_all()
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def train_baselines() -> None:
    """Phase 4.2 baselines: always-long, momentum-only, full-feature LightGBM
    under purged CV, both horizons; every config registered."""
    _setup_logging("train")
    import json

    from cryptoacademy.models.train import run_baselines

    results = run_baselines()
    typer.echo(json.dumps(results, indent=2, default=str))


@app.command()
def run_sweep(n_trials: int = 40) -> None:
    """Phase 4.2: label variants, Optuna sweep, SHAP-stable selection,
    ablations — everything registered."""
    _setup_logging("train")
    import json

    from cryptoacademy.labels.generate import generate_variants
    from cryptoacademy.models.sweep import (
        block_ablations,
        optuna_sweep,
        shap_stable_features,
    )
    from cryptoacademy.models.train import BASE_PARAMS, evaluate_config

    generate_variants()
    report: dict = {}
    for horizon in ("24h", "96h"):
        best = optuna_sweep(horizon, n_trials=n_trials)
        params = dict(BASE_PARAMS)
        bm = best["best_params"].pop("barrier_mult", None)
        params.update(best["best_params"])
        selected = shap_stable_features(horizon, params, barrier_mult=bm)
        # tag makes the in-loop selection bias explicit (audit F1): this score
        # is selection-conditioned; the unbiased anchor is the full-feature run
        sel_metrics = evaluate_config(
            horizon, ["price", "derivatives", "onchain", "macro", "news"],
            params=params, tag="shap-selected-INLOOP", barrier_mult=bm,
            features_override=selected,
        )
        ablations = block_ablations(horizon, params, barrier_mult=bm)
        report[horizon] = {
            "sweep_best_mcc": best["best_value"],
            "best_params": {**best["best_params"], "barrier_mult": bm},
            "n_selected_features": len(selected),
            "selected_mcc": sel_metrics["mean_mcc"],
            "selected_acc": sel_metrics["mean_acc"],
            "ablations": ablations,
        }
    (config.DATA_DIR / "trials").mkdir(parents=True, exist_ok=True)
    out = config.DATA_DIR / "trials" / "phase42_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    typer.echo(json.dumps(report, indent=2, default=str))


@app.command()
def backfill_regime(max_days: int = 5000) -> None:
    """Score daily risk regimes over all harvested GDELT days (resumable).

    Local AI is OFF by default on this shared gaming machine: this command does
    nothing unless CRYPTOACADEMY_ENABLE_LOCAL_AI=1 is set for the run.
    """
    _setup_logging("regime")
    from cryptoacademy.localai import ENABLE_ENV, local_ai_enabled

    log = logging.getLogger("regime")
    if not local_ai_enabled():
        msg = f"backfill-regime skipped: local AI is OFF (set {ENABLE_ENV}=1 to run it)."
        log.warning(msg)
        typer.echo(msg)
        return

    from cryptoacademy.news.regime import backfill_regime as _run

    result = _run(max_days=max_days)
    typer.echo(str(result))


@app.command()
def validate_regime() -> None:
    """Run the standalone regime quality gates against forward outcomes."""
    _setup_logging("regime")
    import polars as pl

    from cryptoacademy.news.regime import REGIME_PATH
    from cryptoacademy.validation.regime_gates import format_report, validate_regime_scores

    regime = pl.read_parquet(REGIME_PATH)
    results = validate_regime_scores(regime)
    typer.echo(format_report(results))


@app.command()
def run_meta(meta_threshold: float = 0.55) -> None:
    """Phase 4.4: meta-labeling evaluation for both horizons (best 4.2 configs)."""
    _setup_logging("train")
    import json

    from cryptoacademy.models.meta import run_meta_labeling
    from cryptoacademy.models.train import BASE_PARAMS

    report_path = config.DATA_DIR / "trials" / "phase42_report.json"
    best = json.loads(report_path.read_text(encoding="utf-8"))
    out = {}
    for horizon in ("24h", "96h"):
        params = dict(BASE_PARAMS)
        bp = dict(best[horizon]["best_params"])
        bm = bp.pop("barrier_mult", None)
        params.update(bp)
        m = run_meta_labeling(
            horizon, params=params, barrier_mult=bm, meta_threshold=meta_threshold
        )
        out[horizon] = {k: v for k, v in m.items() if k != "folds"}
    typer.echo(json.dumps(out, indent=2, default=str))


@app.command()
def run_patchtst() -> None:
    """Phase 4.4: PatchTST classifier challenger, both horizons, purged CV."""
    _setup_logging("train")
    import json

    from cryptoacademy.models.dl import evaluate_patchtst

    out = {}
    for horizon in ("24h", "96h"):
        m = evaluate_patchtst(horizon)
        out[horizon] = {k: v for k, v in m.items() if k != "folds"}
    typer.echo(json.dumps(out, indent=2, default=str))


@app.command()
def run_chronos() -> None:
    """Phase 4.4: Chronos-2 zero-shot direction benchmark, both horizons."""
    _setup_logging("train")
    import json

    from cryptoacademy.models.chronos_bench import evaluate_chronos

    out = {h: evaluate_chronos(h) for h in ("24h", "96h")}
    typer.echo(json.dumps(out, indent=2, default=str))


@app.command()
def build_matrix() -> None:
    """Assemble the per-asset feature matrices (PIT as-of joins + global shift)."""
    _setup_logging("matrix")
    from cryptoacademy.features.matrix import build_matrix as _build

    for asset in config.load_assets():
        df = _build(asset)
        typer.echo(f"{asset}: {len(df)} rows x {len(df.columns)} cols")


@app.command()
def daily_update() -> None:
    """One command that refreshes every dataset and rebuilds the matrices.
    Scheduled daily 06:30 UTC — after Coin Metrics' D-1 completion."""
    _setup_logging("daily_update")
    from datetime import UTC, datetime, timedelta

    from cryptoacademy.data.altdata import (
        download_cot,
        download_dvol,
        download_metrics,
        download_wiki_pageviews,
    )
    from cryptoacademy.data.binance_vision import (
        download_funding,
        download_klines,
        gap_report,
    )
    from cryptoacademy.data.fng import download_fng
    from cryptoacademy.data.macro_onchain import backfill_macro_all
    from cryptoacademy.features.matrix import build_matrix as _build
    from cryptoacademy.notify import telegram

    log = logging.getLogger("daily_update")
    failures: list[str] = []
    start = (datetime.now(UTC) - timedelta(days=40)).strftime("%Y-%m")

    def _gap_check() -> None:
        # recent window only: 15 small historical gaps (2020-2024, exchange
        # outages) are known and documented — NEW gaps are what's actionable
        import polars as pl

        cutoff = datetime.now(UTC) - timedelta(days=45)
        for a, m in config.load_assets().items():
            df = pl.read_parquet(
                config.RAW_DIR / "klines" / a / "spot" / f"{m['spot_symbol']}_1h.parquet"
            ).filter(pl.col("open_time") >= cutoff)
            gaps = gap_report(df)
            if len(gaps):
                raise RuntimeError(f"{a}: {len(gaps)} hourly gaps in recent klines")

    for step_name, step in [
        ("prices", lambda: [
            download_klines(a, m["spot_symbol"], "spot", start=start)
            for a, m in config.load_assets().items()
        ]),
        ("funding", lambda: [
            download_funding(a, m["perp_symbol"], start=start)
            for a, m in config.load_assets().items()
        ]),
        # metrics/DVOL/wiki/COT were NEVER refreshed by daily-update before
        # (audit 2026-07-11: the derivatives block — the strongest feature
        # family — sat 9 days stale while matrices rebuilt daily). metrics is
        # resumable (skips existing days), the rest are cheap full refreshes.
        ("metrics", lambda: [
            download_metrics(a, m["perp_symbol"])
            for a, m in config.load_assets().items()
        ]),
        ("dvol", lambda: [download_dvol(c) for c in ("BTC", "ETH")]),
        ("wiki_attention", download_wiki_pageviews),
        ("cot", download_cot),
        ("fng", download_fng),
        ("macro_onchain_etf", backfill_macro_all),
        ("gap_check", _gap_check),
        ("matrices", lambda: [_build(a) for a in config.load_assets()]),
    ]:
        try:
            step()
            log.info("daily-update step ok: %s", step_name)
        except Exception as exc:  # keep going; report all failures at once
            log.exception("daily-update step failed: %s", step_name)
            failures.append(f"{step_name}: {exc}")

    # freshness gate: a step can 'succeed' while its dataset silently stops
    # advancing (API returns stale data, source outage) — check max
    # timestamps against each feed's expected cadence
    stale: list[str] = []
    import polars as pl

    now = datetime.now(UTC)
    for label, path, tcol, max_age_h in [
        ("klines", config.RAW_DIR / "klines" / "btc" / "spot" / "BTCUSDT_1h.parquet",
         "open_time", 6),
        ("metrics", config.RAW_DIR / "metrics" / "btc" / "BTCUSDT_metrics.parquet",
         "create_time", 48),
        ("dvol", config.RAW_DIR / "options" / "btc_dvol.parquet", "time", 48),
        ("fng", config.RAW_DIR / "sentiment" / "fear_greed.parquet", "date", 48),
        ("onchain", config.RAW_DIR / "onchain" / "coinmetrics.parquet",
         "published_at_utc", 72),
    ]:
        try:  # per-feed: one bad file must not abort the remaining checks
            if not path.exists():
                stale.append(f"{label}: file missing")
                continue
            newest = pl.read_parquet(path, columns=[tcol])[tcol].max()
            if newest is None:
                stale.append(f"{label}: empty file")
                continue
            if newest.tzinfo is None:
                newest = newest.replace(tzinfo=UTC)
            age_h = (now - newest).total_seconds() / 3600
            if age_h > max_age_h:
                stale.append(f"{label}: {age_h:.0f}h stale")
        except Exception as exc:
            stale.append(f"{label}: freshness check failed ({exc})")

    if failures or stale:
        parts = []
        if failures:
            parts.append("failures: " + " | ".join(failures))
        if stale:
            parts.append("STALE: " + " | ".join(stale))
        telegram.send(("🔴 daily-update " + " ;; ".join(parts))[:1000])
        raise typer.Exit(1)
    telegram.send("✅ daily-update complete: all datasets refreshed and fresh, matrices rebuilt")


@app.command()
def backfill_fng() -> None:
    """Download full Fear & Greed history (2018 -> today)."""
    _setup_logging("backfill")
    from cryptoacademy.data.fng import download_fng

    df = download_fng()
    typer.echo(f"Fear & Greed: {len(df)} days, {df['date'].min()} -> {df['date'].max()}")


@app.command()
def status() -> None:
    """Health overview: collector, feeds, datasets."""
    from cryptoacademy.news.store import NewsStore

    config.ensure_dirs()
    if config.NEWS_DB_PATH.exists():
        with NewsStore(config.NEWS_DB_PATH, read_only=True) as store:
            s = store.stats()
        typer.echo(f"Articles: {s['articles_total']} ({s['articles_backfilled']} backfilled)")
        if s["last_run"]:
            at, ok, failed, new = s["last_run"]
            typer.echo(f"Last run: {at} UTC | feeds ok/failed: {ok}/{failed} | new: {new}")
        typer.echo("By source: " + ", ".join(f"{src}={n}" for src, n in s["by_source"]))
        for name, count, err in s["unhealthy_feeds"]:
            typer.echo(f"  UNHEALTHY feed {name} ({count} consecutive errors): {err}")
    else:
        typer.echo("News DB not created yet (collector has not run).")

    import polars as pl

    for label, pattern in [
        ("klines", "klines/*/*/*.parquet"),
        ("funding", "funding/*/*.parquet"),
        ("open_interest", "open_interest/*/*.parquet"),
        ("sentiment", "sentiment/*.parquet"),
        ("metrics", "metrics/*/*.parquet"),
        ("options", "options/*.parquet"),
        ("attention", "attention/*.parquet"),
        ("positioning", "positioning/*.parquet"),
    ]:
        files = sorted(config.RAW_DIR.glob(pattern))
        for f in files:
            df = pl.scan_parquet(f).select(pl.len()).collect()
            typer.echo(f"{label}: {f.relative_to(config.RAW_DIR)} — {df.item()} rows")


if __name__ == "__main__":
    app()
