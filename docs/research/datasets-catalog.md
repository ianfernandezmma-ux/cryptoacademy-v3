# Catálogo de fuentes de datos gratuitas (research 2026-07-03)

Resumen operativo del deep research. U = utilidad (evidencia predictiva × backfill × limpieza point-in-time).

## Shortlist priorizada

| # | Fuente | Features | Backfill | Auth/límites | PIT | U |
|---|---|---|---|---|---|---|
| 1 | data.binance.vision futures `metrics` + `fundingRate` + `premiumIndexKlines` | OI, long/short (top traders y global), taker buy/sell, funding, basis | **2020-09** (funding 2019) | ninguna | inmutable ★★★★★ | 5 |
| 2 | data.binance.vision klines (columnas taker-buy) + aggTrades | order flow con signo / CVD | 2017 spot / 2019 fut | ninguna | ★★★★★ | 5 |
| 3 | Coin Metrics Community API / github.com/coinmetrics/data | MVRV, realized cap, direcciones activas, fees, hashrate, NVT | BTC 2010, ETH 2015 | sin key, 10 req/6s | T+1 ★★★★ | 5 |
| 4 | FRED + **ALFRED** (vintages) | WALCL, RRP, TGA, yields reales, DXY, HY OAS | décadas | key gratis, 120/min | vintages ★★★★★ | 4 |
| 5 | Deribit API pública — DVOL + funding | IV 30d, variance risk premium | DVOL 2021-03 | ninguna | ★★★★★ | 4 |
| 6 | Coinalyze API | OI/funding/**liquidaciones** cross-exchange | ~2019-20 | key gratis, 40/min | ruptura estructural liq. 2021 | 4 |
| 7 | Farside (farside.co.uk/btc, /eth) | flujos diarios ETF spot | 2024-01 | ninguna (HTML) | se restatea T+2 → lag 2 días o snapshot propio | 4 |
| 8 | DeFiLlama stablecoins API | supply USDT/USDC, mcap stablecoins | ~2020 | ninguna | ★★★★ | 4 |
| 9 | Wikipedia Pageviews API | atención (páginas Bitcoin/Ethereum) | 2015-07, horario | ninguna | **inmutable — el proxy de atención más limpio** | 4 |
| 10 | CFTC COT (publicreporting.cftc.gov, dataset TFF `gpe5-46if`) | posicionamiento CME por clase de trader | BTC 2018, ETH 2021 | ninguna | datos de martes publicados VIERNES 15:30 ET → embargo 3 días | 3 |
| 11 | Calendarios FOMC + CPI (federalreserve.gov, bls.gov) | dummies de evento, horas-hasta-evento | completo | ninguna | conocido ex-ante ★★★★★ | 4 |
| 12 | Blockchain.com charts API | hashrate, dificultad, miner revenue | 2009 | ninguna | ★★★★ | 4 |
| 13 | bitcoin-data.com (BGeometrics) | SOPR, NUPL, MVRV-Z, realized price, CDD gratis | 2009, solo BTC | key gratis, **15 req/día** | ★★★★ | 4 |
| 14 | alternative.me F&G | sentimiento compuesto | 2018-02 | ninguna | cambios de metodología silenciosos | 3 |
| 15 | Bybit funding + Bitfinex margin longs/shorts + yfinance | funding cross-venue, posicionamiento margin, TradFi | 2013-2019 | ninguna | ★★★ | 3 |

## Claves operativas

- **`metrics` de Binance Vision** (5-min, desde 2020-09): `https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-YYYY-MM-DD.zip` — OI en contratos y notional, ratios long/short de top traders (cuentas y posiciones), ratio global, taker buy/sell. La única historia honesta de posicionamiento (la REST API solo guarda 30 días).
- **Taker-buy en klines**: las columnas taker_buy_base/quote de los klines dan order-flow imbalance hasta 2017 sin tocar datos tick — ya las estamos guardando.
- **DVOL Deribit**: `GET /api/v2/public/get_volatility_index_data?currency=BTC&resolution=1D` desde 2021-03, sin auth.
- **Wikipedia pageviews**: `GET https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Bitcoin/daily/20200101/...` — inmutable, sin key (poner User-Agent).
- **COT**: usar timestamp de PUBLICACIÓN (viernes), no el del dato (martes).
- **ALFRED para macro**: M2/WALCL se revisan; usar `realtime_start/realtime_end` para vintages tal como se publicaron.

## Advertencias PIT transversales

1. Todo lo basado en **etiquetas de direcciones de exchange** (reservas, netflows, whale-to-exchange) se reescribe retroactivamente → solo archivo forward.
2. **Farside/SoSoValue**: las filas se rellenan durante 24-48h → lag de 2 días o snapshots propios diarios.
3. **Liquidaciones**: ruptura estructural en 2021 (Binance limitó su websocket) → indicador de missingness.
4. **Google Trends**: renormalizado por ventana y muestreado → NO point-in-time; evitar o archivar forward.
5. **DeFiLlama TVL**: protocolos añadidos retroactivamente; usar solo como feature de régimen.
6. **Yahoo futuros continuos**: el método de roll afecta al basis; calcular basis propio y manejar fechas de roll.
7. Snapshots imposibles de backfillear honestamente (cadena de opciones Deribit, app-store ranks, reservas): **empezar a archivarlos forward YA**.
