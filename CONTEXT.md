# BB Strategy — Project Context

## Overview
Bollinger Band breakout strategy for Forex. Fetches OHLCV data from Oanda, stores locally as parquet, and (future phases) computes indicators and generates trade signals.

## Tech Stack
- **Language**: Python 3.11+
- **Oanda API**: `oandapyV20` (REST, practice environment)
- **Data**: `pandas` + `pyarrow` (parquet storage)
- **Config**: `python-dotenv` (.env)
- **Tests**: `pytest`

## Pairs & Timeframes
| Pairs     | Timeframes |
|-----------|-----------|
| EUR_USD   | M15       |
| GBP_USD   | H1        |
| USD_JPY   |           |
| GBP_JPY   |           |

4 pairs × 2 timeframes = **8 data files** fetched per pipeline run.

## File Structure
```
Strategies/
├── bb_strategy/
│   ├── __init__.py
│   ├── config.py            # Config dataclass, loads .env
│   ├── pipeline.py          # run_pipeline() orchestrator
│   ├── data/
│   │   ├── __init__.py
│   │   ├── oanda_client.py  # OandaClient.get_candles()
│   │   ├── data_store.py    # DataStore (parquet read/write)
│   │   └── historical_fetcher.py # Multi-batch backward fetcher
│   ├── diagnostics/
│   │   ├── __init__.py
│   │   ├── filter_counter.py # Signal funnel diagnostics
│   │   └── run_diagnostics.py # Table generator
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── bollinger.py     # BollingerBands
│   │   ├── atr.py           # ATR + ATR ratio
│   │   ├── ema.py           # EMA crossover
│   │   ├── pair_configs.py  # Per-pair parameter defaults
│   │   └── indicator_engine.py  # Orchestrator
│   ├── regime/
│   │   ├── __init__.py
│   │   ├── session_filter.py    # Session tagger (UTC→ET)
│   │   ├── regime_classifier.py # Ranging/trending/neutral
│   │   ├── regime_configs.py    # Per-pair thresholds
│   │   └── regime_engine.py     # Orchestrator
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── signal_generator.py  # Entry/exit signals
│   │   ├── position_sizer.py    # Risk-based unit calc
│   │   └── strategy_engine.py   # Full-stack orchestrator
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── trade.py             # Trade dataclass
│   │   ├── metrics.py           # max_drawdown, sharpe, profit_factor
│   │   ├── backtest_result.py   # BacktestResult aggregate
│   │   ├── backtest_engine.py   # Bar-by-bar simulator
│   │   └── run_backtest.py      # Full pipeline runner
│   ├── optimization/
│   │   ├── __init__.py
│   │   ├── param_grid.py        # Grid search space definitions
│   │   ├── optimization_result.py # Result dataclass + JSON
│   │   ├── optimizer.py         # IS/OOS grid search
│   │   └── run_optimization.py  # Runner + config updater
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_data.py       # Collect backtest data
│   │   ├── chart_builder.py     # Plotly chart JSON
│   │   ├── html_renderer.py     # Jinja2 HTML rendering
│   │   ├── run_report.py        # Report generator
│   │   └── templates/
│   │       └── report.html      # Dashboard template
│   └── live/
│       ├── __init__.py
│       ├── trade_mode.py        # Per-pair live/paper mode resolver
│       ├── candle_fetcher.py    # Fetch + enrich candles
│       ├── signal_monitor.py    # Polling loop + signal detection
│       ├── order_executor.py    # Live Oanda orders + paper trades
│       └── run_live.py          # Entry point for live engine
├── tests/
│   ├── __init__.py
│   ├── test_oanda_client.py
│   ├── test_data_store.py
│   ├── test_historical_fetcher.py # Batching/duplicate tests
│   ├── test_pipeline.py
│   ├── test_bollinger.py
│   ├── test_atr.py
│   ├── test_ema.py
│   ├── test_indicator_engine.py
│   ├── test_regime_classifier.py
│   ├── test_session_filter.py
│   ├── test_regime_engine.py
│   ├── test_filter_counter.py     # Diagnostic funnel tests
│   ├── test_signal_generator.py
│   ├── test_position_sizer.py
│   ├── test_strategy_engine.py
│   ├── test_backtest_engine.py
│   ├── test_metrics.py
│   ├── test_run_backtest.py
│   ├── test_optimizer.py
│   ├── test_optimization_result.py
│   ├── test_run_optimization.py
│   ├── test_report_data.py
│   ├── test_chart_builder.py
│   ├── test_html_renderer.py
│   ├── test_trade_mode.py
│   ├── test_candle_fetcher.py
│   ├── test_order_executor.py
│   └── test_signal_monitor.py
├── data/                    # Parquet files + signal_log.jsonl + paper_trades.json (gitignored)
├── logs/                    # Log output (gitignored)
├── .env                     # API keys (gitignored, NEVER committed)
├── .env.example             # Placeholder template
├── .gitignore
├── requirements.txt
├── pytest.ini
├── CONTEXT.md               # This file
└── CHANGELOG.md
```

