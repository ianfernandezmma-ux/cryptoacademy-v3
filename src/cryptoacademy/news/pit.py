"""Point-in-time correctness rules — the single most important module.

Rule: a piece of information is usable for a decision at time T only if
    usable_at(row) <= T
where
    usable_at = max(published_at, first_seen_at) + buffer
and the buffer is LIVE_BUFFER for live-collected rows and BACKFILL_BUFFER for
backfilled rows (whose timestamps are publisher claims we could not verify).

Every feature-building query MUST go through select_usable(); nothing may
filter articles by calendar date.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cryptoacademy.config import BACKFILL_BUFFER, LIVE_BUFFER


def usable_at(
    published_at_utc: datetime | None,
    first_seen_at_utc: datetime,
    backfilled: bool,
) -> datetime:
    """Earliest decision time at which this row may be used."""
    base = _as_utc(first_seen_at_utc)
    if published_at_utc is not None:
        published_at_utc = _as_utc(published_at_utc)
    if published_at_utc is not None and published_at_utc > base:
        # A publisher claim in the future of our sighting is suspicious;
        # be conservative and take the later of the two.
        base = published_at_utc
    if backfilled and published_at_utc is not None:
        # For backfilled rows first_seen_at is our scrape time (useless, years
        # later) — the claim is all we have, padded by the large buffer.
        base = published_at_utc
        return _as_utc(base) + BACKFILL_BUFFER
    return _as_utc(base) + LIVE_BUFFER


def select_usable(
    rows: list[dict],
    decision_time: datetime,
    window: timedelta = timedelta(hours=24),
) -> list[dict]:
    """Filter article rows to those usable at decision_time within a window.

    Each row needs keys: published_at_utc, first_seen_at_utc, backfilled.
    """
    decision_time = _as_utc(decision_time)
    out = []
    for row in rows:
        ua = usable_at(row["published_at_utc"], row["first_seen_at_utc"], row["backfilled"])
        if ua <= decision_time and ua > decision_time - window:
            out.append(row)
    return out


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
