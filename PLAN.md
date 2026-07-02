# CryptoAcademy v3 — Plan Maestro de Reconstrucción

> Elaborado el 2026-07-02 con research independiente (ML de señales, datos de noticias point-in-time, stack de IA local para RTX 5090) + auditoría del repo `ianfernandezmma-ux/cryptoacademy-thesis`.
> Hardware objetivo: Ryzen 7 + RTX 5090 (32GB VRAM, Blackwell sm_120), Windows 11.

---

## 1. Diagnóstico del proyecto actual (lo que hay que corregir)

### 1.1 Los números reales vs. los publicados

| Métrica | Publicado (README/tesis) | Reproducible desde los artefactos del repo |
|---|---|---|
| MCC BTC / ETH | 0.5642 / 0.6243 | **0.3407 / 0.3581** |
| Accuracy | 78.2% / 81.1% | 67.1% / 67.7% |
| Sharpe | 3.51 / 3.83 | **0.86 (holdout de la capa de calibración — el número creíble)** |

Los parquets commiteados corresponden al modelo *baseline* de 10 features (pre-noticias, pre-tuning). Las predicciones que respaldan los números headline no están en el repo (el código ML real vive en `C:/Users/Ian/OneDrive/Escritorio/ThesisFinalPres/thesis-archive`, referenciado en `loaders.py:32`).

### 1.2 Las tres fuentes de inflación (por orden de gravedad)

1. **Optuna tuneó hiperparámetros maximizando el MCC sobre las MISMAS predicciones out-of-sample que se reportan** (tesis p.19, p.28: 0.48 → 0.56/0.62). El "OOS" reportado es in-sample respecto a la selección del modelo. No existe holdout final intocado para el modelo ML.
2. **Lookahead de noticias confirmado (tu sospecha era correcta):** el sentimiento se agrega en ventanas de 24h por fecha de calendario y se une a la barra de medianoche (todas las predicciones tienen timestamp 00:00). El modelo del día D ve un resumen de titulares publicados A LO LARGO de todo el día D — hasta ~24h de noticias futuras. El "shift de una barra" (4h) de la tesis no neutraliza un desalineamiento de 24h. El salto de MCC 0.34 → 0.48 (+41%) al añadir 2-3 features de sentimiento diario es la firma clásica de leakage, no de alpha. Además, scorear titulares 2021-2025 con un modelo OpenAI moderno inyecta hindsight (el modelo "sabe" cómo acabaron los eventos).
3. **Selección de features y del umbral P≥0.60 sobre la misma ventana de evaluación** (tesis p.17, p.21).

Otros fallos: sin purging/embargo alrededor del horizonte de 96h en el reentrenamiento rolling; backtest con slippage cero y full-Kelly; el bot en vivo tradea con un **stub de datos fabricados** (`predict_stub.py` reetiqueta una predicción de 2026-03-20 como fresca cada día, para ambos assets).

### 1.3 Lo que SÍ merece migrarse del repo viejo

- `src/automation/backtest/` (harness de validación limpio y testeado).
- La metodología de calibración D-0 (Hansen SPA, block bootstrap, deflated Sharpe, costes 66-86 bps, haircut 0.80×) — es lo más riguroso del proyecto.
- `scrapers/` (RSS + FRED, yaml-driven, timestamps reales) y `local_scrape.py`.
- Módulos operacionales: `positions/orders.py`, `positions/trail.py`, `git_ops/safe_push.py`, `routines/lock.py`, `observability/`.
- El static site builder (`src/automation/web/`) con su diseño "JSON es la fuente de verdad".
- La suite de 117 tests y la disciplina de `decisions.md`.

**Punto de partida honesto:** MCC ~0.34-0.36, Sharpe realista ~0.86. La literatura 2025-2026 dice que 52-56% de accuracy direccional diaria OOS en BTC/ETH es lo alcanzable; cualquier backtest muy por encima es más probablemente leakage que genialidad.

---

## 2. Arquitectura objetivo

