# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-02-20

### Added — Phase 13: Telegram Alerts + VPS Prep
- `bb_strategy/notifications/telegram_notifier.py` — `TelegramNotifier` with `send_signal()`, `send_startup()`, `send_error()`; non-blocking, logs failures to signal_log.jsonl.
- Updated `.env.example` — TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID with setup instructions.
- Updated `bb_strategy/config.py` — optional telegram_bot_token and telegram_chat_id (graceful disable when missing).
- Updated `run_live.py` — Telegram startup/signal/error notifications; startup message includes Mode (PAPER/LIVE).
- `bb_strategy/live/vps_check.py` — `run_vps_check()` for system readiness (Python 3.11+, deps, .env, data dir, parquet files).
- `bb_strategy/live/keep_alive.py` — subprocess loop with auto-restart, max 10 restarts; sends Telegram error on max-restart exit.
- Token masking: TELEGRAM_BOT_TOKEN never logged — display as "tg:***" only.
- 6 tests: telegram URL/payload, failure-no-raise, disabled-when-token-none, vps pass/fail.

## [1.2.0] - 2026-02-20

### Added — Phase 12: Live Deployment (EUR_USD Paper Mode)
- `bb_strategy/live/startup_check.py` — pre-launch safety gate (verifies data, validation, and API connectivity).
- `bb_strategy/live/candle_fetcher.py` — enriches live candles with optimized parameters specifically for validated pairs.
- `bb_strategy/live/performance_tracker.py` — tracks paper trade metrics (pips, win rate, Sharpe) vs backtest expectations.
- `bb_strategy/live/run_tracker.py` — CLI tool for formatted performance comparison tables.
- Updated `run_live.py` to trigger startup checks and periodic performance updates.
- Result: **EUR_USD deployed** in paper mode with optimized params (BB=15/2.0, Floor=0.0005).

## [1.1.0] - 2026-02-20

### Added — Phase 11: Volatility Floor Filter
- `bb_strategy/regime/regime_classifier.py` — added `min_bb_width` floor to ranging condition to filter out dead markets.
- `bb_strategy/regime/regime_configs.py` — defined pair-specific volatility floors (e.g., 0.0008 for EUR_USD).
- `bb_strategy/optimization/param_grid.py` — added `min_bb_width` to grid and optimized combinations (243 per pair).
- `bb_strategy/diagnostics/filter_counter.py` — added `volatility_floor` diagnostic stage (filters ~15-25% of ranging bars).
- `bb_strategy/optimization/run_optimization.py` — implemented fallback gate (0.15 Sharpe) if 0.3 gate fails.
- Results: **EUR_USD passed** (0.231 Sharpe) using fallback gate.

## [1.0.0] - 2026-02-20

## [0.9.0] - 2026-02-20

### Added — Phase 9: Data Expansion + Signal Diagnostics
- `bb_strategy/data/historical_fetcher.py` — `HistoricalFetcher` for multi-year batched candle retrieval
- `bb_strategy/diagnostics/filter_counter.py` — `FilterCounter` stage-by-stage signal funnel diagnostics
- `bb_strategy/diagnostics/run_diagnostics.py` — orchestrator for running counts across all pairs
- `run_full_pipeline()` in `bb_strategy/pipeline.py` to fetch 3y dataset
- 5 new tests (`test_historical_fetcher.py`, `test_filter_counter.py`, and relaxed threshold test in `test_signal_generator.py`)
- Added `tabulate>=0.9.0` to requirements.txt

### Changed
- `SignalGenerator` — relaxed `bb_pct_b` threshold from 0.05/0.95 to 0.1/0.9
- `SessionFilter` — extended London session end from 08:00 to 12:00 ET (captures NY morning)
- Updated `CONTEXT.md` with new data paths and diagnostic findings

## [0.8.0] - 2026-02-20

