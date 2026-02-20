"""Tests for IndicatorEngine orchestrator."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.indicators.indicator_engine import IndicatorEngine


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


def test_run_adds_all_columns():
    """IndicatorEngine.run() adds all 10 indicator columns."""
    engine = IndicatorEngine()
    df = _synthetic_ohlcv(200)
    result = engine.run("EUR_USD", "H1", df)

    for col in IndicatorEngine.INDICATOR_COLUMNS:
        assert col in result.columns, f"Missing indicator column: {col}"


def test_no_nan_after_warmup():
    """No NaN values after the warmup period (first 21 rows)."""
    engine = IndicatorEngine()
    df = _synthetic_ohlcv(200)
    result = engine.run("EUR_USD", "H1", df)

    # Warmup = max(bb_period=20, atr_period=14+20 for atr_ratio, ema_slow=21)
    # ATR needs period(14) rows for atr, then 20 more for atr_ratio = 33 rows warmup
    after_warmup = result.iloc[33:]
    indicator_cols = IndicatorEngine.INDICATOR_COLUMNS
    nulls = after_warmup[indicator_cols].isnull().sum()
    assert nulls.sum() == 0, f"NaN values found after warmup:\n{nulls[nulls > 0]}"


def test_unknown_pair_raises():
    """IndicatorEngine raises ValueError for unconfigured pair."""
    engine = IndicatorEngine()
    df = _synthetic_ohlcv(50)
    with pytest.raises(ValueError, match="No indicator config"):
        engine.run("UNKNOWN_PAIR", "H1", df)


def test_gbpjpy_uses_wider_bands():
    """GBP_JPY should use std_dev=2.5 producing wider bands than EUR_USD."""
    engine = IndicatorEngine()
    df = _synthetic_ohlcv(200)

    eur = engine.run("EUR_USD", "H1", df.copy())
    gbp = engine.run("GBP_JPY", "H1", df.copy())

    valid = ~eur["bb_width"].isna()
    # Same data → wider std_dev → wider bands
    assert (gbp.loc[valid, "bb_width"] >= eur.loc[valid, "bb_width"]).all()