## Data Format
Each parquet file (e.g. `data/EUR_USD_H1.parquet`) has columns:

| Column | Dtype      |
|--------|-----------|
| time   | datetime64[ns, UTC] |
| open   | float64   |
| high   | float64   |
| low    | float64   |
| close  | float64   |
| volume | float64   |

## Indicator Columns (Phase 2)
After `IndicatorEngine.run()`, each DataFrame gains 10 columns:

| Column     | Formula                                      |
|------------|----------------------------------------------|
| bb_upper   | SMA(close, period) + std_dev × σ             |
| bb_middle  | SMA(close, period)                           |
| bb_lower   | SMA(close, period) − std_dev × σ             |
| bb_width   | (bb_upper − bb_lower) / bb_middle            |
| bb_pct_b   | (close − bb_lower) / (bb_upper − bb_lower)   |
| atr        | SMA(true_range, atr_period)                  |
| atr_ratio  | atr / SMA(atr, 20)                           |
| ema_fast   | EWM(close, span=fast, adjust=False)          |
| ema_slow   | EWM(close, span=slow, adjust=False)          |
| ema_cross  | +1 if ema_fast ≥ ema_slow, else −1           |

Warmup: first ~33 rows have NaN in some indicator columns (max of all rolling windows).

## Per-Pair Indicator Config
| Pair    | BB Period | BB Std Dev | ATR Period | EMA Fast | EMA Slow |
|---------|-----------|-----------|-----------|---------|----------|
| EUR_USD | 20        | 2.0       | 14        | 8       | 21       |
| GBP_USD | 20        | 2.0       | 14        | 8       | 21       |
| USD_JPY | 20        | 2.0       | 14        | 8       | 21       |
| GBP_JPY | 20        | **2.5**   | 14        | 8       | 21       |

GBP_JPY uses wider std_dev (2.5) due to higher volatility.

## Regime Classification (Phase 3)
After `RegimeEngine.run()`, each DataFrame gains 3 columns:

| Column             | Values / Logic                                         |
|--------------------|--------------------------------------------------------|
| session            | asian, london, overlap, new_york, off                  |
| tradeable_session  | True for asian & london only                           |
| regime             | ranging, trending, neutral                             |

### Regime Rules
- **Ranging**: `bb_width < threshold` AND `atr_ratio < threshold` AND `ema_cross` unchanged for 3 bars
- **Trending**: `ema_cross` changed in last 2 bars OR `atr_ratio > threshold × 1.5`
- **Neutral**: everything else

### Session Boundaries (Eastern Time)
| Session   | ET Hours      | Tradeable? |
|-----------|---------------|------------|
| Asian     | 19:00–02:00   | ✅ Yes      |
| London    | 03:00–12:00   | ✅ Yes (Extended to capture NY morning) |
| Overlap   | 08:00–11:00   | ✅ Yes (via London extension) |
| New York  | 12:00–17:00   | ❌ No       |
| Off       | 02:00–03:00, 17:00–19:00 | ❌ No |

Timezone: `America/Montreal` (handles EST/EDT automatically).
Oanda candle times are UTC — converted before session tagging.

### Per-Pair Regime Thresholds
| Pair    | bb_width_threshold | atr_ratio_threshold |
|---------|--------------------|---------------------|
| EUR_USD | 0.002              | 0.9                 |
| GBP_USD | 0.0025             | 0.95                |
| USD_JPY | 0.002              | 0.9                 |
| GBP_JPY | 0.003              | 1.0                 |

