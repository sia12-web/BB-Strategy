"""Collect all data needed for the HTML report."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from bb_strategy.config import Config
from bb_strategy.data.data_store import DataStore
from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.regime.regime_engine import RegimeEngine
from bb_strategy.strategy.strategy_engine import StrategyEngine
from bb_strategy.backtest.backtest_engine import BacktestEngine
from bb_strategy.backtest.backtest_result import BacktestResult
from bb_strategy.backtest.trade import Trade

logger = logging.getLogger(__name__)

# Keys that must never appear in report output
_FORBIDDEN = {"api_key", "account_id", "access_token", "secret"}


class ReportData:
    """Assemble all data for the dashboard report."""

    def __init__(
        self,
        config: Optional[Config] = None,
        initial_balance: float = 10_000.0,
        risk_pct: float = 0.01,
        data_suffix: str = "_3y",
    ) -> None:
        self.config = config or Config()
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.data_suffix = data_suffix

    def collect(self, pairs: Optional[list[str]] = None) -> dict[str, Any]:
        """Run backtests and collect all report data.

        Returns a dict with keys:
        - pairs: dict[pair_name -> pair_data]
        - optimization: dict or None
        - generated_at: timestamp str
        """
        pairs = pairs or self.config.PAIRS
        store = DataStore(self.config.DATA_DIR)
        strategy = StrategyEngine()

        pair_results: dict[str, dict] = {}

        for pair in pairs:
            logger.info("Collecting report data for %s", pair)
            try:
                h1_df = store.load(pair, "H1", suffix=self.data_suffix)
                m15_df = store.load(pair, "M15", suffix=self.data_suffix)

                signals_df = strategy.run(pair, h1_df, m15_df)
                bt = BacktestEngine(
                    initial_balance=self.initial_balance,
                    risk_pct=self.risk_pct,
                )
                result = bt.run(pair, signals_df)

                pair_results[pair] = self._result_to_dict(result)
            except Exception as e:
                logger.warning("Failed to collect data for %s: %s", pair, e)
                pair_results[pair] = self._empty_pair(pair, str(e))

        # Load optimization results if available
        opt_summary = self._load_optimization_summary()

        report = {
            "pairs": pair_results,
            "optimization": opt_summary,
            "generated_at": pd.Timestamp.now().isoformat(),
        }

        self._sanitize(report)
        return report

    # ------------------------------------------------------------------
    # Converters
    # ------------------------------------------------------------------

    def _result_to_dict(self, result: BacktestResult) -> dict:
        """Convert BacktestResult to report-friendly dict."""
        trades = result.trades
        trade_dicts = [self._trade_to_dict(t) for t in trades]

        # Average trade duration (hours)
        durations = []
        for t in trades:
            if t.exit_time and t.entry_time:
                dur = (t.exit_time - t.entry_time).total_seconds() / 3600
                durations.append(dur)
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Best / worst trade
        pnls = [t.pnl_usd for t in trades]
        best_trade = max(pnls) if pnls else 0.0
        worst_trade = min(pnls) if pnls else 0.0

        return {
            "pair": result.pair,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "sharpe": result.sharpe_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "profit_factor": result.profit_factor,
            "total_return_pct": result.total_return_pct,
            "avg_pips_per_trade": result.avg_pips_per_trade,
            "avg_duration_hours": round(avg_duration, 2),
            "best_trade_usd": round(best_trade, 2),
            "worst_trade_usd": round(worst_trade, 2),
            "initial_balance": result.initial_balance,
            "final_balance": round(result.final_balance, 2),
            "equity_curve": result.equity_curve,
            "trades": trade_dicts,
            "has_data": True,
        }

    @staticmethod
    def _trade_to_dict(t: Trade) -> dict:
        return {
            "pair": t.pair,
            "direction": "long" if t.direction == 1 else "short",
            "entry_time": str(t.entry_time) if t.entry_time else None,
            "entry_price": t.entry_price,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "units": t.units,
            "exit_time": str(t.exit_time) if t.exit_time else None,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "pnl_pips": round(t.pnl_pips, 2),
            "pnl_usd": round(t.pnl_usd, 2),
        }

    @staticmethod
    def _empty_pair(pair: str, error: str) -> dict:
        return {
            "pair": pair,
            "total_trades": 0,
            "win_rate": 0,
            "sharpe": 0,
            "max_drawdown_pct": 0,
            "profit_factor": 0,
            "total_return_pct": 0,
            "avg_pips_per_trade": 0,
            "avg_duration_hours": 0,
            "best_trade_usd": 0,
            "worst_trade_usd": 0,
            "initial_balance": 0,
            "final_balance": 0,
            "equity_curve": [],
            "trades": [],
            "has_data": False,
            "error": error,
        }

    def _load_optimization_summary(self) -> Optional[dict]:
        path = self.config.DATA_DIR / "optimization_results.json"
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _sanitize(data: dict) -> None:
        """Recursively strip credential-like keys."""
        if isinstance(data, dict):
            for key in list(data.keys()):
                if any(f in key.lower() for f in _FORBIDDEN):
                    del data[key]
                else:
                    ReportData._sanitize(data[key])
        elif isinstance(data, list):
            for item in data:
                ReportData._sanitize(item)
