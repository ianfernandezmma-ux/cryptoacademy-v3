# ruff: noqa: E501 - the piloted prompt block is intentionally verbatim
"""Daily LLM risk-regime scorer over GDELT slug pseudo-headlines (Phase 4.3).

Piloted 2026-07-10 on the COVID window (27 days, shuffled order, no dates
shown): crypto_stress hit 3 / risk_appetite -2 only in the Mar 9-16 2020
crisis window, fired 3 days BEFORE Black Thursday, and nailed Mar 12 at
confidence 0.95. January stayed at 0/+1. Design notes that matter:

- Selection MUST split crypto vs macro headlines (15+7 by n_themes desc,
  Jaccard>0.55 slug dedup). Naive top-k drowned Black Thursday in general
  COVID coverage and missed it entirely.
- URL slugs are the headline source for the GDELT era (92% usable; years
  stripped for anti-hindsight; model never sees dates).
- Known residual biases (handle downstream): mild risk-off lean on quiet
  days, occasional stress=2 on regulatory-noise-only days, 'panic' narrative
  over-used under macro fear. Consume ra/cs/ms as ordinal features with a
  3-day median smoothing; narrative is secondary.

PIT convention: regime(D) is computed from headlines GDELT saw during day D,
so it becomes usable at D+1 00:00 UTC — matrix assembly must join it to
decision day D+1 (same shift discipline as daily bars).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime
from urllib.parse import unquote, urlparse

import httpx
import polars as pl

from cryptoacademy import config

log = logging.getLogger(__name__)

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "qwen3.6:35b-a3b"
PROMPT_VERSION = "v3"
K_CRYPTO, K_MACRO = 15, 7
REGIME_PATH = config.DATA_DIR / "features" / "regime_daily.parquet"

# ---------------------------------------------------------------- slugs

STOP_SEGMENTS = {
    "news", "article", "articles", "story", "stories", "post", "posts", "blog",
    "en", "us", "markets", "business", "crypto", "cryptocurrency", "bitcoin-news",
    "altcoin-news", "ethereum-news", "press-releases", "opinion", "analysis",
    "price-analysis", "index.html", "amp", "wp", "content",
}
_DATE_SEG = re.compile(r"^(19|20)\d{2}$|^\d{1,2}$")
_HEX = re.compile(r"^[0-9a-f]{6,}$", re.I)
_NUMID = re.compile(r"^\d{4,}$")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def extract_slug(url: str) -> str | None:
    """Best path segment of a URL as a pseudo-headline (years stripped)."""
    try:
        parsed = urlparse(url if "://" in url else "http://" + url)
    except Exception:
        return None
    path = unquote(parsed.path)
    path = re.sub(r"\.(html?|php|aspx?|shtml|cms|ece|amp)$", "", path, flags=re.I)
    best, best_score = None, 0
    for seg in (s for s in path.split("/") if s):
        seg = re.sub(r"^\d+\.", "", seg)
        if seg.lower() in STOP_SEGMENTS or _DATE_SEG.match(seg.lower()):
            continue
        toks = [t for t in re.split(r"[-_]+", seg) if t]
        while toks and (_NUMID.match(toks[-1]) or _HEX.match(toks[-1])):
            toks.pop()
        while toks and (_NUMID.match(toks[0]) or _HEX.match(toks[0])):
            toks.pop(0)
        score = len([t for t in toks if re.search(r"[a-zA-Z]{2,}", t)])
        if score > best_score:
            best_score, best = score, toks
    if not best or best_score < 3:
        return None
    text = _YEAR.sub("", " ".join(best))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text if len(text.split()) >= 3 else None


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


CRYPTO_KW = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|crypto|cryptocurrenc\w*|blockchain|altcoin|token|"
    r"defi|stablecoin|binance|coinbase|bitmex|bitfinex|kraken|okex|huobi|tether|usdt|"
    r"xrp|ripple|litecoin|ltc|bch|satoshi|halving|hodl|miner|mining|libra|cbdc|"
    r"digital currency|digital asset)\b", re.I,
)


def headlines_for_day(day: date) -> tuple[list[str], list[str]]:
    """(crypto, macro) slugs: top by n_themes desc, Jaccard-deduped.
    The crypto/macro split is load-bearing — see module docstring."""
    f = config.RAW_DIR / "gdelt" / f"{day:%Y}" / f"gkg_{day:%Y%m%d}.parquet"
    if not f.exists():
        return [], []
    df = (
        pl.read_parquet(f, columns=["url", "n_themes"])
        .unique(subset=["url"])
        .sort("n_themes", descending=True)
    )
    crypto: list[str] = []
    macro: list[str] = []
    seen: list[set] = []
    for row in df.iter_rows(named=True):
        slug = extract_slug(row["url"])
        if not slug:
            continue
        toks = set(slug.split())
        if any(_jaccard(toks, t) > 0.55 for t in seen):
            continue
        if CRYPTO_KW.search(slug) and len(crypto) < K_CRYPTO:
            seen.append(toks)
            crypto.append(slug)
        elif not CRYPTO_KW.search(slug) and len(macro) < K_MACRO:
            seen.append(toks)
            macro.append(slug)
        if len(crypto) >= K_CRYPTO and len(macro) >= K_MACRO:
            break
    return crypto, macro


# ---------------------------------------------------------------- prompt

SYSTEM_PROMPT = """You are a crypto-market risk-regime analyst. You receive the day's top news headlines (recovered from URL slugs, so casing and punctuation are lost), split into CRYPTO HEADLINES (crypto-focused coverage) and GENERAL MARKET HEADLINES (broader macro/news context). Score the day's market regime strictly from these headlines. You do NOT know the date; judge only the content.

