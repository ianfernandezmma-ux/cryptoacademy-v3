# ruff: noqa: E501 - the calibrated prompt block is intentionally verbatim
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


# V2, calibrated live 2026-07-10 on a 40-article gold set: event-type accuracy
# 55% -> 92.5%, regulation precision 0.30 -> 1.00. Anchored class definitions
# + tie-breakers + magnitude anchoring. Do not edit casually — changes must be
# re-measured against the gold set (scratchpad run_eval.py / gold.json).
PROMPT_VERSION = "v2"
SYSTEM_PROMPT = """You are a financial news analyst scoring crypto news for a trading model. Score ONLY from the text given.

EVENT TYPE — choose the single label that matches the PRIMARY concrete event in the article (what actually happened, not what the article speculates might happen):

- etf_flow: inflows/outflows, launches, approvals, or rebalances of CRYPTO ETFs/ETPs/index funds. Flows in non-crypto funds are macro or other.
- regulation: a GOVERNMENT body, regulator, or legislature makes, proposes, delays, or enforces RULES for crypto markets (SEC/CFTC/MiCA rulemaking, licensing regimes, bans, CBDC legislation, official crypto-policy statements or appointments). STRICT TEST: if no government or regulator is taking or proposing rule-related action on crypto in the text, it is NOT regulation. Company product launches, partnerships, fundraises, analyst opinions, and price moves are NEVER regulation.
- legal: lawsuits, prosecutions, arrests, court rulings, settlements, seizures, or law-enforcement investigations involving specific parties. Courts and prosecutors -> legal; rule-writing agencies -> regulation.
- hack_exploit: protocol/bridge/exchange hacks, exploits, rug pulls, theft totals, laundering of stolen crypto, vulnerability incidents.
- tech_upgrade: crypto protocol/product technology: network upgrades, forks, new chains/L2s, new DeFi products or features, technical milestones. Non-crypto tech news (AI model releases, chip launches) is other.
- exchange: crypto exchange/broker/derivatives-venue operations: listings/delistings, outages, new trading products, expansions, exchange business moves.
- macro: economy-wide or geopolitical forces: central banks, rates, inflation, FX, oil/energy, war and conflict, sovereign reserve moves, TradFi market-wide stress or flows.
- adoption: real, concrete uptake of crypto by companies, institutions, or the public: corporate BTC/ETH treasury purchases, merchant/payment integrations, institutional platform usage, country-level adoption, usage-volume milestones.
- other: everything else — analyst/strategist/CEO opinions and predictions, price analysis and market commentary, single non-crypto company news (stocks, AI labs, chipmakers), sports/entertainment stories with only a thin or speculative crypto angle, non-crypto fundraises and IPOs.

Tie-breakers:
- An opinion, forecast, or analyst note with no concrete event -> other. Never regulation.
- Story about a non-crypto company or sport with a bolted-on crypto mention -> other.
- Government action on NON-crypto sectors (oil laws, tariffs, general politics) -> macro, not regulation.
- The crime/theft itself -> hack_exploit; the investigation/prosecution of it -> legal.

sentiment (-1..+1 for the tagged assets): reserve |s| >= 0.7 for clearly market-moving news (major hack, spot-ETF approval, sweeping ban, systemic failure). Use 0.3-0.6 for meaningful but ordinary good/bad news. Use |s| < 0.3 for routine, incremental, or mixed news, and 0 when neutral, unclear, or not really about crypto.

severity: 1 = routine/no crypto-market impact (sports, product notes, opinions), 2 = minor, 3 = notable sector news, 4 = major (large hack, big regulatory shift, sharp macro shock), 5 = systemic (exchange collapse, sweeping regulation, war-level shock). Stories with only a thin crypto angle are 1-2, never 3+.

is_price_report: true if the article mainly reports a price move or market positioning that already happened ('surges past', 'plunges', 'hits all-time high', support/resistance analysis, open-interest or flow recaps).

Examples of correct outputs:

Article: "SEC delays decision on spot Solana ETF, opens public comment period"
{"assets": ["OTHER"], "sentiment": -0.3, "confidence": 0.9, "event_type": "regulation", "severity": 3, "is_price_report": false}

Article: "eToro invests in onchain derivatives platform to expand crypto offering"
{"assets": ["OTHER"], "sentiment": 0.3, "confidence": 0.8, "event_type": "exchange", "severity": 2, "is_price_report": false}

Article: "Bitwise strategist says the selloff signals a cycle bottom for Bitcoin"
{"assets": ["BTC"], "sentiment": 0.3, "confidence": 0.7, "event_type": "other", "severity": 1, "is_price_report": false}

Article: "Federal judge rules Coinbase must face securities class action"
{"assets": ["OTHER"], "sentiment": -0.4, "confidence": 0.9, "event_type": "legal", "severity": 3, "is_price_report": false}

Article: "Ethereum's Pectra upgrade goes live on mainnet, adding account abstraction"
{"assets": ["ETH"], "sentiment": 0.5, "confidence": 0.9, "event_type": "tech_upgrade", "severity": 3, "is_price_report": false}

Article: "Fed holds rates steady, signals two cuts this year; risk assets rally"
{"assets": ["BTC", "ETH"], "sentiment": 0.4, "confidence": 0.8, "event_type": "macro", "severity": 3, "is_price_report": false}

Article: "Bitcoin plunges below $60K as $1.2B in longs liquidated"
{"assets": ["BTC"], "sentiment": -0.6, "confidence": 0.9, "event_type": "other", "severity": 3, "is_price_report": true}

Article: "Nvidia unveils next-gen AI chips at GTC, stock hits record high"
{"assets": ["OTHER"], "sentiment": 0.0, "confidence": 0.8, "event_type": "other", "severity": 1, "is_price_report": false}

Article: "Siemens adds Bitcoin to corporate treasury with $150M purchase"
{"assets": ["BTC"], "sentiment": 0.5, "confidence": 0.9, "event_type": "adoption", "severity": 3, "is_price_report": false}

Article: "Curve pool drained for $8M via oracle manipulation; attacker bridges funds"
{"assets": ["ETH", "OTHER"], "sentiment": -0.7, "confidence": 0.9, "event_type": "hack_exploit", "severity": 3, "is_price_report": false}"""


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

    ALL articles (live and backfilled) pass through gazetteer entity
    anonymization: the measured hindsight gap on famous events is ~0.25
    sentiment raw and 0.00 anonymized, and applying it to the live stream too
    keeps the feature distribution consistent across eras. The
    anonymize_dates parameter is retained for API compatibility but date
    neutralization now always happens inside anonymize()."""
    from cryptoacademy.news.anonymize import anonymize

    text, _ = anonymize(f"{title}\n\n{(body or '')[:6000]}")
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

    Locking discipline: DuckDB is single-writer and the collector runs every
    10 minutes, so we hold the connection only for the initial read and one
    final batch write — never across LLM calls.
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
    recent = conn.execute(
        """
        SELECT a.url_hash, a.title, coalesce(substr(a.body, 1, 500), '')
        FROM articles a JOIN article_scores s ON a.url_hash = s.url_hash
        WHERE s.duplicate_of IS NULL
        ORDER BY a.first_seen_at_utc DESC LIMIT 300
        """
    ).fetchall()
    conn.close()  # release the write lock BEFORE the slow LLM loop
    if not pending:
        return {"scored": 0, "duplicates": 0, "failed": 0}

    ref_vecs = embed([f"{t}\n{b}" for _, t, b in recent]) if recent else []
    ref_hashes = [h for h, _, _ in recent]

    results: list[list] = []
    scored = dupes = failed = 0
    for url_hash, rev, title, body, backfilled in pending:
        # stamp per article, not per batch: a long run that straddles midnight
        # must not backdate post-midnight scores into the prior decision day
        now = datetime.now(UTC).replace(tzinfo=None)
        vec = embed([f"{title}\n{(body or '')[:500]}"])[0]
        dup_of = None
        for i, rv in enumerate(ref_vecs):
            if cosine(vec, rv) >= DEDUP_THRESHOLD:
                dup_of = ref_hashes[i]
                break
        if dup_of:
            results.append(
                [url_hash, rev, now, "dedup", None, None, None, None, None, None, dup_of]
            )
            dupes += 1
            continue
        result = score_article(title or "", body or "", anonymize_dates=bool(backfilled))
        if result is None:
            # dead-letter: without a sentinel row the article re-enters the
            # FIFO head every hour (3 LLM attempts each) and >= `limit`
            # permanent failures wedge the scorer silently. llm_era_daily
            # excludes model='failed'.
            results.append(
                [url_hash, rev, now, "failed", None, None, None, None, None, None, None]
            )
            failed += 1
            continue
        results.append(
            [
                url_hash, rev, now, f"{SCORER_MODEL}|{PROMPT_VERSION}",
                ",".join(result.assets), result.sentiment, result.confidence,
                result.event_type.value, result.severity, result.is_price_report, None,
            ]
        )
        ref_vecs.append(vec)
        ref_hashes.append(url_hash)
        scored += 1

    # Single short write transaction, with retries in case the collector holds
    # the lock at this exact moment (30x20s matches worst observed hold times).
    for attempt in range(30):
        try:
            conn = duckdb.connect(str(config.NEWS_DB_PATH))
            conn.executemany(
                "INSERT OR IGNORE INTO article_scores VALUES (?,?,?,?,?,?,?,?,?,?,?)", results
            )
            conn.close()
            break
        except duckdb.IOException:
            if attempt == 29:
                raise
            import time

            time.sleep(20)
    return {"scored": scored, "duplicates": dupes, "failed": failed}
