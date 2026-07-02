"""Append-only store semantics: revisions never overwrite, timestamps immutable."""

from datetime import UTC, datetime

from cryptoacademy.news.store import Article, NewsStore

T0 = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def _article(body: str, first_seen: datetime) -> Article:
    return Article(
        source="test",
        tier=1,
        url="https://example.com/a",
        title="BTC news",
        body=body,
        published_at_utc=T0,
        first_seen_at_utc=first_seen,
    )


def test_same_body_is_not_reinserted(tmp_path):
    with NewsStore(tmp_path / "n.duckdb") as store:
        assert store.upsert(_article("hello", T0)) == "new"
        assert store.upsert(_article("hello", T1)) == "unchanged"
        assert store.stats()["articles_total"] == 1


def test_edited_body_creates_revision_preserving_original(tmp_path):
    with NewsStore(tmp_path / "n.duckdb") as store:
        store.upsert(_article("original", T0))
        assert store.upsert(_article("edited after the fact", T1)) == "revision"
        rows = store.conn.execute(
            "SELECT revision_no, body, first_seen_at_utc FROM articles ORDER BY revision_no"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][1] == "original"
        assert rows[0][2].replace(tzinfo=UTC) == T0  # original sighting untouched
        assert rows[1][2].replace(tzinfo=UTC) == T1  # revision has its own sighting


def test_distinct_urls_are_distinct_articles(tmp_path):
    with NewsStore(tmp_path / "n.duckdb") as store:
        a = _article("x", T0)
        b = _article("x", T0)
        b.url = "https://example.com/b"
        store.upsert(a)
        assert store.upsert(b) == "new"
        assert store.stats()["articles_total"] == 2