```
C:\CryptoAcademy\
├── pyproject.toml            # uv, Python 3.12, ruff + mypy + pytest
├── configs/                  # Hydra: feature blocks × modelos × labels × CV
├── data/
│   ├── raw/                  # Parquet particionado por symbol/mes (nunca se muta)
│   ├── news.duckdb           # almacén bitemporal append-only de artículos
│   └── features/             # matrices de features versionadas
├── src/cryptoacademy/
│   ├── data/                 # ingesta: binance.vision, CCXT, CoinMetrics, FRED, F&G
│   ├── news/                 # scraping, dedup, scoring LLM local, agregación PIT
│   ├── features/             # bloques modulares: price, derivs, onchain, macro, sentiment
│   ├── labels/               # CUSUM + triple-barrier + sample weights
│   ├── models/               # LightGBM/XGB/CatBoost + PatchTST/N-HiTS + meta-labeling
│   ├── validation/           # CPCV purged+embargo, DSR, PBO, lockbox
│   ├── backtest/             # vectorbt (triage) + nautilus_trader (realista)
│   ├── pipeline/             # orquestación diaria (Task Scheduler entrypoints)
│   └── web/                  # site builder (migrado y mejorado)
├── tests/                    # incluye test anti-leakage sintético en CI
└── .github/workflows/ci.yml  # ruff + mypy + pytest en cada push (no existía antes)
```

**Stack:** Polars + DuckDB + Parquet (pandas solo en la última milla) · PyTorch ≥2.7 cu128 en WSL2 para deep learning (sm_120) · LightGBM con `device="cuda"` · MLflow local (loggear TODOS los trials — el conteo es input del Deflated Sharpe) · Hydra + Optuna · Ollama/llama.cpp nativo Windows para los LLM.

---

## 3. Fases

### Fase 0 — Fundaciones + empezar a recolectar YA (semana 1)
- `git init`, pyproject con uv, CI en GitHub Actions, estructura de arriba.
- WSL2 actualizado a ≥2.7.0 (`wsl --update --pre-release`) para PyTorch/vLLM; verificar `torch.cuda.get_device_capability() == (12, 0)`.
- Instalar Ollama; descargar Qwen3-30B-A3B (Q4_K_M) + un 32B denso Q5/Q6 + bge-m3.
- Migrar los módulos reutilizables del repo viejo.
- **Arrancar el colector forward de noticias HOY**: polling RSS cada 5-10 min (~15 feeds) registrando `first_seen_at_utc` en cada ingesta. Cada día que corre es historia limpia e irreproducible que ganas. Este es el paso más urgente de todo el plan.

### Fase 1 — Capa de datos (semanas 1-3)
- **Precios/derivados:** dumps masivos de `data.binance.vision` (klines 1H/4H, funding completo, aggTrades) + top-ups con CCXT. Open interest solo tiene ~30 días de historia en Binance → empezar a archivarlo diariamente ya; backfill vía Coinalyze/Coinglass free.
- **Cross-asset:** DXY, SPX, oro, 10Y, VIX, M2 (yfinance/FRED) — con lag conservador de publicación (el CPI sale a las 8:30 ET, no a medianoche).
- **On-chain:** Coin Metrics Community API (la mejor fuente gratuita programática), Blockchain.com, DeFiLlama. Glassnode requiere ~$79/mes para API → descartado.
- **Fear & Greed:** `api.alternative.me/fng/?limit=0` (histórico completo desde 2018 en una llamada).
- **Backfill de noticias 2020-2026** (reemplaza el corpus CryptoPanic — su API gratuita murió en abril 2026 y no permite backfill):
  - Primario: **CoinDesk Data API** (`news/v1/article/list` paginando hacia atrás con `to_ts`) — su `published_on` es timestamp de ingesta del agregador, mejor aún para PIT que la fecha del publisher.
  - Amplitud: **GDELT GKG 2.0** (archivos crudos de 15 min desde 2015 o BigQuery) — el archivo de 15 min donde aparece una URL es en sí una cota point-in-time.
  - Verificación: Wayback Machine CDX sobre una muestra del 1% por fuente.