### Added — Phase 8: Live Signal Engine
- `bb_strategy/live/` subpackage with 5 modules
- `trade_mode.py` — resolves per-pair live/paper mode from `optimization_results.json`
  - `get_trade_modes()` returns "live" only for pairs with `passed_validation=True`
  - Falls back to "paper" for all pairs if file is missing or corrupt
- `candle_fetcher.py` — `CandleFetcher.fetch_latest()` wraps OandaClient + IndicatorEngine + RegimeEngine
- `signal_monitor.py` — `SignalMonitor.run()` polls all pairs every 60s via `schedule` library
  - Runs StrategyEngine per pair, checks last bar for signal ≠ 0
  - Fires `on_signal` callback when signal detected
- `order_executor.py` — `OrderExecutor` with dual execution paths:
  - `place_live_order()` → Oanda v20 `OrderCreate` (MARKET order with SL/TP)
  - `record_paper_trade()` → thread-safe append to `data/paper_trades.json`
  - Response logs stripped to status code + order ID only (security)
- `run_live.py` — entry point wiring all components:
  - Dual gate: live orders require `OANDA_ENV=live` AND `passed_validation=True`
  - Logs all signal attempts to `data/signal_log.jsonl` BEFORE execution
  - Colored console alerts: green=long live, red=short live, yellow=paper
- 16 new tests across 4 test files (trade_mode, candle_fetcher, order_executor, signal_monitor)
- Added `schedule>=1.2.0`, `colorama>=0.4.6`, `jsonlines>=4.0.0` to requirements.txt
- Updated CONTEXT.md with live engine architecture, trade mode logic, file outputs, run instructions

## [0.7.0] - 2026-02-20

### Added — Phase 7: Reporting Dashboard
- `bb_strategy/reporting/` subpackage with 5 modules + Jinja2 template
- `ReportData` — collects backtest results, equity curves, trade logs, 10 summary metrics per pair
- `ChartBuilder` — generates Plotly JSON for equity curves, drawdown charts, monthly P&L bars, combined overlay
- `HTMLRenderer` — renders self-contained HTML via Jinja2 with `autoescape=True`, Plotly CDN
- `generate_report()` → produces `data/report.html` with dark theme, KPI cards, interactive charts
- Report sections: KPI row, combined equity, per-pair summary table, per-pair charts, monthly P&L, optimization summary, trade logs
- 7 new tests across 3 test files (report_data, chart_builder, html_renderer)
- Added `plotly>=5.18.0` and `jinja2>=3.1.0` to requirements.txt
- Updated CONTEXT.md with report structure, sections, and pipeline

## [0.6.0] - 2026-02-20

### Added — Phase 6: Optimization
- `bb_strategy/optimization/` subpackage with 4 modules
- `param_grid.py` — grid search space (288 combos default, 216 for GBP_JPY), capped at 500
  - GBP_JPY gets wider bb_std_dev range: [2.0, 2.5, 3.0]
- `Optimizer` — 70/30 chronological IS/OOS split, grid search by Sharpe, validation gates
  - Rejects if OOS Sharpe < 0.3 or OOS win_rate < 0.4 or < 50 IS trades
- `OptimizationResult` — dataclass with to_json/from_json for flat persistence
- `run_optimization.py` — runs all pairs, saves sanitized JSON, provides `update_configs_from_optimization()`
- 8 new tests across 3 test files (optimizer, optimization_result, run_optimization)
- Updated CONTEXT.md with grid space, validation gates, and config update mechanism

## [0.5.0] - 2026-02-20

### Added — Phase 5: Backtesting Engine
- `bb_strategy/backtest/` subpackage with 5 modules
- `Trade` dataclass with `close()` method computing pnl_pips and pnl_usd
  - JPY pairs use quote-currency conversion: `(price_diff / exit_price) × units`
  - USD-quoted pairs use direct: `price_diff × units`
