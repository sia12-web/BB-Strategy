"""Tests for RegimeEngine orchestrator."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.regime.regime_engine import RegimeEngine


def _synthetic_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV with UTC timestamps."""
    rng = np.random.default_rng(seed)
    close = 1.1000 + np.cumsum(rng.normal(0, 0.001, n))
    high = close + rng.uniform(0.0005, 0.002, n)
    low = close - rng.uniform(0.0005, 0.002, n)
    opn = close + rng.normal(0, 0.0005, n)
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-15", periods=n, freq="h"),
            "open": opn,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(500, 5000, n).astype(float),
        }
    )


def test_run_adds_regime_and_session_columns():
    """Full pipeline: indicators → regime engine adds all expected columns."""
    df = _synthetic_ohlcv(200)

    # First compute indicators
    ind_engine = IndicatorEngine()
    df = ind_engine.run("EUR_USD", "H1", df)

    # Then classify regime
    reg_engine = RegimeEngine()
    result = reg_engine.run("EUR_USD", "H1", df)

    for col in RegimeEngine.REGIME_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"

    # No nulls in regime/session columns
    assert result["regime"].notna().all()
    assert result["session"].notna().all()
    assert result["tradeable_session"].notna().all()


def test_all_pairs_supported():
    """RegimeEngine should work for every configured pair."""
    df = _synthetic_ohlcv(200)
    ind_engine = IndicatorEngine()
    reg_engine = RegimeEngine()

    for pair in ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]:
        enriched = ind_engine.run(pair, "H1", df.copy())
        result = reg_engine.run(pair, "H1", enriched)
        assert "regime" in result.columns
        assert "session" in result.columns


def test_unknown_pair_raises():
    """RegimeEngine raises ValueError for unconfigured pair."""
    df = _synthetic_ohlcv(50)
    with pytest.raises(ValueError, match="No regime config"):
        RegimeEngine().run("UNKNOWN", "H1", df)