- **Esquema bitemporal append-only:** `articles(url_hash, source, title, body_hash, published_at_utc, first_seen_at_utc, backfilled, revision_no)`. Regla de features: `usable_at = max(published_at, first_seen_at) + buffer` (15-60 min live, **2-6h para filas backfilled**). Nunca bucketing por fecha de calendario; siempre cutoff exacto sobre epoch UTC.
- **Test anti-leakage en CI:** inyectar artículo sintético con timestamp T−1s y T+1s y asertar que solo el primero entra en las features de la decisión T.

### Fase 2 — Pipeline de noticias con IA local (semanas 2-4, en paralelo)
Cascada barato → caro, todo gratis en tu 5090 (carga diaria realista de 300-1000 artículos = 15-60 min nocturnos):
1. RSS/API pull → **trafilatura** para extracción de texto (Playwright+Camoufox solo para sitios JS-pesados).
2. **Dedup:** MinHash-LSH (`datasketch`) + embeddings bge-m3 (coseno >0.85-0.90) — las crypto news están sindicadas masivamente; esto recorta 30-50% del trabajo del LLM. Conservar el `usable_at` MÁS TEMPRANO del cluster y el tamaño del cluster como feature de "coverage breadth".
3. **Filtro rápido** (Qwen3-8B o el mismo 30B-A3B): `{relevant, asset_tags, importance}`.
4. **Scoring estructurado** (Qwen3-30B-A3B MoE, ~110-125 tok/s, JSON schema forzado por gramática + Pydantic + retry vía Instructor, temperature 0-0.3, un artículo por request, paralelismo del servidor): `{assets, event_type: regulation|hack|etf|macro|exchange|whale|tech, direction, severity 1-5, is_price_report: bool, novelty}`.
   - **`is_price_report` es crítico:** "Bitcoin surges past $100k" es sentimiento CAUSADO por el retorno que quieres predecir. Separar `sentiment_exogenous` de `sentiment_price_reporting`; solo el primero es candidato a alpha.
   - Para el histórico: anonimizar entidades/fechas/precios en el prompt (mitiga el lookahead del propio LLM) y validar contra CryptoBERT como segunda opinión (el desacuerdo entre ambos es en sí una feature).
5. **Síntesis diaria** (32B denso Q5/Q6, ~45-52 tok/s): resúmenes ES+EN por cluster y de mercado + una fila JSON/Parquet de agregados diarios por asset.
6. **Agregación PIT:** media ponderada por decay exponencial (half-life 6-24h), pesos por credibilidad de fuente (tier fijo o aprendidos walk-forward), dispersión, negative-share (las noticias negativas mueven BTC mucho más que las positivas), novelty-weighted.
- **Scheduling:** Windows Task Scheduler → `run_daily.py` con tenacity (retries), logging rotativo, `run_manifest.json` por ejecución, digest a Telegram (también en éxito — el silencio es ambiguo), idempotencia por url_hash en la DB. Sin Docker: venv plano, más debuggeable.

### Fase 3 — Features y labels (semanas 4-6)
- Bloques modulares para ablations: (a) precio/vol (retornos multi-horizonte, RV Parkinson/Garman-Klass, RSI/MACD/ATR/BB, momentum), (b) **derivados — empíricamente los más predictivos:** funding, OI, taker buy/sell, basis, liquidaciones, (c) on-chain, (d) cross-asset, (e) sentimiento (exógeno vs price-report, y ortogonalizado: residuo de regresar sentimiento sobre retornos de la misma ventana, fit walk-forward).
- **Labels:** CUSUM event sampling → triple-barrier vol-scaled (barreras 1-2σ, vertical 5-10 días) → pesos por unicidad de muestra (los labels solapados violan i.i.d.). Validado en crypto por Financial Innovation 2025.
- Todos los joins como as-of point-in-time (`merge_asof` backward con tolerancia). Ejecución siempre en la apertura de la barra t+1, nunca al cierre de la barra t.

