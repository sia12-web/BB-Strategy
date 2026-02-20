"""BacktestResult: aggregate stats from a completed backtest run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from bb_strategy.backtest.trade import Trade
from bb_strategy.backtest.metrics import (
    calc_max_drawdown,
    calc_profit_factor,
    calc_sharpe,
)


@dataclass
class BacktestResult:
    """Aggregated performance for a single pair backtest."""

    pair: str
    trades: List[Trade]
    initial_balance: float
    final_balance: float
    equity_curve: List[float] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def total_return_pct(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return (self.final_balance - self.initial_balance) / self.initial_balance * 100

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.is_winner) / len(self.trades)

    @property
    def profit_factor(self) -> float:
        return calc_profit_factor(self.trades)

    @property
    def max_drawdown_pct(self) -> float:
        return calc_max_drawdown(self.equity_curve) * 100

    @property
    def sharpe_ratio(self) -> float:
        if not self.trades:
            return 0.0
        # Build daily returns from equity curve diffs
        if len(self.equity_curve) < 2:
            return 0.0
        eq = np.array(self.equity_curve)
        daily_returns = np.diff(eq) / eq[:-1]
        return calc_sharpe(daily_returns.tolist(), periods_per_year=252.0)

    @property
    def avg_pips_per_trade(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.pnl_pips for t in self.trades) / len(self.trades)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Return a dict of all key metrics."""
        return {
            "pair": self.pair,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4) if self.profit_factor != float("inf") else "inf",
            "total_return_pct": round(self.total_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "avg_pips_per_trade": round(self.avg_pips_per_trade, 2),
            "initial_balance": self.initial_balance,
            "final_balance": round(self.final_balance, 2),
        }