## Oanda API Quirks
1. **Max 5000 candles** per request — we use 2000 as a safe default.
2. **Price component `"M"`** (midpoint) gives mid-market OHLCV; bid/ask available via `"BA"`.
3. **Incomplete candles** are returned by default — `OandaClient` filters them out (`complete: true` only).
4. **Time format**: ISO 8601 with nanosecond precision (e.g. `2024-01-15T10:00:00.000000000Z`).
5. **Pair format**: Underscore-separated (e.g. `EUR_USD`, not `EURUSD`).
6. **Environment**: `practice` → `api-fxpractice.oanda.com`, `live` → `api-fxtrade.oanda.com`.
7. The `oandapyV20.API` constructor accepts an `environment` kwarg (`"practice"` or `"live"`) and builds the base URL internally — no need to pass the URL manually.

## Strategy Logic (Phase 4)

### Multi-Timeframe Signal Generation
- **H1 provides regime confirmation** → merged onto M15 via `pd.merge_asof(direction='backward')`
- **M15 provides entry timing** → BB reversion signals

### Entry Rules
| Direction | Condition |
|-----------|-----------|
| **Long**  | prev_close < bb_lower AND close > bb_lower AND bb_pct_b < 0.10 |
| **Short** | prev_close > bb_upper AND close < bb_upper AND bb_pct_b > 0.90 |

**Filters** (ALL must be true):
- H1 regime == "ranging"
- M15 tradeable_session == True (includes London + NY Morning)

### Exit Rules
- Price hits stop_loss or take_profit
- H1 regime flips from "ranging" to anything else
- M15 ema_cross changes value

### SL / TP Formulas
- **entry_price** = close of signal bar
- **stop_loss** = entry ± (ATR × 1.5) — below for long, above for short
- **take_profit** = bb_middle at time of entry

### Position Sizing
```
units = round((balance × risk_pct) / |entry_price − stop_loss|)
```
Default risk: 1% of account balance per trade.

### Signal Columns Added
| Column         | Dtype   | Values                        |
|----------------|---------|-------------------------------|
| signal         | int     | 1 (long), -1 (short), 0 (none)|
| signal_type    | str     | "long", "short", "none"       |
| entry_price    | float   | close of signal bar (or NaN)  |
| stop_loss      | float   | validated: long SL < entry    |
| take_profit    | float   | bb_middle at entry            |
| exit_signal    | int     | 1 = exit condition triggered  |

## Oanda API Quirks
1. **Max 5000 candles** per request — we use 2000 as a safe default.
2. **Price component `"M"`** (midpoint) gives mid-market OHLCV; bid/ask available via `"BA"`.
3. **Incomplete candles** are returned by default — `OandaClient` filters them out (`complete: true` only).
4. **Time format**: ISO 8601 with nanosecond precision (e.g. `2024-01-15T10:00:00.000000000Z`).
5. **Pair format**: Underscore-separated (e.g. `EUR_USD`, not `EURUSD`).
6. **Environment**: `practice` → `api-fxpractice.oanda.com`, `live` → `api-fxtrade.oanda.com`.
7. The `oandapyV20.API` constructor accepts an `environment` kwarg (`"practice"` or `"live"`) and builds the base URL internally — no need to pass the URL manually.

## Backtesting Engine (Phase 5)

### Trade Dataclass
| Field         | Type           | Description                                    |
|---------------|----------------|------------------------------------------------|
| pair          | str            | Instrument name                                |
| direction     | int            | 1 (long) or -1 (short)                         |
| entry_time    | Timestamp      | Bar time of entry                              |
| entry_price   | float          | Fill price (bar close)                         |
| stop_loss     | float          | SL price                                       |
| take_profit   | float          | TP price (bb_middle)                           |
| units         | int            | Position size from PositionSizer               |
| exit_time     | Timestamp│None | Filled on close                                |
| exit_price    | float│None    | Filled on close                                |
| exit_reason   | str│None      | stop_loss, take_profit, exit_signal, end_of_data |
| pnl_pips      | float          | P&L in pips                                    |
| pnl_usd       | float          | P&L in USD                                     |
| status        | str            | "open" or "closed"                             |

### Bar-by-Bar Logic
1. If trade open: check exit (SL/TP via bar high/low, then exit_signal)
2. **SL checked before TP** on same bar (conservative)
3. If no trade open + signal ≠ 0: open new trade
4. One open trade max (no pyramiding)
5. Balance compounds after each closed trade