### Fase 4 — Modelos y validación (semanas 6-10)
- **Primario: LightGBM** (+ XGBoost/CatBoost) sobre features tabulares — sigue siendo el estándar a batir en 2026. **Meta-labeling:** modelo secundario que predice P(señal primaria rentable) para filtrar y dimensionar.
- **Challengers DL** (aquí luce la 5090): PatchTST, N-HiTS, TFT (neuralforecast/Time-Series-Library); opcional CryptoMamba. Benchmark zero-shot Chronos/TimesFM (los revisores de 2026 lo esperan).
- Ensemble por promediado de probabilidades. Hipótesis honesta de tesis: "GBDT ≈ ensemble > DL puro en features tabulares".
- **Protocolo de validación (el corazón del proyecto):**
  1. CPCV con purging + embargo (~1%) usando `purgedcv` — distribución de Sharpes, no un número.
  2. **Deflated Sharpe Ratio + PBO** (`pypbo`) — requiere loggear cada trial en MLflow; objetivo PBO < 0.2.
  3. Walk-forward como resultado headline.
  4. **Lockbox:** los últimos N meses no se tocan hasta el final, UNA sola vez.
  5. Optuna optimiza SOLO dentro de los folds de entrenamiento — nunca sobre las predicciones OOS reportadas (el error fatal de v2).
  6. Multi-seed con barras de incertidumbre; test vs. random walk.
- **Ablation clave para la tesis:** ¿el sentimiento añade algo POR ENCIMA de lagged returns/momentum? La literatura dice que la causalidad va mayormente de retornos → sentimiento; si tu contribución desaparece al incluir momentum, el "news alpha" era momentum disfrazado. Un resultado nulo bien medido es igual de valioso académicamente.

### Fase 5 — Backtest realista y paper trading (semanas 8-12)
- **VectorBT** para triage rápido de señales → **NautilusTrader** (event-driven, mismo código backtest/live) para los finalistas.
- Costes: taker 5 bps, slippage 5-30 bps escalando con estrés, **funding cada 8h si hay perps** (una estrategia crónicamente long paga 5-20%/año en régimen de funding positivo). Backtest en variante spot Y perp.
- **Sizing: vol targeting + máximo ¼-Kelly** sobre probabilidades calibradas (isotonic) — nunca full-Kelly como en v2.
- Reportar por año y por régimen (bull/bear/chop), turnover y coste de breakeven por trade. Tearsheets con quantstats.
- Eliminar `predict_stub.py`: conectar el modelo real al paper trading (Alpaca/Binance testnet) con cutoffs estrictos: decisión en T usa solo noticias con `usable_at ≤ T − buffer` y precios hasta la barra cerrada anterior.

### Fase 6 — Web y automatización end-to-end (semanas 10-14)
- Migrar el static site builder (JSON source of truth) y desplegarlo de verdad (GitHub Pages/Vercel) con: tearsheet vivo, curva de calibración, registro de predicciones con timestamp verificable ANTES del resultado (integridad demostrable), y el resumen diario ES/EN generado por el modelo local.
- Rutina diaria completa: colector RSS continuo → pipeline de noticias nocturno (LLM local) → predicción a hora fija → paper trade → informe → publicación web → digest Telegram. Todo local, coste marginal $0.

---

## 4. Reglas de oro (grabar a fuego)

1. Ningún dato entra en una feature antes de su `usable_at`. Sin excepciones, con test en CI.
2. Optuna nunca ve las predicciones que se reportan.
3. El lockbox se abre una vez. Si el resultado es malo, se publica malo.
4. Loggear todos los trials: N es input del Deflated Sharpe.
5. Sentimiento se evalúa contra baseline de momentum, no contra baseline de nada.
6. Ejecución en t+1 open, costes completos (fees + slippage + funding), ¼-Kelly máximo.
7. El número que se publica es el que sobrevive a todo lo anterior. En v2 ese número era Sharpe 0.86 — superarlo DE VERDAD es el objetivo de v3.
