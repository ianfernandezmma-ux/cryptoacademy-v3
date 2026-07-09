# Valor añadido de IA local + backtest bulletproof (research 2026-07-09)

## Ranking de usos del LLM local para el modelo (evidencia 2024-2026)

1. **Features de eventos estructurados agregadas a diario** (HACER YA) — extender el schema actual; conteos por tipo, severidad ponderada, novedad. Señal ortogonal al precio (arXiv 2512.19484, 2510.15691). Riesgo de leakage bajo con anonimización de fechas (ya implementada) + taxonomía CONGELADA antes de tocar el test.
2. **Clasificación de régimen risk-on/off diaria** (SEGUNDO) — score ordinal −2..+2 + split crypto_stress vs macro_stress sobre titulares dedupeados; usar como feature condicionante y gate, no como estrategia (ICAIF'24; arXiv 2604.10996: la señal LLM se recupera en calma, falla en crisis).
3. **Minería de factores con LLM bajo protocolo** — DSL restringido de operadores, evaluador determinista con IC en purged-CV SOLO train, gates pre-registrados (suelo de IC, t-stat, cap de correlación), log append-only, contar TODOS los candidatos para el DSR. Validado en crypto (arXiv 2604.26747, Sharpe 1.55 OOS, alpha concentrado en small-caps — esperar menos en BTC/ETH; el protocolo es lo transferible).
4. Informe semanal deep-research → contexto para el humano, NO feature (52 obs/año = ruido).
5. **Datos sintéticos (TimeGAN/difusión): SKIP** — fidelidad ≠ lift predictivo; no añade información sobre P(y|X); solo útil para stress de sizing.
6. **LLM como agente de trading: NO** — arXiv 2605.16895 (Alpha Illusion): con tickers anonimizados un agente representativo se negó a operar 25/25; la "señal" era memoria del ticker. Los LLM fabrican features; la decisión es estadística y auditable.

## Stack de backtest (verificado jul-2026)

`LightGBM → skfolio CombinatorialPurgedCV (cross-check purged-cv) → vectorbt OSS 0.28.x (sweeps; PRO ~$20-40/mes solo si el loop se vuelve cuello de botella) → pypbo DSR/PBO → nautilus_trader ≥1.227 (event-driven, Rust, adapter Binance production-ready spot+USDⓈ-M, Windows OK, mismo código backtest→demo→live) → Binance DEMO vía nautilus (mejor que testnet: datos reales, fondos simulados) → live 1-5% tamaño`.

- timeseriescv ABANDONADO con bugs — no usar. vectorbt OSS congelado en 0.28.x (funciona).
- Alpaca crypto sigue vivo pero fees 0.15-0.25% y libros finos — venue equivocado para ensayar Binance. Bybit demo v5 como fallback.

## Modelo de costes (Binance 2026, verificado)

- Perps USDⓈ-M VIP0: maker 2 bps / taker 5 bps (4.5 con BNB). Spot: 10 bps.
- Slippage <$100k BTC/ETH: 1-5 bps normal (mediana ~$8M en ±$100 del mid), ×5-10 en estrés → modelar taker + spread/2 + 2 bps, stress +15-25 bps.
- **Funding**: baseline +0.01%/8h ≈ **+10.95%/año de coste para longs** (~78-88% del tiempo en baseline en 2025; picos 50-100% anualizado en bull 2024). Cargar el funding HISTÓRICO REAL por día de posición, jamás una constante.
- **Regla 2×**: repetir todo el backtest con costes dobles; si muere, no era estrategia.

## Orden de fases del backtest

1. Selección bajo CPCV (embargo ≥ horizonte del label), todos los trials loggeados.
2. Sweep vectorizado cost-aware (1× y 2× costes).
3. Gate estadístico: DSR > 0.95 con N_trials real, PBO < 20-25%, MinTRL vs span OOS. Fallo → volver a features, no a tunear.
4. Confirmación event-driven en nautilus; PnL vectorizado ≈ event-driven o hay bug.
5. Paper 8-12 semanas en Binance demo midiendo slippage realizado vs modelado.
6. Live al 1-5% del tamaño objetivo; escalar solo si el tracking error se mantiene en el sobre del paper.
