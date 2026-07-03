"""Structured news scoring with the local LLM (Ollama).

Validated rules for this GPU/setup (benchmarked 2026-07-03):
- ALWAYS `think: false` for scoring — with thinking enabled the answer goes to
  the thinking channel and `response` comes back empty.
- temperature 0, JSON schema enforced via Ollama's `format` (grammar-level),
  then re-validated with the same Pydantic model; up to 2 retries.
- One article per request; throughput comes from sequential speed (~93 tok/s),
  not batching in the prompt (attention dilution degrades per-item accuracy).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

import httpx
from pydantic import BaseModel, Field, ValidationError

from cryptoacademy import config

log = logging.getLogger(__name__)

OLLAMA = "http://localhost:11434"
SCORER_MODEL = "qwen3.6:35b-a3b"
EMBED_MODEL = "qwen3-embedding:4b"


class EventType(StrEnum):
    etf_flow = "etf_flow"
    regulation = "regulation"
    hack_exploit = "hack_exploit"
    tech_upgrade = "tech_upgrade"
    macro = "macro"
    exchange = "exchange"
    adoption = "adoption"
    legal = "legal"
    other = "other"


class ArticleScore(BaseModel):
    """One article's structured extraction. `is_price_report` separates news
    that CAUSE moves from news that merely REPORT them (endogeneity control —
    only exogenous sentiment is a candidate for alpha)."""

    assets: list[str] = Field(description="Affected assets: BTC, ETH, or OTHER")
    sentiment: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    event_type: EventType
    severity: int = Field(ge=1, le=5, description="Market impact: 1 minor .. 5 systemic")
    is_price_report: bool = Field(
        description="True if the article mainly reports a price move that already happened"
    )


SYSTEM_PROMPT = (
    "You are a financial news analyst scoring crypto news for a trading model. "
    "Score ONLY from the text given. sentiment: -1 very bearish .. +1 very bullish "
    "for the tagged assets; 0 if neutral/unclear. severity: 1 = routine, "
    "3 = notable, 5 = systemic (exchange collapse, major regulation). "
    "is_price_report=true if the article mainly describes a price move that "
    "already happened ('surges past', 'plunges', 'hits all-time high')."
)


def _generate(prompt: str, schema: dict, model: str = SCORER_MODEL) -> str:
    resp = httpx.post(
        f"{OLLAMA}/api/generate",
        json={
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 8192},
        },
        timeout=300.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def score_article(title: str, body: str, anonymize_dates: bool = False) -> ArticleScore | None:
    """Score one article; 2 retries on schema violations, then dead-letter (None).

    anonymize_dates: for BACKFILLED articles — strips explicit dates so the
    LLM's knowledge of what happened later biases the score less (LLM lookahead,
    arXiv:2309.17322)."""
    text = f"{title}\n\n{(body or '')[:6000]}"
    if anonymize_dates:
        import re

        text = re.sub(r"\b(19|20)\d{2}\b", "YEAR", text)
    schema = ArticleScore.model_json_schema()
    for attempt in range(3):
        try:
            raw = _generate(f"Score this article:\n\n{text}", schema)
            return ArticleScore.model_validate_json(raw)
        except (ValidationError, httpx.HTTPError, KeyError) as exc:
            log.warning("score attempt %d failed: %s", attempt + 1, str(exc)[:200])
    return None


def embed(texts: list[str]) -> list[list[float]]:
    resp = httpx.post(
        f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": texts}, timeout=300.0
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


SCORES_SCHEMA = """
CREATE TABLE IF NOT EXISTS article_scores (
    url_hash    TEXT NOT NULL,
    revision_no INTEGER NOT NULL,
    scored_at_utc TIMESTAMP NOT NULL,
    model       TEXT NOT NULL,
    assets      TEXT,
    sentiment   DOUBLE,
    confidence  DOUBLE,
    event_type  TEXT,
    severity    INTEGER,
    is_price_report BOOLEAN,
    duplicate_of TEXT,
    PRIMARY KEY (url_hash, revision_no)
);
"""

DEDUP_THRESHOLD = 0.87  # validated: same story ES/EN ~0.80+, unrelated ~0.39


def score_pending(limit: int = 500) -> dict:
    """Score unscored articles from the news store.

    Cascade: embed title+lede -> mark near-duplicates of already-scored recent
    articles (skip LLM) -> LLM-score the survivors. Idempotent by PK.
    """
    import duckdb

    conn = duckdb.connect(str(config.NEWS_DB_PATH))
    conn.execute(SCORES_SCHEMA)
    pending = conn.execute(
        """
        SELECT a.url_hash, a.revision_no, a.title, a.body, a.backfilled
        FROM articles a
        LEFT JOIN article_scores s
          ON a.url_hash = s.url_hash AND a.revision_no = s.revision_no
        WHERE s.url_hash IS NULL
        ORDER BY a.first_seen_at_utc
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    if not pending:
        conn.close()
        return {"scored": 0, "duplicates": 0, "failed": 0}

    # Recent scored articles form the dedup reference set (7-day window scale).
    recent = conn.execute(
        """
        SELECT a.url_hash, a.title, coalesce(substr(a.body, 1, 500), '')
        FROM articles a JOIN article_scores s ON a.url_hash = s.url_hash
        WHERE s.duplicate_of IS NULL
        ORDER BY a.first_seen_at_utc DESC LIMIT 300
        """
    ).fetchall()
    ref_vecs = embed([f"{t}\n{b}" for _, t, b in recent]) if recent else []
    ref_hashes = [h for h, _, _ in recent]

    scored = dupes = failed = 0
    now = datetime.now(UTC).replace(tzinfo=None)
    for url_hash, rev, title, body, backfilled in pending:
        vec = embed([f"{title}\n{(body or '')[:500]}"])[0]
        dup_of = None
        for i, rv in enumerate(ref_vecs):
            if cosine(vec, rv) >= DEDUP_THRESHOLD:
                dup_of = ref_hashes[i]
                break
        if dup_of:
            conn.execute(
                "INSERT OR IGNORE INTO article_scores VALUES "
                "(?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,?)",
                [url_hash, rev, now, "dedup", dup_of],
            )
            dupes += 1
            continue
        result = score_article(title or "", body or "", anonymize_dates=bool(backfilled))
        if result is None:
            failed += 1
            continue
        conn.execute(
            "INSERT OR IGNORE INTO article_scores VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
            [
                url_hash, rev, now, SCORER_MODEL,
                ",".join(result.assets), result.sentiment, result.confidence,
                result.event_type.value, result.severity, result.is_price_report,
            ],
        )
        ref_vecs.append(vec)
        ref_hashes.append(url_hash)
        scored += 1
    conn.close()
    return {"scored": scored, "duplicates": dupes, "failed": failed}
