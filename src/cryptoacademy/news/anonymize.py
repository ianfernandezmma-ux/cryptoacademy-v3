"""Entity anonymization against LLM hindsight (Phase 4.3 audit finding).

Measured on this machine (qwen3.6:35b-a3b, 6 famous/fictional headline pairs):
raw scoring leaks ~0.25 mean sentiment toward the KNOWN OUTCOME (sign flips
possible); year-stripping removes ~7% of the gap; gazetteer entity replacement
with role-preserving descriptors removes ~100% while keeping legitimate
salience ("one of the largest asset managers" still scores high severity).

Applied to BOTH backfilled and live articles so the feature distribution is
consistent across eras (live has no hindsight, but anonymized-vs-raw scores
differ systematically).

Generic institutional actors (SEC, Fed, ECB...) are NOT anonymized — they are
recurring generic actors, not outcome-keyed entities.
"""

from __future__ import annotations

import re

# entity -> role-preserving placeholder. Longest patterns first at compile
# time so "FTX US" wins over "FTX".
GAZETTEER: dict[str, str] = {
    # exchanges & their people
    "FTX US": "a major crypto exchange (EXCHANGE_A)",
    "FTX": "a major crypto exchange (EXCHANGE_A)",
    "Alameda Research": "a trading firm affiliated with EXCHANGE_A (FIRM_B)",
    "Alameda": "a trading firm affiliated with EXCHANGE_A (FIRM_B)",
    "Sam Bankman-Fried": "the founder of EXCHANGE_A (PERSON_A)",
    "Bankman-Fried": "the founder of EXCHANGE_A (PERSON_A)",
    "SBF": "the founder of EXCHANGE_A (PERSON_A)",
    "Binance.US": "a leading global crypto exchange (EXCHANGE_B)",
    "Binance": "a leading global crypto exchange (EXCHANGE_B)",
    "Changpeng Zhao": "the CEO of EXCHANGE_B (PERSON_B)",
    " CZ ": " the CEO of EXCHANGE_B (PERSON_B) ",
    "Coinbase": "a large US-listed crypto exchange (EXCHANGE_C)",
    "Brian Armstrong": "the CEO of EXCHANGE_C (PERSON_C)",
    "Kraken": "a major US crypto exchange (EXCHANGE_D)",
    "Bitfinex": "a large offshore crypto exchange (EXCHANGE_E)",
    "OKX": "a large Asian crypto exchange (EXCHANGE_F)",
    "OKEx": "a large Asian crypto exchange (EXCHANGE_F)",
    "Huobi": "a large Asian crypto exchange (EXCHANGE_G)",
    "HTX": "a large Asian crypto exchange (EXCHANGE_G)",
    "Bybit": "a major derivatives crypto exchange (EXCHANGE_H)",
    "KuCoin": "a mid-size crypto exchange (EXCHANGE_I)",
    "Gemini": "a US-regulated crypto exchange (EXCHANGE_J)",
    "Winklevoss": "the founders of EXCHANGE_J (PERSON_D)",
    "Bittrex": "a US crypto exchange (EXCHANGE_K)",
    "Mt. Gox": "a defunct crypto exchange (EXCHANGE_L)",
    "Mt Gox": "a defunct crypto exchange (EXCHANGE_L)",
    "MtGox": "a defunct crypto exchange (EXCHANGE_L)",
    "QuadrigaCX": "a defunct crypto exchange (EXCHANGE_M)",
    # collapsed lenders / funds / stablecoin sagas
    "Terraform Labs": "a blockchain company (COMPANY_A)",
    "TerraUSD": "an algorithmic stablecoin (STABLECOIN_A)",
    "Terra": "a blockchain ecosystem (CHAIN_A)",
    " UST ": " an algorithmic stablecoin (STABLECOIN_A) ",
    "LUNA": "the governance token of CHAIN_A (TOKEN_A)",
    "Do Kwon": "the founder of CHAIN_A (PERSON_E)",
    "Celsius Network": "a crypto lending platform (LENDER_A)",
    "Celsius": "a crypto lending platform (LENDER_A)",
    "Alex Mashinsky": "the CEO of LENDER_A (PERSON_F)",
    "Three Arrows Capital": "a crypto hedge fund (FUND_A)",
    "3AC": "a crypto hedge fund (FUND_A)",
    "Voyager Digital": "a crypto broker (BROKER_A)",
    "Voyager": "a crypto broker (BROKER_A)",
    "BlockFi": "a crypto lender (LENDER_B)",
    "Genesis Global": "a crypto lending desk (LENDER_C)",
    "Grayscale": "a large digital asset manager (FIRM_C)",
    "Digital Currency Group": "a crypto conglomerate (COMPANY_B)",
    "DCG": "a crypto conglomerate (COMPANY_B)",
    "Barry Silbert": "the CEO of COMPANY_B (PERSON_G)",
    "FTT": "the exchange token of EXCHANGE_A (TOKEN_B)",
    # banks of the 2023 crisis
    "Silvergate": "a crypto-focused bank (BANK_A)",
    "Signature Bank": "a crypto-friendly bank (BANK_B)",
    "Silicon Valley Bank": "a tech-focused bank (BANK_C)",
    " SVB ": " a tech-focused bank (BANK_C) ",
    # tradfi giants
    "BlackRock": "one of the largest traditional asset managers (FIRM_A)",
    "Larry Fink": "the CEO of FIRM_A (PERSON_H)",
    "Fidelity": "a major traditional asset manager (FIRM_D)",
    "MicroStrategy": "a listed company with large BTC holdings (COMPANY_C)",
    "Michael Saylor": "the chairman of COMPANY_C (PERSON_I)",
    "Tesla": "a large listed tech company (COMPANY_D)",
    "Elon Musk": "a high-profile tech billionaire (PERSON_J)",
    "Galaxy Digital": "a crypto merchant bank (FIRM_E)",
    "JPMorgan": "a global investment bank (BANK_D)",
    "Goldman Sachs": "a global investment bank (BANK_E)",
    # tokens / chains with event-keyed histories
    "Ripple Labs": "a payments-focused crypto company (COMPANY_E)",
    "Ripple": "a payments-focused crypto company (COMPANY_E)",
    "XRP": "the token of COMPANY_E (TOKEN_C)",
    "Solana": "a high-throughput blockchain (CHAIN_B)",
    " SOL ": " the token of CHAIN_B (TOKEN_D) ",
    "Dogecoin": "a meme cryptocurrency (TOKEN_E)",
    "DOGE": "a meme cryptocurrency (TOKEN_E)",
    "Shiba Inu": "a meme cryptocurrency (TOKEN_F)",
    "Cardano": "a proof-of-stake blockchain (CHAIN_C)",
    "Polygon": "an Ethereum scaling network (CHAIN_D)",
    "Avalanche": "a smart-contract blockchain (CHAIN_E)",
    "Tether": "the largest stablecoin issuer (STABLECOIN_B)",
    "USDT": "the largest stablecoin (STABLECOIN_B)",
    "Circle": "a US stablecoin issuer (STABLECOIN_C)",
    "USDC": "a major US stablecoin (STABLECOIN_C)",
    "Paxos": "a regulated stablecoin issuer (STABLECOIN_D)",
    "BUSD": "an exchange-branded stablecoin (STABLECOIN_D)",
    # people & protocols
    "Vitalik Buterin": "the co-founder of Ethereum (PERSON_K)",
    "Justin Sun": "a controversial crypto founder (PERSON_L)",
    "Tron": "a blockchain founded by PERSON_L (CHAIN_F)",
    "Gary Gensler": "the head of the US securities regulator (OFFICIAL_A)",
    "OpenSea": "a large NFT marketplace (PLATFORM_A)",
    "Axie Infinity": "a play-to-earn game (PLATFORM_B)",
    "Ronin": "a gaming sidechain (CHAIN_G)",
    "Wormhole": "a cross-chain bridge (BRIDGE_A)",
    "Poly Network": "a cross-chain bridge (BRIDGE_B)",
    "Nomad": "a cross-chain bridge (BRIDGE_C)",
    "Curve Finance": "a DeFi exchange protocol (PROTOCOL_A)",
    "Aave": "a DeFi lending protocol (PROTOCOL_B)",
    "Compound": "a DeFi lending protocol (PROTOCOL_C)",
    "MakerDAO": "a DeFi stablecoin protocol (PROTOCOL_D)",
    "Uniswap": "a decentralized exchange (PROTOCOL_E)",
    "SushiSwap": "a decentralized exchange (PROTOCOL_F)",
    "PancakeSwap": "a decentralized exchange (PROTOCOL_G)",
    "Lido": "a liquid staking protocol (PROTOCOL_H)",
    "Prime Trust": "a crypto custodian (CUSTODIAN_A)",
    "Bakkt": "a crypto infrastructure firm (COMPANY_F)",
    "Robinhood": "a retail trading app (BROKER_B)",
    "PayPal": "a global payments company (COMPANY_G)",
    "Visa": "a global card network (COMPANY_H)",
    "Mastercard": "a global card network (COMPANY_I)",
    "El Salvador": "a small country that adopted BTC as legal tender (COUNTRY_A)",
    "Nayib Bukele": "the president of COUNTRY_A (PERSON_M)",
    "Bitmain": "a mining hardware maker (MINER_A)",
    "Marathon Digital": "a listed BTC miner (MINER_B)",
    "Riot Platforms": "a listed BTC miner (MINER_C)",
    "Riot Blockchain": "a listed BTC miner (MINER_C)",
    "Core Scientific": "a listed BTC miner (MINER_D)",
    "Hut 8": "a listed BTC miner (MINER_E)",
}

_DATE_PATTERNS = [
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|"
                r"October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b"), "recently"),
    (re.compile(r"\b(19|20)\d{2}\b"), "recently"),
]

_COMPILED: list[tuple[re.Pattern, str]] | None = None


def _compiled() -> list[tuple[re.Pattern, str]]:
    global _COMPILED
    if _COMPILED is None:
        items = sorted(GAZETTEER.items(), key=lambda kv: -len(kv[0]))
        _COMPILED = [
            (
                re.compile(
                    (re.escape(k) if k != k.strip() else r"\b" + re.escape(k) + r"\b"),
                    re.IGNORECASE,
                ),
                v,
            )
            for k, v in items
        ]
    return _COMPILED


def anonymize(text: str) -> tuple[str, int]:
    """Replace hindsight-prone entities and explicit dates. Returns
    (anonymized_text, n_replacements)."""
    hits = 0
    for pattern, repl in _compiled():
        text, n = pattern.subn(repl, text)
        hits += n
    for pattern, repl in _DATE_PATTERNS:
        text, n = pattern.subn(repl, text)
        hits += n
    return text, hits
