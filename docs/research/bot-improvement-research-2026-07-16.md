# Bot improvement research — strategy classes, frameworks, communities (2026-07-16)

**Question.** For a solo retail systematic trader running a Python paper-trading bot on
Binance (currently long-only spot BTC/ETH, Donchian-20 trend following with volatility
targeting, ~12.6%/yr simulated, maxDD 10.5%, strict anti-leakage and pre-registered-trial
discipline): what evidence-backed strategy classes, open-source bot frameworks,
communities, and educational resources offer the highest-probability path to a genuinely
more profitable bot? Scope open: futures strategies (funding carry, basis), market
making, and top-N altcoin expansion all in scope.

**Method.** Deep-research harness: 5 parallel search angles → 21 sources fetched →
103 falsifiable claims extracted → top 12 claims adversarially verified (single skeptical
verifier per claim, default-refute-if-uncertain) → synthesis. 11 claims confirmed,
1 refuted. Run stats: 40 agents, 5 angles, 21 sources (6 primary academic), 1 URL dupe,
8 budget-dropped low-relevance sources.

**Honesty note on method.** Verification was single-vote (1-0) per claim after a
mid-run budget cut, not the usual 3-vote panel. Confidence ratings below therefore lean
on primary-source verbatim verification and source independence rather than
multi-verifier agreement. Retail "best crypto bot" content is dominated by affiliate
marketing and outright scams (see Workstream D); everything below that survived
verification comes from academic/institutional primary sources.

---

## Executive summary

Two strategy classes have genuinely strong, primary-source support:

1. **Perpetual-futures funding-rate carry** (delta-hedged long spot / short perp) —
   documented by a BIS working paper (~7%/yr average gross carry 2019–2024, spikes >40%)
   and a CMU study (16–22%/yr gross in-sample; driven almost entirely by the funding
   rate, which on Binance is **known one period in advance** — an unusually clean,
   PIT-compatible signal). BUT: all headline numbers are gross-of-cost, the trade has
   severe liquidation risk, and the edge has structurally compressed since the Jan-2024
   spot-ETF launch. Realistic net expectation at retail size: low-to-mid single digits
   p.a. with episodic spikes.
2. **Trend following / momentum** — validated on two independent axes: time-series
   (NBER/RFS: BTC daily and weekly momentum) and cross-sectional (JFQA CTREND factor,
   3,000+ coins, robust to known factors and transaction costs, persists in liquid
   coins). This validates the bot's existing trend core and supports expanding to a
   **cross-sectional momentum sleeve over top-N liquid alts**.

No claims about bot frameworks, practitioner communities, or YouTube channels
(workstreams B–D) survived adversarial verification — the actionable conclusions rest on
workstream A. The recommendation is to **layer** new sleeves alongside the validated
trend core, not replace it, each as a pre-registered trial with net-of-cost acceptance
criteria fixed in advance.

---

## Workstream A — What works in crypto (verified findings)

### A1. Funding-rate carry is the best-documented gross return source — HIGH confidence

Average annualized carry across exchanges ~7% p.a. Apr-2019→Jul-2024, spikes >40% (BIS).
A delta-hedged long-BTC-spot / short-Binance-perp trade earned 21.84%/yr (Tether-settled,
Sharpe 11.5) and 16.74%/yr (coin-settled, Sharpe 6.4) in-sample 2020-08→2022-06 (CMU,
Table 3, N=2036). The return is driven almost entirely by the perpetual funding rate
(median 0.01%/8h ≈ 11%/yr), not basis convergence, and under Binance's timing convention
the funding component is **known one period in advance**.

- BIS WP 1087 (Schmeling, Schrimpf & Todorov; also Management Science):
  https://www.bis.org/publ/work1087.pdf
- CMU (Christin, Routledge, Soska, Zetlin-Jones):
  https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf
- Verified verbatim against both PDFs. Vote: unanimous (3 merged claims, each 1-0).

### A2. All carry headline numbers are GROSS and the trade is not risk-free — HIGH confidence