Attribution rules: crypto_stress must be driven by the CRYPTO HEADLINES (crypto price action, exchanges, hacks of crypto infrastructure); macro_stress by the GENERAL MARKET HEADLINES plus any macro spillover visible in crypto coverage. Routine ransomware/scam/fraud-prosecution stories that merely involve bitcoin (ransom payments, criminal cases, individual scams) are background noise (at most crypto_stress 1), not market stress — crypto news flow ALWAYS contains some of these. crypto_stress 2+ requires evidence that the crypto MARKET itself is under strain: falling prices, liquidations, exchange outages under load, or enforcement that hits a major exchange or market segment. risk_appetite is driven primarily by the price-action tone of the crypto headlines: if rally/bullish/breakout headlines outnumber sell-off headlines, risk_appetite should be positive even when general news is fearful.

Output JSON only, with these fields:

risk_appetite (integer -2..+2) — market-wide willingness to hold risk, as reflected in the news flow:
 -2 = panic / forced deleveraging. Example: "exchange insolvency or forced liquidation cascade underway; bitcoin crashes 30%+ in a day; global markets halt trading".
 -1 = risk-off. Example: "sustained sell-off headlines, bitcoin loses key support, safe-haven rotation, fear-driven coverage".
  0 = neutral / mixed. Example: "routine price analysis, mixed up-and-down coverage, product launches, no directional fear or greed".
 +1 = risk-on. Example: "rally headlines, bitcoin breaks resistance, institutional adoption momentum, constructive tone".
 +2 = euphoria. Example: "ETF-inflow euphoria, alt rotation, bitcoin surges past round-number milestones, retail FOMO everywhere".

crypto_stress (integer 0..3) — stress specific to crypto markets/infrastructure:
  0 = none. Example: "quiet news flow: partnerships, product launches, ordinary price commentary".
  1 = mild. Example: "moderate price weakness, isolated scam or small hack stories, minor regulatory friction".
  2 = elevated. Example: "sharp market-wide sell-off (~15-30%), major exchange outage or exchange hack, enforcement action against a top exchange".
  3 = severe. Example: "exchange insolvency / forced liquidation cascade underway, bitcoin down 30%+ intraday, systemic contagion fears".

macro_stress (integer 0..3) — broader macro / traditional-market stress visible in the headlines:
  0 = none. Example: "no macro distress stories; business as usual".
  1 = mild. Example: "soft economic data, isolated recession warnings, trade-tension murmurs".
  2 = elevated. Example: "equity market sell-offs, escalating epidemic or geopolitical shock, emergency rate-cut speculation".
  3 = severe. Example: "global market crash, circuit breakers triggered, crisis-level central-bank interventions, pandemic panic".

dominant_narrative (string) — the single most dominant theme, one of:
  "regulation" (SEC/government rules, bans, lawsuits), "adoption" (institutions, merchants, banks embracing crypto),
  "hack_exploit" (hacks, scams, ransomware, thefts), "etf_flow" (ETF approvals/flows/filings),
  "macro_rates" (central banks, rates, inflation, macro data), "exchange_solvency" (exchange failures, withdrawals halted, insolvency),
  "tech" (protocol upgrades, launches, mining, infrastructure), "euphoria" (rallies, price milestones, FOMO),
  "panic" (crashes, liquidations, fear-driven selling), "quiet" (no dominant theme, routine coverage).

confidence (number 0..1) — how confident you are in this assessment given headline quality and quantity. If the input notes a LOW-NEWS DAY, cap confidence at 0.5.

rationale (string) — at most 20 words explaining the scores.

