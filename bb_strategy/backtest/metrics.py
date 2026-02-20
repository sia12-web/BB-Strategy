"""Standalone metric functions for backtest analysis."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from bb_strategy.backtest.trade import Trade


def calc_max_drawdown(equity_curve: list[float]) -> float:
    """Return maximum drawdown as a fraction (0–1).

    Tracks running peak; max drop from peak → trough.
    Returns 0.0 if equity never declines.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak != 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd


def calc_sharpe(returns: list[float], periods_per_year: float = 252.0) -> float:
    """Annualised Sharpe ratio (risk-free rate = 0).

    Args:
        returns: List of per-period returns (e.g. daily).
        periods_per_year: Annualisation factor. 252 for daily trading.

    Returns:
        Sharpe ratio, or 0.0 if insufficient data.
    """
    if len(returns) < 2:
        return 0.0

    arr = np.array(returns, dtype=float)
    mean = arr.mean()
    std = arr.std(ddof=1)

    if std == 0:
        return 0.0

    return float((mean / std) * math.sqrt(periods_per_year))


def calc_profit_factor(trades: list["Trade"]) -> float:
    """Gross profit / gross loss.  Returns inf if no losing trades, 0 if no winners."""
    gross_profit = sum(t.pnl_usd for t in trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in trades if t.pnl_usd < 0))

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss
