"""THE test. If this ever fails, stop everything else.

A synthetic article stamped 1 second after the decision cutoff must never be
selected; one stamped early enough (cutoff minus buffer) must be. This encodes
the v2 bug (24h sentiment aggregates joined to the midnight bar) so it can
never come back.
"""

from datetime import UTC, datetime, timedelta

from cryptoacademy.config import BACKFILL_BUFFER, LIVE_BUFFER
from cryptoacademy.news.pit import select_usable, usable_at

DECISION = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)


def _row(published: datetime, first_seen: datetime | None = None, backfilled: bool = False):
    return {
        "published_at_utc": published,
        "first_seen_at_utc": first_seen or published,
        "backfilled": backfilled,
    }


def test_article_one_second_after_cutoff_is_excluded():
    late = _row(DECISION - LIVE_BUFFER + timedelta(seconds=1))
    assert select_usable([late], DECISION) == []


def test_article_at_cutoff_is_included():
    ok = _row(DECISION - LIVE_BUFFER - timedelta(seconds=1))
    assert select_usable([ok], DECISION) == [ok]


def test_v2_bug_same_day_news_never_visible_at_midnight():
    """The v2 failure mode: news published during day D visible at 00:00 of D."""
    same_day_news = [
        _row(DECISION + timedelta(hours=h)) for h in (1, 6, 12, 23)
    ]
    assert select_usable(same_day_news, DECISION) == []


def test_backfilled_rows_get_larger_buffer():
    published = DECISION - LIVE_BUFFER - timedelta(seconds=1)
    live = _row(published)
    backfilled = _row(published, first_seen=datetime(2026, 7, 2, tzinfo=UTC), backfilled=True)
    assert select_usable([live], DECISION) == [live]
    assert select_usable([backfilled], DECISION) == []  # needs BACKFILL_BUFFER
    ua = usable_at(published, backfilled["first_seen_at_utc"], True)
    assert ua == published + BACKFILL_BUFFER


def test_future_publisher_claim_is_distrusted():
    """A publisher-claimed time later than our sighting dominates (conservative)."""
    seen = DECISION - timedelta(hours=2)
    claimed_future = DECISION + timedelta(hours=1)
    ua = usable_at(claimed_future, seen, backfilled=False)
    assert ua > DECISION


def test_unknown_publish_time_falls_back_to_first_seen():
    seen = DECISION - LIVE_BUFFER - timedelta(minutes=1)
    ua = usable_at(None, seen, backfilled=False)
    assert ua == seen + LIVE_BUFFER


def test_window_lower_bound():
    old = _row(DECISION - timedelta(hours=30))
    assert select_usable([old], DECISION, window=timedelta(hours=24)) == []
