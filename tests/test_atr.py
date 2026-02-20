"""Tests for ATR indicator."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.indicators.atr import ATR


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


def test_atr_positive():
    """ATR should be > 0 for all non-NaN rows."""
    df = _synthetic_ohlcv(200)
    result = ATR(period=14).calculate(df)
    valid = result["atr"].dropna()
    assert (valid > 0).all()


def test_atr_ratio_reasonable():
    """ATR ratio should be between 0.1 and 10.0 for normal data."""
    df = _synthetic_ohlcv(200)
    result = ATR(period=14).calculate(df)
    valid = result["atr_ratio"].dropna()
    assert (valid > 0.1).all()
    assert (valid < 10.0).all()


def test_atr_columns_present():
    """Both atr and atr_ratio columns are added."""
    df = _synthetic_ohlcv(50)
    result = ATR().calculate(df)
    assert "atr" in result.columns
    assert "atr_ratio" in result.columns
