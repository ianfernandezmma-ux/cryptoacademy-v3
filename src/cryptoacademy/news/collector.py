"""Forward RSS collector. Runs every 10 minutes via Windows Task Scheduler.

Design notes:
- Conditional GETs (etag/last-modified) so unchanged feeds cost one cheap request.
- Full text extracted with trafilatura from the article URL; if extraction
  fails we still store the RSS title/summary (a timestamped headline is
  valuable on its own).
- first_seen_at_utc is stamped once per run, before any network fetch, so all
  articles in a run share a conservative sighting time.
- A feed failing is recorded in feed_state and never aborts the run.
"""

from __future__ import annotations

import logging
import time
from calendar import timegm
from datetime import UTC, datetime

import feedparser
import httpx
import trafilatura

from cryptoacademy import config
from cryptoacademy.news.store import Article, NewsStore

log = logging.getLogger(__name__)

MAX_BODY_FETCHES_PER_FEED = 25  # politeness cap per run
FETCH_DELAY_S = 1.0


def parse_entry_time(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.fromtimestamp(timegm(parsed), tz=UTC)
    return None  # unknown publish time: usable_at falls back to first_seen_at


def fetch_body(client: httpx.Client, url: str) -> str | None:
    try:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return trafilatura.extract(resp.text, include_comments=False, favor_precision=True)
    except Exception as exc:  # any single article failure is non-fatal
        log.debug("body fetch failed for %s: %s", url, exc)
        return None


def collect_once(store: NewsStore, feeds: list[dict]) -> dict:
    started = time.monotonic()
    feeds_ok = feeds_failed = new = revisions = 0

    with httpx.Client(
        headers={"User-Agent": config.USER_AGENT}, timeout=config.HTTP_TIMEOUT
    ) as client:
        for feed in feeds:
            name, url, tier = feed["name"], feed["url"], feed.get("tier", 3)
            etag, modified = store.get_feed_state(name)
            try:
                parsed = feedparser.parse(
                    url, etag=etag, modified=modified, agent=config.USER_AGENT
                )
                if parsed.get("bozo") and not parsed.entries and parsed.get("status") != 304:
                    raise RuntimeError(str(parsed.get("bozo_exception", "unparseable feed")))
                store.set_feed_state(
                    name, parsed.get("etag"), parsed.get("modified"), error=None
                )
                feeds_ok += 1
                fetches = 0
                for entry in parsed.entries:
                    link = entry.get("link")
                    if not link:
                        continue
                    body = None
                    if fetches < MAX_BODY_FETCHES_PER_FEED:
                        body = fetch_body(client, link)
                        fetches += 1
                        time.sleep(FETCH_DELAY_S)
                    result = store.upsert(
                        Article(
                            source=name,
                            tier=tier,
                            url=link,
                            title=entry.get("title", ""),
                            body=body or entry.get("summary", "") or "",
                            published_at_utc=parse_entry_time(entry),
                            # stamped per article at possession time — stamping
                            # the run start would claim we saw late-fetched
                            # articles earlier than we did (audit M-3)
                            first_seen_at_utc=datetime.now(UTC),
                            backfilled=False,
                        )
                    )
                    if result == "new":
                        new += 1
                    elif result == "revision":
                        revisions += 1
            except Exception as exc:  # one feed must not kill the run
                log.warning("feed %s failed: %s", name, exc)
                store.set_feed_state(name, None, None, error=str(exc))
                feeds_failed += 1

    duration = time.monotonic() - started
    store.log_run(feeds_ok, feeds_failed, new, revisions, duration)
    return {
        "feeds_ok": feeds_ok,
        "feeds_failed": feeds_failed,
        "new_articles": new,
        "new_revisions": revisions,
        "duration_s": round(duration, 1),
    }