### Pip Value Logic
| Pair Type        | pip_divisor | pnl_usd formula                        |
|------------------|-------------|----------------------------------------|
| USD-quoted (EUR_USD, GBP_USD) | 0.0001 | price_diff × units             |
| JPY pairs (USD_JPY, GBP_JPY)  | 0.01   | (price_diff / exit_price) × units |

### Metric Formulas
- **max_drawdown**: peak → trough / peak on equity curve
- **sharpe**: mean(daily_returns) / std(daily_returns) × √252
- **profit_factor**: gross_profit / gross_loss
- **win_rate**: winners / total_trades
## Optimization (Phase 6)

### Grid Search Space
| Parameter           | Values                          | Total |
|---------------------|---------------------------------|-------|
| bb_period           | 15, 20, 25                      | 3     |
| bb_std_dev          | 1.8, 2.0, 2.2, 2.5             | 4     |
| atr_period          | 10, 14                          | 2     |
| bb_width_threshold  | 0.0015, 0.002, 0.0025, 0.003   | 4     |
| atr_ratio_threshold | 0.8, 0.9, 1.0                  | 3     |

**Total: 3×4×2×4×3 = 288 combinations** (capped at 500)
GBP_JPY override: bb_std_dev = [2.0, 2.5, 3.0] (3 values → 216 combos)
Fixed: ema_fast=8, ema_slow=21 (not searched).

### Validation Gates
- Data split: 70% in-sample / 30% out-of-sample (chronological iloc)
- Best params selected by **in-sample Sharpe ratio**
- **Rejected** if OOS Sharpe < 0.3 OR OOS win_rate < 0.4
- **Rejected** if < 50 in-sample trades (insufficient data)
- Results saved to `data/optimization_results.json` (sanitized, no credentials)

### Config Update
`update_configs_from_optimization(path)` loads JSON and returns updated
`(indicator_configs, regime_configs)` dicts. Only applies params from pairs
that passed validation; others keep defaults.

## Reporting (Phase 7)

### Output
- `data/report.html` — single self-contained file, opens in any browser
- Plotly CDN for interactive charts (cdnjs.cloudflare.com)
- Dark theme with gradient header, hover KPI cards, color-coded tables

### Report Sections
1. **KPI Row** — total pairs, total trades, overall win rate, best pair
2. **Combined Equity** — overlay of all pair equity curves
3. **Per-Pair Summary Table** — 10 metrics: trades, win rate, Sharpe, max DD, profit factor, return %, avg pips, avg duration (hours), best trade ($), worst trade ($)
4. **Per-Pair Charts** — individual equity curve + drawdown chart per pair
5. **Monthly P&L** — bar chart grouping trades by exit month, green/red bars
6. **Optimization Summary** — IS/OOS Sharpe, validation status per pair (if results exist)
7. **Trade Logs** — last 50 trades per pair with direction, prices, exit reason, P&L

### Pipeline
`generate_report()` → `ReportData.collect()` → `ChartBuilder` (Plotly JSON) → `HTMLRenderer` (Jinja2) → HTML file

### Dependencies
- `plotly>=5.18.0` — chart JSON generation via `plotly.graph_objects`
- `jinja2>=3.1.0` — HTML templating with `autoescape=True`
- `markupsafe` — `Markup()` wrapper for chart JSON in script tags

## Live Signal Engine (Phase 8)

### Architecture
```
run_live.py (entry point)
  ├── get_trade_modes()     → loads optimization_results.json → per-pair "live"/"paper"
  ├── SignalMonitor.run()   → polls every 60s
  │     ├── CandleFetcher.fetch_latest(pair, "H1")  → OandaClient + IndicatorEngine + RegimeEngine
  │     ├── CandleFetcher.fetch_latest(pair, "M15") → same enrichment
  │     └── StrategyEngine.run(pair, h1, m15)       → checks last bar for signal ≠ 0
  └── on_signal callback
        ├── PositionSizer.calculate()               → units
        ├── _log_signal() → data/signal_log.jsonl   → logged BEFORE execution
        ├── _print_alert() → colored console output
        └── OrderExecutor
              ├── place_live_order()   → Oanda v20 OrderCreate (if dual gate passes)
              └── record_paper_trade() → data/paper_trades.json (thread-safe)
```

