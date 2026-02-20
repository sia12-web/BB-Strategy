"""Tests for run_full_backtest integration."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from bb_strategy.backtest.run_backtest import run_full_backtest
from bb_strategy.backtest.backtest_result import BacktestResult
from bb_strategy.config import Config


def _synthetic_ohlcv(n: int, freq: str, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    rng = np.random.default_rng(seed)
    close = 1.1000 + np.cumsum(rng.normal(0, 0.0005, n))
    high = close + rng.uniform(0.0003, 0.0015, n)
    low = close - rng.uniform(0.0003, 0.0015, n)
    opn = close + rng.normal(0, 0.0003, n)
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-15", periods=n, freq=freq),
            "open": opn,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(500, 5000, n).astype(float),
        }
    )


@patch("bb_strategy.backtest.run_backtest.DataStore")
def test_full_backtest_returns_result_for_all_pairs(mock_store_cls):
    """Full backtest returns a BacktestResult for every pair."""
    # Mock DataStore to return synthetic data
    h1_data = _synthetic_ohlcv(200, "h", seed=42)
    m15_data = _synthetic_ohlcv(200, "15min", seed=99)
    # Align M15 to start after H1 start
    m15_data["time"] = pd.date_range(h1_data["time"].iloc[1], periods=200, freq="15min")

    mock_store = MagicMock()
    mock_store.load.side_effect = lambda pair, tf, **kwargs: h1_data.copy() if tf == "H1" else m15_data.copy()
    mock_store_cls.return_value = mock_store

    pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]
    cfg = Config(OANDA_API_KEY="fake", OANDA_ACCOUNT_ID="fake")

    results = run_full_backtest(pairs=pairs, initial_balance=10_000, config=cfg)

    assert len(results) == 4
    for pair in pairs:
        assert pair in results
        assert isinstance(results[pair], BacktestResult)
        # Check summary is well-formed
        s = results[pair].summary()
        assert "total_trades" in s
        assert "win_rate" in s
@patch("bb_strategy.backtest.run_backtest.DataStore")
def test_data_suffix_loads_correct_file(mock_store_cls):
    """run_backtest passes the data_suffix down to store.load."""
    mock_store = MagicMock()
    mock_store.load.return_value = _synthetic_ohlcv(50, "h")
    mock_store_cls.return_value = mock_store

    from bb_strategy.backtest.run_backtest import run_backtest
    run_backtest("EUR_USD", data_suffix="_3y")

    # Assert load was called with suffix="_3y"
    mock_store.load.assert_any_call("EUR_USD", "H1", suffix="_3y")
    mock_store.load.assert_any_call("EUR_USD", "M15", suffix="_3y")


def test_invalid_data_suffix_raises_error():
    """run_backtest raises ValueError for unapproved suffixes."""
    from bb_strategy.backtest.run_backtest import run_backtest
    with pytest.raises(ValueError, match="data_suffix must be one of"):
        run_backtest("EUR_USD", data_suffix="_unauthorized")
