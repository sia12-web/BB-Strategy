"""Tests for standalone metric functions."""

import math

import pytest

from bb_strategy.backtest.metrics import calc_max_drawdown, calc_sharpe, calc_profit_factor
from bb_strategy.backtest.trade import Trade
import pandas as pd


def _make_trade(pnl_usd: float) -> Trade:
    """Shortcut: closed Trade with given P&L."""
    t = Trade(
        pair="EUR_USD", direction=1,
        entry_time=pd.Timestamp("2024-01-15"),
        entry_price=1.10, stop_loss=1.09, take_profit=1.11,
        units=1000,
    )
    t.pnl_usd = pnl_usd
    t.status = "closed"
    return t


def test_max_drawdown_correct():
    """equity [100, 90, 95, 80, 85] → max DD = (100-80)/100 = 0.20"""
    equity = [100, 90, 95, 80, 85]
    assert abs(calc_max_drawdown(equity) - 0.20) < 1e-9


def test_max_drawdown_no_decline():
    """Monotonically increasing equity → DD = 0."""
    assert calc_max_drawdown([100, 110, 120]) == 0.0


def test_max_drawdown_empty():
    """Empty or single-element → 0."""
    assert calc_max_drawdown([]) == 0.0
    assert calc_max_drawdown([100]) == 0.0


def test_profit_factor_above_one_for_winning_trades():
    """3 winners + 1 loser → profit_factor > 1."""
    trades = [
        _make_trade(50.0),
        _make_trade(30.0),
        _make_trade(40.0),
        _make_trade(-20.0),
    ]
    pf = calc_profit_factor(trades)
    assert pf > 1.0
    # (50+30+40) / 20 = 6.0
    assert abs(pf - 6.0) < 1e-9


def test_profit_factor_no_losers():
    """All winners → inf."""
    trades = [_make_trade(50.0), _make_trade(30.0)]
    assert calc_profit_factor(trades) == float("inf")


def test_profit_factor_no_winners():
    """All losers → 0."""
    trades = [_make_trade(-10.0), _make_trade(-20.0)]
    assert calc_profit_factor(trades) == 0.0


def test_sharpe_positive_returns():
    """Positive consistent returns → positive Sharpe."""
    returns = [0.01, 0.02, 0.015, 0.01, 0.02, 0.012, 0.018]
    s = calc_sharpe(returns, periods_per_year=252)
    assert s > 0


def test_sharpe_zero_std():
    """All same return → std=0 → Sharpe=0."""
    returns = [0.01, 0.01, 0.01]
    assert calc_sharpe(returns) == 0.0