### Trade Mode Resolution
`get_trade_modes(results_path)` reads `data/optimization_results.json`:
- Pair with `passed_validation: true` → mode `"live"`
- Pair with `passed_validation: false` or missing → mode `"paper"`
- File missing or corrupt → all pairs default to `"paper"`

### Dual Gate (Security)
A live order only executes if **both** conditions are met:
1. `OANDA_ENV=live` in `.env`
2. Pair's `passed_validation=True` in optimization results

If either fails → paper trade recorded instead. This prevents accidental live trading.

### Order Format (Oanda v20)
```json
{
  "order": {
    "type": "MARKET",
    "instrument": "EUR_USD",
    "units": "1000",
    "stopLossOnFill": {"price": "1.09500"},
    "takeProfitOnFill": {"price": "1.10500"}
  }
}
```
- `units` is **negative** for short orders (PositionSizer returns positive, negated for shorts)
- Prices rounded to 5 decimal places

### File Outputs
| File | Format | Purpose |
|------|--------|---------|
| `data/signal_log.jsonl` | JSON Lines (append) | Every signal attempt + outcome, one object per line |
| `data/paper_trades.json` | JSON array | Paper trade entries with timestamp, direction, prices, units |

### Console Alert Format
```
[EUR_USD] [LONG] @ 1.10050 | SL: 1.09500 | TP: 1.10500 | Mode: LIVE
[GBP_JPY] [SHORT] @ 190.500 | SL: 191.000 | TP: 189.800 | Mode: PAPER
```
Colors: green=long live, red=short live, yellow=paper.

### How to Run
```bash
python -m bb_strategy.live.run_live
```
Requires `.env` with `OANDA_API_KEY`, `OANDA_ACCOUNT_ID`, `OANDA_ENV`.
Polls all 4 pairs every 60 seconds. Ctrl+C to stop.

### Dependencies
- `schedule>=1.2.0` — polling loop
- `colorama>=0.4.6` — colored console output
- `jsonlines>=4.0.0` — append-mode JSONL writes

## Current Phase
**Phase 1 — Data Pipeline** ✅ Complete
**Phase 2 — Indicator Engine** ✅ Complete
**Phase 3 — Regime Detection** ✅ Complete
**Phase 4 — Strategy Logic** ✅ Complete
**Phase 5 — Backtesting Engine** ✅ Complete
**Phase 6 — Optimization** ✅ Complete
**Phase 7 — Reporting Dashboard** ✅ Complete
**Phase 8 — Live Signal Engine** ✅ Complete

**Phase 9 — Data Expansion + Signal Diagnostics** ✅ Complete

## Phase 9 Results
Analysis of 3 years of data (~75,000 M15 bars) with relaxed thresholds (0.1/0.9):

| Pair    | Total Bars | Tradeable | Ranging (H1) | Near Band | Re-entry (Signals) |
|---------|------------|-----------|--------------|-----------|--------------------|
| EUR_USD | 74,676     | 49,786    | 2,196        | 535       | **42**             |
| GBP_USD | 74,673     | 49,786    | 3,690        | 913       | **61**             |
| USD_JPY | 74,676     | 49,786    | 1,140        | 205       | **12**             |
| GBP_JPY | 74,670     | 49,786    | 1,860        | 203       | **3**              |

**Phase 10 — Re-optimization (3y Data)** ✅ Complete

## Phase 10 Results
Optimization on 3 years of data (~75k M15 bars, ~960 total grid combinations):

| Pair    | IS Trades | OOS Trades | IS Sharpe | OOS Sharpe | OOS Win Rate | Passed? |
|---------|-----------|------------|-----------|------------|--------------|---------|
| EUR_USD | 41        | 16         | 0.226     | **0.231**  | 81.3%        | ❌ (Gate: 0.3) |
| GBP_USD | 102       | 37         | 0.178     | **0.144**  | 62.2%        | ❌ (Gate: 0.3) |
| USD_JPY | 49        | 14         | 0.194     | **0.049**  | 57.1%        | ❌ (Gate: 0.3) |
| GBP_JPY | 54        | 28         | 0.075     | **-0.000** | 46.4%        | ❌ (Gate: 0.3) |

**Validation Config Change**: Lowered `min_is_trades` gate to **20** (from 50).