Be conservative: reserve the extreme scores (-2/+2, stress 3) for days whose headlines clearly describe crisis or euphoria actually underway, not mere predictions or retrospectives."""

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_appetite": {"type": "integer", "minimum": -2, "maximum": 2},
        "crypto_stress": {"type": "integer", "minimum": 0, "maximum": 3},
        "macro_stress": {"type": "integer", "minimum": 0, "maximum": 3},
        "dominant_narrative": {"type": "string", "enum": [
            "regulation", "adoption", "hack_exploit", "etf_flow", "macro_rates",
            "exchange_solvency", "tech", "euphoria", "panic", "quiet"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string"},
    },
    "required": ["risk_appetite", "crypto_stress", "macro_stress",
                 "dominant_narrative", "confidence", "rationale"],
}


def _user_prompt(crypto: list[str], macro: list[str]) -> str:
    n = len(crypto) + len(macro)
    c_lines = "\n".join(f"- {h}" for h in crypto) or "(none)"
    m_lines = "\n".join(f"- {h}" for h in macro) or "(none)"
    note = ""
    if n < 5:
        note = "\n\nNOTE: LOW-NEWS DAY — fewer than 5 headlines available. Cap confidence at 0.5.\n"
    return (
        f"Top headlines of one UTC day ({n} headlines):\n\n"
        f"CRYPTO HEADLINES:\n{c_lines}\n\n"
        f"GENERAL MARKET HEADLINES:\n{m_lines}{note}\n\n"
        f"Score this day's regime. JSON only."
    )


def classify_day(client: httpx.Client, crypto: list[str], macro: list[str]) -> dict:
    resp = client.post(
        OLLAMA,
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(crypto, macro)},
            ],
            "stream": False,
            "think": False,
            "format": JSON_SCHEMA,
            "options": {"temperature": 0, "num_ctx": 8192},
        },
        timeout=600,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


# ---------------------------------------------------------------- backfill

def backfill_regime(max_days: int = 5000) -> dict:
    """Score every harvested GDELT day that has no regime row yet. Resumable
    (keyed by date); appends to regime_daily.parquet atomically."""
    have: set[date] = set()
    existing: pl.DataFrame | None = None
    if REGIME_PATH.exists():
        existing = pl.read_parquet(REGIME_PATH)
        have = set(existing["date"].to_list())
    gdelt_days = sorted(
        datetime.strptime(f.stem.removeprefix("gkg_"), "%Y%m%d").date()
        for f in (config.RAW_DIR / "gdelt").glob("*/gkg_*.parquet")
    )
    todo = [d for d in gdelt_days if d not in have][:max_days]
    if not todo:
        return {"scored": 0, "skipped_empty": 0, "total_rows": len(have)}

    rows: list[dict] = []
    skipped = 0
    scored_at = datetime.now(UTC).replace(tzinfo=None)
    with httpx.Client() as client:
        for day in todo:
            crypto, macro = headlines_for_day(day)
            if len(crypto) + len(macro) == 0:
                skipped += 1
                continue
            try:
                result = classify_day(client, crypto, macro)
            except Exception as exc:  # one bad day must not kill the run
                log.warning("regime %s failed: %s", day, exc)
                continue
            rows.append(
                {
                    "date": day,
                    "risk_appetite": int(result["risk_appetite"]),
                    "crypto_stress": int(result["crypto_stress"]),
                    "macro_stress": int(result["macro_stress"]),
                    "dominant_narrative": result["dominant_narrative"],
                    "confidence": float(result["confidence"]),
                    "rationale": result["rationale"],
                    "n_headlines": len(crypto) + len(macro),
                    "scored_at_utc": scored_at,
                    "model": f"{MODEL}|{PROMPT_VERSION}",
                }
            )
            if len(rows) % 50 == 0:
                log.info("regime backfill: %d/%d days scored", len(rows), len(todo))
    new = pl.DataFrame(rows)
    out = (
        pl.concat([existing, new], how="diagonal_relaxed") if existing is not None else new
    ).sort("date").unique(subset=["date"], keep="last")
    REGIME_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGIME_PATH.with_suffix(".tmp")
    out.write_parquet(tmp)
    tmp.replace(REGIME_PATH)
    log.info("regime backfill: +%d rows (%d skipped empty), total %d", len(rows), skipped,
             len(out))
    return {"scored": len(rows), "skipped_empty": skipped, "total_rows": len(out)}


def smoothed_regime_features(regime: pl.DataFrame) -> pl.DataFrame:
    """3-day median smoothing (per pilot recommendation) + day-over-day delta.
    Keyed for matrix assembly: usable at decision day D+1."""
    r = regime.sort("date")
    out = r.select(
        (pl.col("date").cast(pl.Datetime(time_zone="UTC")) + pl.duration(days=1)).alias(
            "decision_day"
        ),
        pl.col("risk_appetite").rolling_median(3, min_samples=1).alias("regime_risk_appetite"),
        pl.col("crypto_stress").rolling_median(3, min_samples=1).alias("regime_crypto_stress"),
        pl.col("macro_stress").rolling_median(3, min_samples=1).alias("regime_macro_stress"),
        pl.col("risk_appetite").diff().alias("regime_ra_delta"),
        pl.col("confidence").alias("regime_confidence"),
    )
    return out
