# Preprocessing y feature engineering — mejores prácticas (research 2026-07-03)

Resumen operativo para la Fase 3. Objetivo: el mejor feed de datos posible para LightGBM/XGBoost (primarios) y PatchTST/N-HiTS (challengers).

## Decisiones de diseño

1. **Sin escalado para GBDTs** (invariantes a transformaciones monótonas); las transformaciones son por estabilidad estadística, no por el optimizador. Para DL: **RevIN** (instance normalization reversible) + StandardScaler por fold para exógenas.
2. **Nunca niveles de precio crudos** a los GBDTs (los árboles no extrapolan fuera del soporte de entrenamiento). Sí: retornos log multi-horizonte, ratios precio/MA, z-scores, distancia-a-máximos. Fractional differentiation: baja prioridad — 2-3 features FFD (d≈0.3-0.5, tuneado con ADF solo en fold de train) y que la selección decida.
3. **Z-scores y ranks con ventana RODANTE** (90d/365d), no expanding (2017 es irrelevante en 2026). Siempre causales: media/std de t−w..t−1 (shift 1). Dar al modelo el valor crudo Y su rank rodante donde el nivel importa (ej. funding: crudo + rank 90d).
4. **Un modelo pooled BTC+ETH** con categórica `asset_id` y features normalizadas por activo en serie temporal — duplica la muestra efectiva (crítico con n≈2000-5000). Cross-sectional con 2 activos no tiene sentido; la info cross-asset va como features de spread: momentum del ratio ETH/BTC, diferencial de retornos, beta rodante ETH-sobre-BTC.
5. **Volatilidad**: estimadores de rango baten a GARCH en crypto (Kristoufek 2025). Usar Parkinson + Garman-Klass + realized vol desde barras intradía (la mejor medida diaria: tenemos 1h). EWMA (λ≈0.94, half-life 10-30d) para vol-scaling de labels y posiciones. Features HAR-style: RV_1d, RV_7d, RV_30d. Skip GARCH.
6. **Barras**: time bars como spine (1d + 4h); CUSUM event sampling como capa de eventos para triple-barrier (umbral h ≈ vol diaria EWMA, dinámico). Dollar bars: opcional intradía desde aggTrades de data.binance.vision (umbral recalibrado mensualmente con media RODANTE LAGGED).
7. **Missing data**: GBDTs — pasar NaN nativo (NO imputar) + indicadores binarios de missingness sistemático (funding pre-2020, liquidaciones pre-2021, macro en finde). DL — ffill + indicador. Joins mixtos: `merge_asof(direction='backward')` sobre available-at + cap de staleness (ej. DXY máx 4 días) + columna `feature_age_hours` (¡la edad es señal!). Dummy `tradfi_market_open` para findes.
8. **Outliers**: winsorizar features a percentiles rodantes 1/99 causales. Target regresión: clip(r/σ, ±5). NUNCA borrar filas de crashes (las más informativas). Nunca clipear retornos en el backtest — solo en el target de entrenamiento.
9. **Régimen como features** (no modelos por régimen): buckets de percentil de vol (252d), filtro de tendencia (precio vs MA200, signo pendiente), bucket drawdown-desde-ATH, régimen de correlación BTC-SPX. HMM opcional pero debe fitearse dentro de cada fold y decodificarse causal (filtered, no smoothed); los buckets de percentil dan el 80% del beneficio con 0% de riesgo de leakage.
10. **Selección de features**: dedup por clusters de correlación (|ρ|>0.95) → SHAP por fold bajo purged CV, quedarse con las de importancia positiva Y ESTABLE entre folds/años → confirmar con clustered MDA. Presupuesto: ~n/10 a n/20 → **30-80 features finales** de un pool de 150-300. LightGBM: depth 3-5, feature_fraction 0.3-0.6, min_child_samples 50-200.
11. **Targets**: (a) primario: clasificación ternaria vol-scaled — label = sign(r) si |r/σ√h| > 0.5, si no "flat"; (b) auxiliar: regresión clip(r_{t+1}/σ_t, ±5) (doble uso como señal de sizing); triple-barrier sobre eventos CUSUM cuando entre el meta-labeling. Multi-horizonte: modelos separados 1d/3d/7d, no target mezclado.
12. **Pesos de muestra**: `w_i = uniqueness_i × decay_recencia(t_i)` (multiplicar, no elegir). Half-life 1-2 años con suelo c≥0.25 (no tirar las únicas muestras de bear market).

## Catálogo de features (evidencia ponderada)

- **Momentum multi-horizonte** (1,2,5,10,21,63,126,252 barras) y **momentum vol-ajustado** `mom_h/(σ·√h)` — probablemente la mejor familia individual (Liu & Tsyvinski; literatura DMN).
- **Derivados (prioridad — alpha crypto-específico)**: funding crudo + z-score 30/90d + percentil + Δfunding (extremos = contrarian); ΔOI 1d/7d normalizado + interacción `ΔOI × sign(r)` (nuevos longs vs short covering); basis anualizado + su z-score; liquidaciones long/short z-scored + imbalance (con indicador de ruptura 2021); taker buy/sell imbalance desde klines.
- **Técnicos**: RSI(7,14,30), MACD histograma normalizado, Bollinger %B y bandwidth, OBV y OBV-MA, volume z-score 21d, Amihud |r|/dollar_volume, posición del cierre en el rango (C−L)/(H−L), distancia a máximo 52w, días desde ATH, vol-of-vol, ratio vol 5d/63d.
- **On-chain (contexto lento, transformado, nunca crudo)**: MVRV z-score, SOPR 7d-EMA, NVT 90d-suavizado, netflow z-score. ETH: staking flows, gas z-score (evidencia fina — pocas y que la selección pode).
- **Cross-asset**: correlación/beta rodante 30/90d a SPX (ES futures), DXY, oro, 5y yield + Δcorrelación (el régimen de correlación ES la feature — cambió estructuralmente post-ETF ene-2024). ETHBTC momentum, dominancia BTC.
- **Calendario**: día-de-semana (los efectos de retorno casi desaparecieron post-2020 en BTC, pero vol/volumen de finde siguen), dummy finde, sesión US/Asia para 4h, FOMC-day, horas-hasta-CPI, días-a-vencimiento CME.
- **Interacciones a mano (~5-10)**: `momentum × régimen_vol`, `funding_z × ΔOI`, `momentum × régimen_corr_SPX`, `SOPR × drawdown`.

## QA automatizado del data layer (asserts en cada refresh)

1. Gaps: diff de timestamps == intervalo; flag `after_gap` en barras adyacentes (indicadores que cruzan un gap están silenciosamente mal).
2. Unicidad (symbol, timestamp); consistencia OHLC (L ≤ O,C ≤ H, todo > 0).
3. Spikes: retorno > 10×MAD rodante sin confirmación en barra siguiente → flag, no borrar.
4. Validación cruzada de precios contra segunda fuente (umbral 0.5-1% diario).
5. Detección de revisiones: hash de los últimos 30 días de cada serie externa y diff en cada refresh (caza restatements silenciosos de vendors).
6. Cobertura: funding exactamente cada 8h; series acumulativas monótonas.
7. Provenance por fila: `is_filled`, `source`, `after_gap` hasta la matriz de features.
