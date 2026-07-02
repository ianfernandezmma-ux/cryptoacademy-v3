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
    ]:
        files = sorted(config.RAW_DIR.glob(pattern))
        for f in files:
            df = pl.scan_parquet(f).select(pl.len()).collect()
            typer.echo(f"{label}: {f.relative_to(config.RAW_DIR)} — {df.item()} rows")


if __name__ == "__main__":
    app()