CMU explicitly abstracts from transaction costs, margin requirements, and liquidation
fees — Sharpes of 7–13 are not realizable net figures. BIS: a 10% rise in standardized
carry predicts short-futures liquidations equal to **22% of total open interest** within
the following month; "even patient carry traders are exposed to significant risk of
forced liquidations due to the existence of margin frictions." High carry predicts
crashes. Any trial must model funding-net-of-fees, maintenance margin, and liquidation
buffers explicitly. Vote: unanimous (2 merged claims).

### A3. The carry premium is regime-dependent and has structurally compressed — HIGH confidence

The Jan-2024 spot-bitcoin-ETF launch reduced carry ~3pp across exchanges (36% of mean)
and ~5pp on CME (97% of mean) — verified verbatim in BIS, with independent 2026 market
corroboration. The 2021-07-23 Binance leverage cut (125x→50x) coincided with BTC
Tether-carry falling 33.03%→10.22%/yr (ETH 44.60%→9.75%) (CMU Table 11; the leverage
interpretation is the authors' hypothesis, confounded with the 2021/2022 regime change —
not causal identification). The premium behaves as longs' willingness to pay for
leverage access. **Historical basis-trade backtests materially overstate today's edge**;
episodic spikes (>20% p.a. in Nov 2024) persist. A carry strategy today is a
conditional/episodic harvest, not a constant yield. Vote: unanimous (2 merged claims).

### A4. Trend/momentum is evidence-backed on two independent axes — HIGH confidence

(a) **Time-series**: statistically significant daily and weekly BTC momentum 2011–2018
(one-SD daily return → +0.33% next day; top weekly quintile 11.22%/wk Sharpe 0.45 vs
bottom 2.60%/wk Sharpe 0.19; weaker for ETH; gross returns) — Liu & Tsyvinski, NBER
w24877 / RFS 2021: https://www.nber.org/system/files/working_papers/w24877/w24877.pdf
(b) **Cross-sectional**: the machine-learning CTREND trend factor (price+volume across
horizons, 3,000+ coins, 2015–2022) reliably predicts the cross-section of crypto
returns, is not subsumed by known factors, and is robust across subperiods, market
states, and ~55,000 alternative research designs — Fieberg, Liedtke, Poddig, Walker &
Zaremba, JFQA 60(7) Nov-2025:
https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178

Caveats: NBER sample ends 2018 (post-publication attenuation likely); CTREND ends 2022
with no independent post-publication replication yet; CTREND authors concede it "could
be another anomaly in disguise, such as momentum." Vote: unanimous (3 merged claims).

### A5. CTREND survives costs and persists in liquid coins — MEDIUM confidence

Verbatim from the JFQA abstract: the effect "survives the impact of transaction costs
and persists in big and liquid coins" — the strongest available evidence that a
cross-sectional trend strategy restricted to top-N liquid pairs is net-of-cost viable at
retail size. Downgraded to medium: single source; academic cost estimates, not actual
Binance retail fee/slippage schedules; and CTREND is a **long-short** factor — the short
leg often drives crypto anomaly profits and is largely infeasible for retail in small
alts. The transferable hypothesis is a **long-only top-quantile momentum sleeve over
top-N liquid Binance pairs**, to be tested as its own pre-registered trial, not assumed
from the paper.

### Refuted in verification (do not use)

- **Attention proxies** (Google searches, Twitter counts forecasting BTC returns 1–6
  weeks ahead, from the same NBER paper): refuted 0-1 — did not survive skeptical
  review. Do not carry attention-based signals forward on the strength of this paper.

---

## Workstreams B–D — frameworks, communities, videos: NO verified findings

**This is itself a result.** Sources were fetched for freqtrade/NostalgiaForInfinity,
NautilusTrader, framework comparisons, Rob Carver's blog, Ernie Chan's backtesting-
pitfalls notes, and regulator scam advisories — but none of their profitability or
consensus claims survived (or reached) adversarial verification within budget. Anything
below is **unverified leads, editorial judgment only**:

- **NostalgiaForInfinity** (flagship freqtrade community strategy, 3.3k stars) makes
  **no explicit profitability claims** in its README — telling, for the most prominent
  "community bot" artifact: https://github.com/iterativv/NostalgiaForInfinity
