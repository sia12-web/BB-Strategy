"""Tests for Optimizer: data splitting, grid search, validation gates."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from bb_strategy.optimization.optimizer import Optimizer
from bb_strategy.optimization.optimization_result import OptimizationResult


def _synthetic_ohlcv(n: int, freq: str, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV with realistic movement."""
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


def test_data_split_is_chronological():
    """In-sample end date must be < out-of-sample start date."""
    h1 = _synthetic_ohlcv(200, "h", seed=42)
    m15 = _synthetic_ohlcv(200, "15min", seed=99)
    m15["time"] = pd.date_range(h1["time"].iloc[1], periods=200, freq="15min")

    opt = Optimizer(pair="EUR_USD", h1_df=h1, m15_df=m15, data_split=0.7)

    # Access the private split method
    h1_is, h1_oos, m15_is, m15_oos = opt._split_data()

    # Chronological: last in-sample time <= first out-of-sample time (if overlap exists at boundary)
    # Actually, with self.m15_base["time"] > split_time, it should be strictly less for is_df[-1]
    assert m15_is["time"].iloc[-1] < m15_oos["time"].iloc[0]
    # Sizes approximately match split ratio
    total = len(m15)
    assert len(m15_is) == int(total * 0.7) + 1 # +1 because of <= split_time
    assert len(m15_oos) == total - (int(total * 0.7) + 1)


def test_optimization_result_has_required_fields():
    """Run optimizer with small grid on synthetic data, check result fields."""
    h1 = _synthetic_ohlcv(300, "h", seed=42)
    m15 = _synthetic_ohlcv(300, "15min", seed=99)
    m15["time"] = pd.date_range(h1["time"].iloc[1], periods=300, freq="15min")

    # Use a small custom grid to keep test fast
    small_grid = [
        {
            "bb_period": 20, "bb_std_dev": 2.0, "atr_period": 14,
            "bb_width_threshold": 0.002, "atr_ratio_threshold": 0.9,
            "ema_fast": 8, "ema_slow": 21,
        },
        {
            "bb_period": 15, "bb_std_dev": 1.8, "atr_period": 10,
            "bb_width_threshold": 0.0025, "atr_ratio_threshold": 1.0,
            "ema_fast": 8, "ema_slow": 21,
        },
    ]

    with patch(
        "bb_strategy.optimization.optimizer.get_grid_for_pair",
        return_value=small_grid,
    ):
        opt = Optimizer(pair="EUR_USD", h1_df=h1, m15_df=m15)
        result = opt.run()

    assert isinstance(result, OptimizationResult)
    assert result.pair == "EUR_USD"
    assert result.total_combinations_tested == 2
    assert isinstance(result.passed_validation, bool)
    assert isinstance(result.in_sample_sharpe, float)
    assert isinstance(result.out_of_sample_sharpe, float)


def test_failed_validation_sets_passed_false():
    """When OOS Sharpe is below threshold, passed_validation should be False."""
    h1 = _synthetic_ohlcv(300, "h", seed=42)
    m15 = _synthetic_ohlcv(300, "15min", seed=99)
    m15["time"] = pd.date_range(h1["time"].iloc[1], periods=300, freq="15min")

    small_grid = [
        {
            "bb_period": 20, "bb_std_dev": 2.0, "atr_period": 14,
            "bb_width_threshold": 0.002, "atr_ratio_threshold": 0.9,
            "ema_fast": 8, "ema_slow": 21,
        },
    ]

    # Mock the backtest to return low Sharpe
    mock_result = MagicMock()
    mock_result.sharpe_ratio = 0.1  # below 0.3 threshold
    mock_result.win_rate = 0.3      # below 0.4 threshold
    mock_result.total_trades = 60
    mock_result.profit_factor = 0.5

    with patch(
        "bb_strategy.optimization.optimizer.get_grid_for_pair",
        return_value=small_grid,
    ), patch.object(
        Optimizer, "_backtest_with_params", return_value=mock_result,
    ):
        opt = Optimizer(pair="EUR_USD", h1_df=h1, m15_df=m15)
        result = opt.run()

    assert result.passed_validation is False
@patch("bb_strategy.optimization.optimizer.get_grid_for_pair")
def test_min_trades_gate_is_20(mock_grid):
    """Optimizer rejects if IS trades < 20, accepts if >= 20."""
    h1 = _synthetic_ohlcv(300, "h")
    m15 = _synthetic_ohlcv(300, "15min")
    mock_grid.return_value = [{"one": 1}]

    # 1. Test rejection (19 trades)
    res_19 = MagicMock()
    res_19.total_trades = 19
    res_19.sharpe_ratio = 1.0

    with patch.object(Optimizer, "_backtest_with_params", return_value=res_19):
        opt = Optimizer(pair="EUR_USD", h1_df=h1, m15_df=m15)
        result = opt.run()
        assert result.passed_validation is False
        assert "produced >= 20 trades" in result.rejection_reason

    # 2. Test acceptance (20 trades)
    res_20 = MagicMock()
    res_20.total_trades = 20
    res_20.sharpe_ratio = 1.0
    res_20.win_rate = 0.5
    res_20.profit_factor = 2.0

    with patch.object(Optimizer, "_backtest_with_params", side_effect=[res_20, res_20]):
        opt = Optimizer(pair="EUR_USD", h1_df=h1, m15_df=m15)
        result = opt.run()
        assert result.passed_validation is True
        assert result.in_sample_trades == 20
