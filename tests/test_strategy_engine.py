"""Tests for StrategyEngine full-stack orchestration."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.strategy.strategy_engine import StrategyEngine


def _synthetic_ohlcv(n: int, freq: str, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV with realistic price movement."""
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


def test_run_returns_signal_columns():
    """Full stack: StrategyEngine.run adds all signal columns with valid values."""
    # H1 = 200 bars, M15 = 200 bars (M15 is subset time-wise)
    h1 = _synthetic_ohlcv(200, "h", seed=42)
    # M15 starts 1h after H1 to ensure H1 covers M15 range
    m15 = _synthetic_ohlcv(200, "15min", seed=99)
    m15["time"] = pd.date_range(
        h1["time"].iloc[1], periods=200, freq="15min",
    )

    engine = StrategyEngine()
    result = engine.run("EUR_USD", h1, m15)

    for col in StrategyEngine.SIGNAL_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"

    # signal values must be in {-1, 0, 1}
    assert result["signal"].isin([-1, 0, 1]).all()

    # signal_type must match signal
    longs = result[result["signal"] == 1]
    shorts = result[result["signal"] == -1]
    no_sigs = result[result["signal"] == 0]

    if len(longs):
        assert (longs["signal_type"] == "long").all()
    if len(shorts):
        assert (shorts["signal_type"] == "short").all()
    assert (no_sigs["signal_type"] == "none").all()


def test_all_pairs_run_without_error():
    """StrategyEngine should work for all configured pairs."""
    h1 = _synthetic_ohlcv(200, "h", seed=42)
    m15 = _synthetic_ohlcv(200, "15min", seed=99)
    m15["time"] = pd.date_range(h1["time"].iloc[1], periods=200, freq="15min")

    engine = StrategyEngine()
    for pair in ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]:
        result = engine.run(pair, h1.copy(), m15.copy())
        assert "signal" in result.columns