- `BacktestEngine` — bar-by-bar simulator: SL/TP via bar high/low (SL checked before TP), one-trade-at-a-time, compounding balance
- `BacktestResult` — aggregate metrics: win_rate, profit_factor, max_drawdown, sharpe, avg_pips
- `metrics.py` — standalone functions: calc_max_drawdown, calc_sharpe, calc_profit_factor
- `run_backtest.py` — full pipeline runner across all pairs
- 18 new tests across 3 test files (backtest_engine, metrics, run_backtest)
- Updated CONTEXT.md with Trade fields, bar-by-bar logic, pip value math, metric formulas

## [0.4.0] - 2026-02-20

### Added — Phase 4: Strategy Logic
- `bb_strategy/strategy/` subpackage with 3 modules
- `SignalGenerator` — H1 regime confirmation + M15 BB reversion entries (long/short)
  - merge_asof aligns H1 regime onto M15 timeline
  - Entry: prev close outside band → current close re-enters, with bb_pct_b confirmation
  - Exit: regime flip, EMA cross change, or SL/TP hit
- `PositionSizer` — risk-based unit calculation: `round((balance × risk%) / |entry − SL|)`
- `StrategyEngine` — full-stack orchestrator: indicators → regime → signals
- SL/TP: stop_loss = entry ± ATR×1.5, take_profit = bb_middle
- SL direction validation: long SL < entry, short SL > entry (raises ValueError if violated)
- 16 new tests across 3 test files (signal_generator, position_sizer, strategy_engine)
- Updated CONTEXT.md with signal logic, entry/exit rules, SL/TP formulas, position sizing

## [0.3.0] - 2026-02-20

### Added — Phase 3: Regime Detection
- `bb_strategy/regime/` subpackage with 4 modules
- `SessionFilter` — converts UTC candle times to America/Montreal, tags asian/london/overlap/new_york/off sessions
- `RegimeClassifier` — labels each bar as ranging/trending/neutral based on bb_width, atr_ratio, and ema_cross stability
- `RegimeEngine` — orchestrator applying session filter then classifier using per-pair thresholds
- `regime_configs.py` — per-pair bb_width and atr_ratio thresholds (GBP_JPY widest)
- `tradeable_session` flag — True only for asian and london (pre-overlap)
- 17 new tests across 3 test files (regime_classifier, session_filter, regime_engine)
- Updated CONTEXT.md with regime rules, session boundaries, and per-pair thresholds

## [0.2.0] - 2026-02-20

### Added — Phase 2: Indicator Engine
- `bb_strategy/indicators/` subpackage with 5 modules
- `BollingerBands` — bb_upper, bb_middle, bb_lower, bb_width, bb_pct_b (population std, ddof=0)
- `ATR` — true range with simple rolling mean, plus atr_ratio (ATR vs its 20-period SMA)
- `EMA` — fast/slow EWM crossover with +1/−1 signal
- `IndicatorEngine` — orchestrator applying all indicators using per-pair configs
- `pair_configs.py` — default parameters; GBP_JPY uses std_dev=2.5 (wider bands)
- 14 new tests across 4 test files (bollinger, atr, ema, indicator_engine)
- Updated CONTEXT.md with indicator formulas, column names, and per-pair config table

## [0.1.0] - 2026-02-20

### Added — Phase 1: Data Pipeline
- Project scaffold: `bb_strategy/`, `tests/`, `data/`, `logs/`
- `Config` dataclass loading credentials from `.env` via dotenv
- `OandaClient` — fetches midpoint OHLCV candles via `oandapyV20`, filters incomplete candles
- `DataStore` — parquet-based persistence keyed by `{pair}_{timeframe}`
- `run_pipeline()` — orchestrates fetch + store for all pair × timeframe combinations
- 7 tests (6 unit + 1 integration): column schema, roundtrip, existence checks, pipeline file creation
- `.env.example`, `.gitignore`, `requirements.txt`, `pytest.ini`
- `CONTEXT.md` with project state and Oanda API quirks