- **NautilusTrader's** architecture lesson worth studying: one shared kernel so the
  exact code path runs backtest and live — the same discipline our matrix/assembly
  design applies to data: https://nautilustrader.io/docs/latest/concepts/architecture/
- **Rob Carver** (ex-AHL, sells nothing but books) and **Ernie Chan's**
  backtesting-pitfalls notes remain the most credible practitioner starting points:
  https://qoppac.blogspot.com/p/systematic-trading-start-here.html ·
  https://epchan.com/img/links/Backtesting-and-its-Pitfalls.pdf
- **Scam anatomy (regulator-documented)**: NASAA advisory on "investment education
  foundations" + proprietary AI-bot scams; CFTC digital-asset red flags. Red flags:
  guaranteed/fixed returns, "AI bot" with unauditable track record, affiliate links to
  the platform being reviewed, martingale/grid marketed as riskless, pressure to move to
  private groups: https://www.nasaa.org/75050/ ·
  https://www.cftc.gov/sites/default/files/2022-10/DigitalAssetRedFlags.pdf
- One SSRN preprint claiming 3x-leveraged delta-neutral carry at 16%/yr Sharpe 6.1 with
  <2% maxDD, and an arXiv Hyperliquid backtest claiming 18–25% APY with ~0 drawdown,
  were fetched but NOT verified — treat as too-good-to-be-true until independently
  replicated on our own funding data.
- A practitioner cost-math example (pruviq blog, unverified but arithmetic checks out):
  at 0.01–0.02%/8h funding on $10k notional, taker fees on 4 legs + slippage make the
  first day of a carry round-trip a net loss — **entry/exit costs dominate at retail
  size**; the trade only clears when expected cumulative funding over the holding
  period beats round-trip costs with margin.

A dedicated source-critical pass on framework architecture/risk practices (docs and
code, not community anecdotes) is listed as an open question.

---

## Workstream E — Ranked shortlist of pre-registerable hypotheses

**H1 — Funding-rate carry sleeve (highest priority).** Long spot BTC/ETH + short
Binance USDT-perp, entered conditionally when net expected funding (after taker/maker
fees, both legs, entry+exit) clears a pre-registered threshold; funding known one period
ahead makes the signal cleanly PIT. Requirements: futures account (paper first),
funding-rate history (already collected since 2020), explicit margin/liquidation
modeling with buffers sized against BIS liquidation-cascade evidence. Realistic net
expectation: **low-to-mid single digits p.a. with episodic spikes** — NOT the academic
16–22%. First step costs nothing: measure 2025–2026 net-of-cost carry on our own
collected funding history and count how often it clears the hurdle.

**H2 — Cross-sectional momentum over top-N liquid alts.** Long-only top-quantile trend
sleeve extending the existing Donchian/vol-target machinery to top-20/50 liquid Binance
pairs. Requirements: top-N klines (Binance Vision, same pipeline), survivorship-safe
universe-construction rules (point-in-time listings/liquidity ranks). Evidence:
net-of-cost per CTREND (JFQA), but long-short → long-only transfer and post-2022
out-of-sample survival must be established in our own pre-registered trial.

**H3 — Keep and refine the existing time-series trend core (lower priority).** The
literature supports the class; nothing verified suggests replacing it. The validated
12.6%/yr / maxDD 10.5% VT20 core remains the base layer the sleeves diversify.

All three go through the registry discipline: register intent → freeze acceptance
criteria (net-of-cost) → evaluate → report honestly, including nulls.

## Open questions

1. Actual 2025–2026 net-of-cost funding carry on Binance at our fee tier, measured from
   our own funding history — how often does it clear a fees+slippage hurdle?
2. Does cross-sectional momentum survive post-2022 out-of-sample, and does a long-only
   top-quantile version over top-20/50 Binance pairs beat the 2-asset trend core?
3. Which framework architecture/risk practices are worth adopting (needs a dedicated
   source-critical pass — no community claims survived verification)?
4. What margin buffer / sizing rule makes a retail carry sleeve robust to the
   BIS-documented liquidation cascades, validated against historical Binance funding
   spikes in our own data?

---

*Produced by a deep-research workflow (40 agents) on 2026-07-16; verification
single-vote after a mid-run budget reduction. Full run journal in the session workflow
transcript.*
