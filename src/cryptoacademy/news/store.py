"""Bitemporal, append-only article store.

Every article row records two times:
  - published_at_utc: the publisher/aggregator claim (may be wrong or edited)
  - first_seen_at_utc: when OUR collector first saw it (ground truth we control)

Rows are never updated. If an article's body changes, a new revision is
inserted with a fresh first_seen_at_utc. Backfilled rows carry backfilled=TRUE
and get a larger point-in-time buffer downstream.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url_hash        TEXT NOT NULL,
    revision_no     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    tier            INTEGER NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT,
    body            TEXT,
    body_hash       TEXT NOT NULL,
    published_at_utc TIMESTAMP,
    first_seen_at_utc TIMESTAMP NOT NULL,
    backfilled      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (url_hash, revision_no)
);
CREATE TABLE IF NOT EXISTS feed_state (
    feed_name   TEXT PRIMARY KEY,
    etag        TEXT,
    modified    TEXT,
    last_ok_utc TIMESTAMP,
    last_error  TEXT,
    error_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS run_log (
    run_at_utc  TIMESTAMP NOT NULL,
    feeds_ok    INTEGER,
    feeds_failed INTEGER,
    new_articles INTEGER,
    new_revisions INTEGER,
    duration_s  DOUBLE
);
"""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _naive_utc(dt: datetime | None) -> datetime | None:
    """DuckDB TIMESTAMP columns are naive; without this, tz-aware datetimes get
    silently converted to the session's LOCAL time on insert. All stored
    timestamps are naive-UTC by convention."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


@dataclass
class Article:
    source: str
    tier: int
    url: str
    title: str
    body: str
    published_at_utc: datetime | None
    first_seen_at_utc: datetime
    backfilled: bool = False


class NewsStore:
    def __init__(self, db_path: Path | str, read_only: bool = False) -> None:
        self.conn = duckdb.connect(str(db_path), read_only=read_only)
        if not read_only:
            self.conn.execute(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> NewsStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def upsert(self, art: Article) -> str:
        """Insert an article. Returns 'new', 'revision' or 'unchanged'.

        Append-only: an existing (url_hash, body_hash) match is left untouched;
        a changed body creates revision N+1 with its own first_seen_at.
        """
        url_hash = sha256(art.url)
        body_hash = sha256((art.title or "") + "\n" + (art.body or ""))
        row = self.conn.execute(
            "SELECT max(revision_no), any_value(body_hash ORDER BY revision_no DESC) "
            "FROM articles WHERE url_hash = ?",
            [url_hash],
        ).fetchone()
        max_rev, last_body_hash = (row or (None, None))
        if max_rev is not None and last_body_hash == body_hash:
            return "unchanged"
        revision_no = 0 if max_rev is None else max_rev + 1
        self.conn.execute(
            "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                url_hash,
                revision_no,
                art.source,
                art.tier,
                art.url,
                art.title,
                art.body,
                body_hash,
                _naive_utc(art.published_at_utc),
                _naive_utc(art.first_seen_at_utc),
                art.backfilled,
            ],
        )
        return "new" if revision_no == 0 else "revision"

    def get_feed_state(self, feed_name: str) -> tuple[str | None, str | None]:
        row = self.conn.execute(
            "SELECT etag, modified FROM feed_state WHERE feed_name = ?", [feed_name]
        ).fetchone()
        return (row[0], row[1]) if row else (None, None)

    def set_feed_state(
        self, feed_name: str, etag: str | None, modified: str | None, error: str | None
    ) -> None:
        now = _naive_utc(datetime.now(UTC))
        if error is None:
            self.conn.execute(
                "INSERT INTO feed_state VALUES (?, ?, ?, ?, NULL, 0) "
                "ON CONFLICT (feed_name) DO UPDATE SET etag=excluded.etag, "
                "modified=excluded.modified, last_ok_utc=excluded.last_ok_utc, "
                "last_error=NULL, error_count=0",
                [feed_name, etag, modified, now],
            )
        else:
            self.conn.execute(
                "INSERT INTO feed_state VALUES (?, NULL, NULL, NULL, ?, 1) "
                "ON CONFLICT (feed_name) DO UPDATE SET last_error=excluded.last_error, "
                "error_count=feed_state.error_count + 1",
                [feed_name, error[:500]],
            )

    def log_run(
        self, feeds_ok: int, feeds_failed: int, new: int, revisions: int, duration_s: float
    ) -> None:
        self.conn.execute(
            "INSERT INTO run_log VALUES (?, ?, ?, ?, ?, ?)",
            [_naive_utc(datetime.now(UTC)), feeds_ok, feeds_failed, new, revisions, duration_s],
        )

    def stats(self) -> dict:
        total, backfilled = self.conn.execute(
            "SELECT count(*), coalesce(sum(CASE WHEN backfilled THEN 1 ELSE 0 END), 0) "
            "FROM articles WHERE revision_no = 0"
        ).fetchone()
        last_run = self.conn.execute(
            "SELECT run_at_utc, feeds_ok, feeds_failed, new_articles FROM run_log "
            "ORDER BY run_at_utc DESC LIMIT 1"
        ).fetchone()
        by_source = self.conn.execute(
            "SELECT source, count(*) FROM articles WHERE revision_no = 0 "
            "GROUP BY source ORDER BY 2 DESC"
        ).fetchall()
        unhealthy = self.conn.execute(
            "SELECT feed_name, error_count, last_error FROM feed_state "
            "WHERE error_count >= 3 ORDER BY error_count DESC"
        ).fetchall()
        return {
            "articles_total": total,
            "articles_backfilled": backfilled,
            "last_run": last_run,
            "by_source": by_source,
            "unhealthy_feeds": unhealthy,
        }