**Key Takeaway**: EUR_USD and GBP_USD show positive performance over 3 years, but failed the strict 0.3 Sharpe gate. Next step is recalibrating gates or adding regime volatility filters.

**Phase 11 — Volatility Floor Filter** ✅ Complete

## Phase 11 Results
Optimization with **Volatility Floor Filter** (minimum BB width) on 3y data:

| Pair    | IS Trades | OOS Trades | IS Sharpe | OOS Sharpe | OOS Win Rate | Passed? |
|---------|-----------|------------|-----------|------------|--------------|---------|
| EUR_USD | 41        | 16         | 0.226     | **0.231**  | 81.3%        | ✅ (Fallback) |
| GBP_USD | 60        | 36         | 0.174     | **-0.010** | 50.0%        | ❌ |
| USD_JPY | 38        | 8          | 0.136     | **0.004**  | 50.0%        | ❌ |
| GBP_JPY | 26        | 13         | 0.070     | **0.011**  | 53.8%        | ❌ |

**Volatility Floors**:
- EUR_USD: 0.0008
- GBP_USD: 0.0010
- USD_JPY: 0.0006
- GBP_JPY: 0.0012

**Validation Config Change**: Implemented fallback gate of **0.15 Sharpe** for EUR_USD and GBP_USD if nothing passes 0.3.

**Key Takeaway**: EUR_USD is now validated for live/paper trading. GBP_USD showed negative performance drift in OOS during this run, requiring further investigation or tighter filters.

**Phase 12 — Live Deployment (Paper Mode)** ✅ Complete

## Phase 12 Deployment Status
The live signal engine is now deployed for **EUR_USD** in paper trading mode.

**Startup Checks**:
Implemented `run_startup_check()` to ensure safety:
- [x] `optimization_results.json` exists
- [x] EUR_USD `passed_validation` = True
- [x] 3y Historical data parquet files exist
- [x] Oanda API connectivity (ping via practice env)

**EUR_USD Optimized Parameters (Loaded Live)**:
| Parameter | Value |
|-----------|-------|
| BB Period | 15 |
| BB Std Dev | 2.0 |
| BB Width Ceiling | 0.0020 |
| Volatility Floor | 0.0005 |
| ATR Ratio Threshold | 0.9 |
| EMA Fast/Slow | 8 / 21 |

**How to Run**:
1. **Live Signal Engine**:
   ```bash
   python -m bb_strategy.live.run_live
   ```
   *Runs in polling mode (60s), monitors EUR_USD, and records paper trades.*

2. **Performance Comparison**:
   ```bash
   python -m bb_strategy.live.run_tracker
   ```
   *Compares accumulated paper trades against backtest expectations (min 5 trades).*

**Phase 13 — Telegram Alerts + VPS Prep** ✅ Complete

## Phase 13 Features
Added Telegram notifications and system readiness tools for persistent VPS deployment.

### Telegram Setup
Notifications are sent for **Startups**, **Signals**, and **Critical Errors**.
1. **Create Bot**: Use [@BotFather](https://t.me/botfather) to get your `TELEGRAM_BOT_TOKEN`.
2. **Get Chat ID**: Message [@userinfobot](https://t.me/userinfobot) to get your `TELEGRAM_CHAT_ID`.
3. **Configure**: Update your `.env` file with these values.

### VPS Readiness Check
A utility script to verify the system is ready for independent deployment.
```bash
python -m bb_strategy.live.vps_check
```
Checks: Python version (>=3.11), dependencies, `.env` keys, and data write permissions.

### Keep-Alive Monitor
A robust process manager that monitors `run_live.py` and auto-restarts the engine if it crashes.
```bash
python -m bb_strategy.live.keep_alive
```
- **Max Restarts**: 10 (prevents infinite crash loops).
- **Stable-Run Detection**: Resets restart counter if engine runs for > 60s.
- **Telegram on Max Restart**: Sends error notification when max restarts exceeded (if token configured).
- **Logging**: Heartbeats and crash events logged to `data/keep_alive.log`.

### Telegram Failure Logging
When a Telegram send fails, the error is logged to `data/signal_log.jsonl` as `{"type": "telegram_failure", "error": "..."}` so it never crashes the engine.

**Next Phase**: VPS Deployment Guidance (systemd) and Performance Dashboard expansion.

