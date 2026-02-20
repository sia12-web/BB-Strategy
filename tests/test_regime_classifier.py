"""Tests for RegimeClassifier."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.regime.regime_classifier import RegimeClassifier


def _base_df(n: int = 50) -> pd.DataFrame:
    """Minimal df with required indicator columns."""
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-15 10:00", periods=n, freq="h"),
            "close": np.linspace(1.09, 1.10, n),
            "bb_width": np.full(n, 0.001),    # low by default
            "atr_ratio": np.full(n, 0.8),     # low by default
            "ema_cross": np.ones(n),           # stable by default
        }
    )


def test_regime_column_only_valid_values():
    """regime column contains only 'ranging', 'trending', or 'neutral'."""
    df = _base_df(100)
    # Mix some variation so we get multiple regimes
    df.loc[50:60, "atr_ratio"] = 2.0  # high → trending
    df.loc[70, "ema_cross"] = -1       # flip → trending

    result = RegimeClassifier().classify(df)
    assert result["regime"].isin(RegimeClassifier.VALID_REGIMES).all()


def test_ranging_requires_low_bb_width_and_atr():
    """Ranging needs low bb_width, low atr_ratio, AND stable ema_cross."""
    df = _base_df(10)
    # All conditions met: low bb_width, low atr_ratio, stable ema_cross
    result = RegimeClassifier(
        bb_width_threshold=0.002, atr_ratio_threshold=0.9
    ).classify(df)

    # After warmup (first 2 rows need rolling(3)), rows 2+ should be ranging
    assert (result["regime"].iloc[2:] == "ranging").all()


def test_trending_on_ema_cross():
    """A flip in ema_cross within last 2 bars → trending."""
    df = _base_df(10)
    df["ema_cross"] = 1
    df.loc[df.index[-1], "ema_cross"] = -1  # flip on last bar

    result = RegimeClassifier().classify(df)
    assert result["regime"].iloc[-1] == "trending"


def test_trending_on_high_atr():
    """atr_ratio > threshold * 1.5 → trending regardless of other conditions."""
    df = _base_df(10)
    df["atr_ratio"] = 2.0  # way above 0.9 * 1.5 = 1.35

    result = RegimeClassifier(atr_ratio_threshold=0.9).classify(df)
    assert (result["regime"] == "trending").all()


def test_neutral_when_mixed():
    """Neither fully ranging nor trending → neutral."""
    df = _base_df(10)
    # High bb_width (not ranging) but stable ema + moderate atr (not trending)
    df["bb_width"] = 0.005
    df["atr_ratio"] = 1.0  # above 0.9 but below 0.9*1.5=1.35

    result = RegimeClassifier(
        bb_width_threshold=0.002, atr_ratio_threshold=0.9
    ).classify(df)

    # Should be neutral (bb_width too high for ranging, atr not high enough for trending)
    assert (result["regime"].iloc[2:] == "neutral").all()


def test_dead_market_classified_as_neutral():
    """Construct df with bb_width below floor, assert regime == 'neutral'."""
    df = _base_df(10)
    df["bb_width"] = 0.0003  # Below default 0.0008 floor
    
    result = RegimeClassifier(min_bb_width=0.0008).classify(df)
    # Ranging conditions (stable EMA, low ATR) met, but width too low
    assert (result["regime"].iloc[2:] == "neutral").all()

def test_ranging_requires_width_above_floor():
    """bb_width=0.0009 with floor=0.0008, assert regime can be 'ranging'."""
    df = _base_df(10)
    df["bb_width"] = 0.0009
    
    result = RegimeClassifier(min_bb_width=0.0008).classify(df)
    assert (result["regime"].iloc[2:] == "ranging").all()

def test_ranging_requires_width_below_ceiling():
    """bb_width=0.005 above ceiling, assert regime != 'ranging'."""
    df = _base_df(10)
    df["bb_width"] = 0.005
    
    result = RegimeClassifier(bb_width_threshold=0.002).classify(df)
    assert (result["regime"].iloc[2:] != "ranging").all()

def test_init_validates_floor_ceiling():
    """Raise ValueError if floor >= ceiling."""
    with pytest.raises(ValueError, match="must be less than"):
        RegimeClassifier(bb_width_threshold=0.002, min_bb_width=0.002)

def test_raises_on_missing_columns():
    """Raise ValueError if indicator columns are absent."""
    df = pd.DataFrame({"close": [1.0]})
    with pytest.raises(ValueError, match="Missing required indicator columns"):
        RegimeClassifier().classify(df)
