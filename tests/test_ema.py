"""Tests for EMA crossover indicator."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.indicators.ema import EMA


def _synthetic_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 1.1000 + np.cumsum(rng.normal(0, 0.001, n))
    high = close + rng.uniform(0.0005, 0.002, n)
    low = close - rng.uniform(0.0005, 0.002, n)
    opn = close + rng.normal(0, 0.0005, n)
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=n, freq="h"),
            "open": opn,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(500, 5000, n).astype(float),
        }
    )


def test_ema_cross_values():
    """ema_cross should only contain +1 or -1 (no NaN after warmup)."""
    df = _synthetic_ohlcv(200)
    result = EMA(fast=8, slow=21).calculate(df)
    # EWM produces values from row 0, so no NaN at all
    assert result["ema_cross"].isin([1, -1]).all()


def test_ema_columns_present():
    """All three EMA columns are added."""
    df = _synthetic_ohlcv(50)
    result = EMA().calculate(df)
    for col in ["ema_fast", "ema_slow", "ema_cross"]:
        assert col in result.columns


def test_ema_fast_reacts_quicker():
    """Fast EMA should react more to recent changes than slow EMA."""
    # Create a series that jumps up sharply at the end
    df = _synthetic_ohlcv(100)
    df.loc[df.index[-10:], "close"] = df["close"].iloc[-10:] + 0.05
    result = EMA(fast=8, slow=21).calculate(df)
    # After a big jump, fast EMA should be above slow
    assert result["ema_cross"].iloc[-1] == 1
