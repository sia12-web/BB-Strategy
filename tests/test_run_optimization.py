"""Tests for run_all_pairs optimization runner."""

import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory

from bb_strategy.optimization.run_optimization import run_all_pairs
from bb_strategy.optimization.optimization_result import OptimizationResult
from bb_strategy.config import Config


def _synthetic_ohlcv(n: int, freq: str, seed: int = 42) -> pd.DataFrame:
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


@patch("bb_strategy.optimization.run_optimization.DataStore")
@patch("bb_strategy.optimization.run_optimization.Optimizer")
def test_output_file_created(mock_optimizer_cls, mock_store_cls):
    """run_all_pairs creates optimization_results.json."""
    with TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "optimization_results.json"

        # Mock optimizer to return a valid result
        mock_result = OptimizationResult(
            pair="EUR_USD",
            best_params={"bb_period": 20},
            in_sample_sharpe=1.0,
            out_of_sample_sharpe=0.5,
            out_of_sample_win_rate=0.55,
            out_of_sample_profit_factor=1.5,
            total_combinations_tested=10,
            in_sample_trades=80,
            out_of_sample_trades=30,
            passed_validation=True,
        )

        mock_opt_instance = MagicMock()
        mock_opt_instance.run.return_value = mock_result
        mock_optimizer_cls.return_value = mock_opt_instance

        # Mock store
        h1_data = _synthetic_ohlcv(200, "h")
        m15_data = _synthetic_ohlcv(200, "15min", seed=99)
        mock_store = MagicMock()
        mock_store.load.side_effect = lambda p, tf: h1_data.copy() if tf == "H1" else m15_data.copy()
        mock_store_cls.return_value = mock_store

        cfg = Config(OANDA_API_KEY="fake", OANDA_ACCOUNT_ID="fake")

        results = run_all_pairs(
            pairs=["EUR_USD"],
            config=cfg,
            output_path=out_path,
        )

        # File created
        assert out_path.exists()

        # Readable JSON
        with open(out_path) as f:
            data = json.load(f)

        assert "EUR_USD" in data
        assert data["EUR_USD"]["passed_validation"] is True

        # No credentials leaked
        raw = out_path.read_text()
        assert "fake" not in raw  # API key shouldn't be in output
