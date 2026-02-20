"""Tests for ReportData collection."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from bb_strategy.reporting.report_data import ReportData
from bb_strategy.config import Config


def _synthetic_ohlcv(n: int, freq: str, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 1.1000 + np.cumsum(rng.normal(0, 0.0005, n))
    high = close + rng.uniform(0.0003, 0.0015, n)
    low = close - rng.uniform(0.0003, 0.0015, n)
    return pd.DataFrame({
        "time": pd.date_range("2024-01-15", periods=n, freq=freq),
        "open": close + rng.normal(0, 0.0003, n),
        "high": high, "low": low, "close": close,
        "volume": rng.integers(500, 5000, n).astype(float),
    })


@patch("bb_strategy.reporting.report_data.DataStore")
@patch("bb_strategy.reporting.report_data.StrategyEngine")
@patch("bb_strategy.reporting.report_data.BacktestEngine")
def test_collect_returns_all_pairs(mock_bt_cls, mock_strat_cls, mock_store_cls):
    """collect() returns data for all 4 pairs."""
    h1 = _synthetic_ohlcv(200, "h")
    m15 = _synthetic_ohlcv(200, "15min", seed=99)
    m15["time"] = pd.date_range(h1["time"].iloc[1], periods=200, freq="15min")

    mock_store = MagicMock()
    mock_store.load.side_effect = lambda p, tf: h1.copy() if tf == "H1" else m15.copy()
    mock_store_cls.return_value = mock_store

    # Mock strategy to return a signals_df
    signals_df = m15.copy()
    signals_df["signal"] = 0
    signals_df["signal_type"] = "none"
    signals_df["entry_price"] = np.nan
    signals_df["stop_loss"] = np.nan
    signals_df["take_profit"] = np.nan
    signals_df["exit_signal"] = 0

    mock_strat = MagicMock()
    mock_strat.run.return_value = signals_df
    mock_strat_cls.return_value = mock_strat

    # Mock backtest result
    from bb_strategy.backtest.backtest_result import BacktestResult
    mock_result = BacktestResult(
        pair="EUR_USD", trades=[], initial_balance=10000,
        final_balance=10000, equity_curve=[10000],
    )
    mock_bt = MagicMock()
    mock_bt.run.return_value = mock_result
    mock_bt_cls.return_value = mock_bt

    cfg = Config(OANDA_API_KEY="fake", OANDA_ACCOUNT_ID="fake")
    collector = ReportData(config=cfg)
    data = collector.collect(pairs=["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"])

    assert len(data["pairs"]) == 4
    for pair in ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]:
        assert pair in data["pairs"]
    assert "generated_at" in data
