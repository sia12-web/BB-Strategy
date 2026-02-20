"""Tests for BacktestEngine bar-by-bar simulation."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.backtest.backtest_engine import BacktestEngine


def _signals_df(
    n: int = 20,
    signal_at: int = 5,
    direction: int = 1,
    entry_price: float = 1.0950,
    stop_loss: float = 1.0935,
    take_profit: float = 1.0970,
) -> pd.DataFrame:
    """Build a minimal signals DataFrame with one entry signal."""
    close = np.full(n, entry_price)
    high = close + 0.0005
    low = close - 0.0005

    df = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-15 05:00", periods=n, freq="15min"),
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(n, 1000.0),
            "signal": np.zeros(n, dtype=int),
            "signal_type": "none",
            "entry_price": np.full(n, np.nan),
            "stop_loss": np.full(n, np.nan),
            "take_profit": np.full(n, np.nan),
            "exit_signal": np.zeros(n, dtype=int),
        }
    )

    # Insert the signal
    df.loc[signal_at, "signal"] = direction
    df.loc[signal_at, "entry_price"] = entry_price
    df.loc[signal_at, "stop_loss"] = stop_loss
    df.loc[signal_at, "take_profit"] = take_profit

    return df


# ------------------------------------------------------------------
# SL / TP tests
# ------------------------------------------------------------------


def test_sl_hit_closes_trade():
    """Bar low goes below SL → trade closed with exit_reason='stop_loss'."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    # Bar after entry: low drops to SL
    df.loc[6, "low"] = 1.0930  # below SL of 1.0935

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "stop_loss"
    assert result.trades[0].status == "closed"


def test_tp_hit_closes_trade():
    """Bar high exceeds TP → trade closed with exit_reason='take_profit'."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    # Bar after entry: high reaches TP
    df.loc[6, "high"] = 1.0975  # above TP of 1.0970

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "take_profit"


def test_sl_wins_when_both_hit_same_bar():
    """If SL and TP both hit on same bar, SL wins (conservative)."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    # Bar after entry: both extremes hit
    df.loc[6, "low"] = 1.0930   # below SL
    df.loc[6, "high"] = 1.0975  # above TP

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert result.trades[0].exit_reason == "stop_loss"


def test_no_concurrent_trades():
    """Two consecutive signals: only first opens while it's still open."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    # Second signal on next bar — should be ignored (trade still open)
    df.loc[6, "signal"] = 1
    df.loc[6, "entry_price"] = 1.0960
    df.loc[6, "stop_loss"] = 1.0945
    df.loc[6, "take_profit"] = 1.0980

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    # Only one trade — the first signal's trade (closed at end_of_data)
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 1.0950


def test_balance_increases_on_winning_trade():
    """TP hit → final balance > initial balance."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    df.loc[6, "high"] = 1.0975  # TP hit

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert result.final_balance > 10_000
    assert result.trades[0].pnl_usd > 0


def test_balance_decreases_on_losing_trade():
    """SL hit → final balance < initial balance."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    df.loc[6, "low"] = 1.0930  # SL hit

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert result.final_balance < 10_000
    assert result.trades[0].pnl_usd < 0


def test_exit_signal_closes_trade():
    """exit_signal=1 closes the trade at bar close."""
    df = _signals_df(signal_at=5, direction=1, entry_price=1.0950, stop_loss=1.0935, take_profit=1.0970)
    df.loc[7, "exit_signal"] = 1

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "exit_signal"


def test_short_sl_above_entry():
    """Short trade: SL hit when bar high >= stop_loss."""
    df = _signals_df(
        signal_at=5, direction=-1,
        entry_price=1.0950, stop_loss=1.0965, take_profit=1.0930,
    )
    df.loc[6, "high"] = 1.0970  # above SL for short

    engine = BacktestEngine(initial_balance=10_000, risk_pct=0.01)
    result = engine.run("EUR_USD", df)

    assert result.trades[0].exit_reason == "stop_loss"
    assert result.trades[0].pnl_usd < 0


def test_raises_on_invalid_params():
    """Reject invalid initial_balance or risk_pct."""
    with pytest.raises(ValueError):
        BacktestEngine(initial_balance=-1000)
    with pytest.raises(ValueError):
        BacktestEngine(risk_pct=0.10)
