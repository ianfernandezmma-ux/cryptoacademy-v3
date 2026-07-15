# Audit round (pre-B3) — Return-improvement levers report

Agent: portfolio-construction critic. Date: 2026-07-15. No backtests run;
analysis of logged B2 results + literature. Every proposal = pre-registrable
hypothesis; adoption resets the paper clock per the B4-freeze rule.

**One-line diagnosis:** the strategy is not weak — it earns ~102%/yr on
deployed capital (5.9% ÷ 5.8% avg exposure). The portfolio is tiny because
sizing runs at ~one-tenth Kelly and 94% of capital earns zero. The two honest
levers: pay idle cash a T-bill-like yield, and raise the vol target within
the half-Kelly speed limit. Everything else is second-order or bait.

## Exposure decomposition (from logged numbers)
Weight when on, both assets (VT_5050 avg): 21.7% × gate-green fraction ~55% ×
in-Donchian-position fraction of green days ~48% = 5.8% avg exposure.
Conditional deployed vol ≈ 11.4% ≈ gross 0.22 × asset vol ~0.50 — sizing layer
is internally consistent.

## Kelly arithmetic
Carver half-Kelly with HONEST expected SR 0.5–0.7 (never the realized 1.01)
supports a 25–35% vol budget; the book realizes 5.9% ≈ 1/5 of half-Kelly.
Scaling table (linear until caps bind):

| VT | E[net ret] | E[vol] | E[maxDD] | Binding |
|---|---|---|---|---|
| 12% (now) | 5.9% | 5.9% | 6.8% | nothing (gross-on ≈ 0.27) |
| 20% | ~9.6% | ~9.8% | ~11.3% | per-asset cap only at the σ-floor |
| 24% | ~11.4% | ~11.6% | ~13.4% | cap binds when σ≤24%; gross ~0.53 |
| 30% | ~13.5–14% | ~14% | ~16–17% | **hard-kill 0.20 now inside plausible DD** |
| ~36% struct. max | ~19% if SR 1; ~12% at SR 0.6 | ~20% | ~23%+ | gross cap 0.8 — the no-leverage ceiling |

**Rails interaction:** any VT increase must be co-registered with a rails
review (kill at −20% was calibrated to 6.8% backtest DD; live DDs run
1.5–2× backtest).

## Cash drag — the biggest, cheapest lever
~94% idle at 0%. Credible July-2026 rates: tokenized T-bills 3.5–4.8% APY
(BENJI/USDY/BUIDL/OUSG); Binance Earn base tiers 1.5–4% (promos are
small-tranche marketing; lending ≠ risk-free). Honest simulation: conservative
floating T-bill proxy (~4% APR) on the un-deployed fraction with a 1-day
redeployment lag. Expected: **+3.8%/yr at ~zero added DD** — more than the
strategy's entire net-over-cash return. Must switch Sharpe reporting to
excess-of-cash consistently. Never simulate promo APYs.

## Breadth (honest delivery of the Carver answer)
2 assets at ρ≈0.8 + 1 family → IDM ≈ 1.1. COMBO already measured the
rule-diversification ceiling: 0.96 vs 1.01 — nothing there. Real breadth
options: +3 spot majors (IDM → ~1.3, +15–25% Sharpe, but alt slippage and
survivorship discipline required — pre-register the universe by a mechanical
past-dated liquidity rule); carry tilts unavailable in spot ("no", plainly);
orthogonal signal = the lab's news/on-chain ML (unproven, low confidence);
shorts/futures = where the other half of the trend premium lives — a v2
MANDATE decision, not a lever. Within spot long-only BTC+ETH, the breadth
ceiling is essentially reached.

## Design choices costing return
- 20% vol floor caps weight at 0.30 in calm uptrends (where trend earns):
  test floor 15% (+0.3–0.8%/yr, gap-risk cost — keep a floor).
- Gated-asset budget: when one asset is red, its 0.5 risk budget idles;
  reallocating to the live asset ≈ +0.5–1.0%/yr, more concentration —
  cleanest signal-side lever.
- 50/50 vs ERC at ρ0.8: ~nothing, skip. Gross cap 0.8: never binds at VT12.
  Buffer: nothing to harvest. Long-only clip: the 2022 −1.14 column is the
  quantified price of the spot mandate (short trend was positive in 2022);
  fix = futures = mandate change.

## What NOT to do (v2-disease list)
Loosen the gate because 2026H1 was flat; re-search Donchian N (PBO 0.52 says
ranking is a coin flip); size off SR 1.01; leverage; stack families selected
on backtest; re-open 24h; simulate promo yields; raise VT without touching
rails.

## Menu for the owner (honest-SR column uses 0.6; cash yield 4% on idle)

| Option | Backtest-implied | Honest-SR-implied | E[maxDD] | Kill-rail headroom |
|---|---|---|---|---|
| Status quo | 5.9% | ~3.5% | 6.8% | 2.9× |
| + cash yield | ~9.7% | ~7.3% | ~6.8% | 2.9× |
| VT 20% + yield | ~13.3% | ~9.5% | ~11.3% | 1.8× |
| VT 24% + yield | ~15% | ~10.5% | ~13.4% | 1.5× — rails re-registered |
| VT 30% + yield | ~17% | ~11.5% | ~16–17% | ~1.2× — do not |

Capital-vs-effort: at $10k even improved ≈ $1.3–1.5k/yr (infrastructure +
learning, not income); ~$50k–100k at an honest ~10% is where "worth the
operational effort" begins. Realistic owner expectation: **8–11%/yr at
low-teens maxDD** — a bond-plus product with crypto-crash immunity. 30%+/yr
is not available from this mandate at any defensible risk setting.

## Lever table (register in this order)
1. Cash yield (High confidence, +3.5–4%/yr, ~0 DD) → 2. VT 20% first step
(High, mechanical; risk is the SR estimate) → 3. Gated-asset reallocation
(Medium, +0.5–1%/yr). Then: floor 15% (Medium-small), universe expansion
(Medium-Low, needs new cost model). Examined-and-rejected (~0): buffer,
ERC weights, gross cap at VT12, speed diversification (COMBO answered it).

Sources: Binance Earn announcements; graphdex/eco.com yield comparisons;
rwa.xyz tokenized treasuries; Carver Systematic Trading (7circles summary,
qoppac Kelly posts); Grinold & Kahn fundamental law.
