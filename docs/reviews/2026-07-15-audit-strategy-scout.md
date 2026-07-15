# Audit round (pre-B3) — Strategy scout report (B2.5 hypothesis list)

Agent: strategy-research scout. Date: 2026-07-15. Literature only, no
backtests on project data. Output = the hypothesis list for a future
registered round ("B2.5"). Registry impact: +11 trials → N 229→240 (E[max SR]
null benchmark rises ~0.5% — effectively free at these variant caps).

## Accept/reject sweep

ACCEPT: multi-speed trend ladders (rank 1); ETHBTC relative-momentum tilt
(rank 2); continuous funding de-risk tilt (rank 3); trailing-exit/re-entry
upgrade (rank 4); MVRV slow valuation gate, 1 variant (rank 5, cautious);
DVOL stress gate, narrow variant only (rank 6).

REJECT: generic vol-regime timing (already vol-targeted; Cederburg et al.
JFE 2020 — vol-managed doesn't replicate OOS); ADX/breakout-quality filters
(folklore, continuous-parameter overfitting surface); ETF flow momentum
(2.5y of data, one regime; flows confirm rather than predict — watchlist
2027); Fear&Greed contrarian (dip-buying in disguise, already cut; weak
sources); BTC/ETH rebalancing premium (subsumed by daily vol-targeted
rebalancing); risk-managed momentum (subsumed).

## The 7 hypotheses (11 trials)

**H1 — Multi-speed Donchian ladder (top pick).** Mean of K binary Donchian
signals at staggered lookbacks; position = ensemble × vol-target weight.
Evidence: Zarattini/Pagani/Barbon 2025 (SSRN 5209907) — BTC Donchian ensemble
5–360d NET Sharpe 1.58, alpha 14%/yr; arXiv 2009.12155 corroborates
multi-speed robustness. ~0.8 correlated to champion → judge as champion
REPLACEMENT (robustness upgrade attacking exactly the PBO-0.52 weakness),
not combo member. Variants (2): {10,20,40,80} and {20,60,120}, half-exits,
NO SMA200 gate (slow rungs replace it — fix in pre-registration).

**H2 — ETHBTC relative-momentum risk-weight tilt.** ETHBTC vs its SMA →
tilt 50/50 to 65/35 toward the stronger asset (only reallocates what the
trend system already holds). Few trades/yr, trivially cost-safe, orthogonal
axis (relative not directional). Risk: ~2 ETH cycles in-sample; may
degenerate to "always BTC". Variants (2): SMA100 65/35; 90d total-return
sign 70/30.

**H3 — Continuous funding de-risk tilt.** Multiplier 1 → 0.5 as 30d mean
funding rises from its trailing-1y 85th to 99th percentile (crowded-longs
crash mechanism: BIS WP 1087 Crypto Carry; SSRN 4666425). Rebalance band
|Δm|>0.1 → handful of partial trades/yr. Slightly negative correlation to
trend where it matters (trims late uptrends). Fixes the cut S4's
rare-event flaw via continuous mapping. Variants (2): 85→99 to 0.5;
80→95 to 0.25.

**H4 — Trailing-exit upgrade.** Same entry+gate; exit = highest-close-since-
entry − 3×ATR20 (Chandelier), re-entry only on fresh 20d high. Evidence:
exit-rule/stop-loss-on-momentum literature (Han–Zhou–Zhu; ATR trails
standard). ~0.95 correlated → champion refinement only. Variants (2): 3×ATR20;
2.5×ATR20 + 5d re-entry lockout.

**H5 — MVRV slow valuation gate (1 variant).** Multiplier 1.0 while BTC
MVRV-z < 3, taper to 0.5 at z=6 (never below 0.5, never blocks entries);
BTC's gate applied to both assets. Evidence: RIBAF 2026 3-cycle backtest;
every cycle top coincided with extreme z. PIT: Coin Metrics community
CapMVRVCur free for BTC/ETH, approximately-PIT (start stamping daily pulls).
Judge on drawdown/left-tail, not Sharpe. HIGH overfit risk (N≈3 cycles).

**H6 — DVOL stress gate (1 variant).** Halve position while DVOL > trailing-1y
95th pct OR VRP (DVOL − 30d RV) < −10 vol pts, until normalized 5 days.
Weakest accepted; redundant with H3 — pre-register that at most one of
H3/H5/H6 composes into production (priority order H3 > H5 > H6).

**H7 — (stretch) EWMAC 4-speed ladder** {4/16, 8/32, 16/64, 32/128}: tests
the ladder concept in the second family; drop first if frugality wins.
Variant (1).

## Pre-committed composition rules (freeze before evaluating)
H1 competes for the trend-core slot vs the current champion; H2 overlays
whichever core wins; at most TWO of {H3, H5, H6} compose (order H3>H5>H6);
H4 evaluated only against the champion baseline.

## Cross-cutting caveats
Overlay stacking (H3/H5/H6 all de-risk euphoria — naive composition
triple-penalizes 2021-style melt-ups); ETH sample poverty (~2 cycles) flags
H2/H5; PIT notes: funding/DVOL clean re-downloads, Coin Metrics ~PIT, ETF
flows rejected partly for vintage shortness.

Sources: SSRN 5209907 (Catching Crypto Trends); arXiv 2009.12155; BIS WP
1087; SSRN 4666425; RIBAF 2026 on-chain cycles; Coin Metrics docs; Moreira–
Muir SSRN 2659431 vs Cederburg JFE 2020; FRL 2025 risk-managed momentum;
Quantpedia (BTC trend revisit, rebalancing premium, multi-timeframe);
Deribit DVOL methodology; trailing-stop literature (SSRN 2126476, arXiv
1701.03960).
