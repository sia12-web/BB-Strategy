# BB Strategy

Bollinger Band breakout strategy for Forex. Fetches OHLCV data from Oanda, computes indicators, and generates trade signals with regime filtering.

## Features

- **Data pipeline**: Oanda API integration, parquet storage, 3-year historical fetch
- **Indicators**: Bollinger Bands, ATR, EMA crossover
- **Regime detection**: Ranging / trending / neutral classification with session filtering
- **Strategy**: BB reversion entries with H1 regime confirmation
- **Backtesting**: Bar-by-bar simulator with full metrics (Sharpe, drawdown, profit factor)
- **Optimization**: Grid search with IS/OOS validation
- **Live engine**: 60s polling, paper/live modes, dual gate for safety
- **Telegram alerts**: Startup, signal, and error notifications
- **VPS tools**: `vps_check`, `keep_alive` for deployment

## Quick Start

```bash
# Clone
git clone https://github.com/sia12-web/BB-Strategy.git
cd BB-Strategy

# Setup
cp .env.example .env
# Edit .env with OANDA_API_KEY, OANDA_ACCOUNT_ID

pip install -r requirements.txt

# Run
python -m bb_strategy.live.run_live      # Live signal engine
python -m bb_strategy.live.vps_check     # VPS readiness check
python -m bb_strategy.live.keep_alive    # Keep-alive with auto-restart
```

## Documentation

See [CONTEXT.md](CONTEXT.md) for full architecture, parameters, and phase history.
