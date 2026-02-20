"""Tests for Bollinger Bands indicator."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.indicators.bollinger import BollingerBands


def _synthetic_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data with realistic price movement."""
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


def test_bb_columns_exist():
    """All five Bollinger Band columns are added."""
    df = _synthetic_ohlcv(100)
    result = BollingerBands().calculate(df)
    for col in ["bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pct_b"]:
        assert col in result.columns, f"Missing column: {col}"


def test_bb_upper_always_above_lower():
    """Upper band >= lower band for every non-NaN row."""
    df = _synthetic_ohlcv(500)
    result = BollingerBands().calculate(df)
    valid = result.dropna(subset=["bb_upper", "bb_lower"])
    assert (valid["bb_upper"] >= valid["bb_lower"]).all()


def test_bb_middle_equals_sma():
    """Middle band should equal rolling mean of close."""
    df = _synthetic_ohlcv(100)
    result = BollingerBands(period=20).calculate(df)
    expected_sma = df["close"].rolling(20).mean()
    pd.testing.assert_series_equal(
        result["bb_middle"], expected_sma, check_names=False
    )


def test_bb_raises_on_missing_columns():
    """Raise ValueError if required OHLC columns are absent."""
    df = pd.DataFrame({"foo": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing required columns"):
        BollingerBands().calculate(df)
