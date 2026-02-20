"""Tests for FilterCounter stage counts."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from bb_strategy.diagnostics.filter_counter import FilterCounter


def _make_enriched_m15(n: int = 200) -> pd.DataFrame:
    """Create a synthetic M15 df that has been through indicators + regime.

    Designed so that some bars pass each filter stage, with counts
    strictly decreasing through the funnel.
    """
    times = pd.date_range("2024-01-15 05:00", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 1.0950)

    df = pd.DataFrame({
        "time": times,
        "open": close,
        "high": close + 0.001,
        "low": close - 0.001,
        "close": close,
        "volume": np.full(n, 1000.0),
        "bb_upper": np.full(n, 1.0980),
        "bb_lower": np.full(n, 1.0920),
        "bb_middle": np.full(n, 1.0950),
        "bb_width": np.full(n, 0.0055),
        "bb_pct_b": np.full(n, 0.50),
        "atr": np.full(n, 0.0010),
        "atr_ratio": np.full(n, 0.85),
        "ema_fast": close,
        "ema_slow": close - 0.0001,
        "ema_cross": np.ones(n),
        "session": "london",
        "tradeable_session": True,
        "regime": "ranging",
    })

    # Make ~half non-tradeable
    df.loc[n // 2:, "tradeable_session"] = False
    df.loc[n // 2:, "session"] = "new_york"

    # Make some bars near-band (bb_pct_b < 0.1)
    near_band_idx = list(range(10, 30))
    df.loc[near_band_idx, "bb_pct_b"] = 0.05

    # Create re-entry at specific bars: prev close below bb_lower, current above
    for i in [15, 20, 25]:
        df.loc[i - 1, "close"] = 1.0910    # below bb_lower
        df.loc[i, "close"] = 1.0925        # above bb_lower
        df.loc[i, "bb_pct_b"] = 0.04

    return df


def _make_enriched_h1(m15_df: pd.DataFrame) -> pd.DataFrame:
    """H1 df covering the M15 range, all ranging."""
    start = m15_df["time"].min() - pd.Timedelta(hours=1)
    end = m15_df["time"].max() + pd.Timedelta(hours=1)
    times = pd.date_range(start, end, freq="h", tz="UTC")
    return pd.DataFrame({
        "time": times,
        "regime": "ranging",
        # Add indicator columns that RegimeEngine expects
        "bb_width": 0.002,
        "atr_ratio": 0.8,
        "ema_cross": 1,
        "session": "london",
        "tradeable_session": True,
    })


class TestFilterCounterStageKeys:
    """test_returns_all_stage_keys"""

    def test_returns_all_stage_keys(self, tmp_path):
        """Output dict must have all expected keys."""
        m15 = _make_enriched_m15()
        h1 = _make_enriched_h1(m15)

        # Save to temp parquet files
        m15_path = tmp_path / "EUR_USD_M15_3y.parquet"
        h1_path = tmp_path / "EUR_USD_H1_3y.parquet"
        m15.to_parquet(m15_path, engine="pyarrow", index=False)
        h1.to_parquet(h1_path, engine="pyarrow", index=False)

        config = MagicMock()
        config.DATA_DIR = tmp_path

        # Mock the indicator + regime engines to pass data through
        indicator_engine = MagicMock()
        indicator_engine.run.side_effect = lambda pair, tf, df: df

        regime_engine = MagicMock()
        regime_engine.run.side_effect = lambda pair, tf, df: df
        regime_engine.pair_configs = {"EUR_USD": {"min_bb_width": 0.0008}}

        counter = FilterCounter(
            config=config,
            indicator_engine=indicator_engine,
            regime_engine=regime_engine,
        )
        result = counter.run("EUR_USD")

        expected_keys = {
            "total", "tradeable", "ranging", "volatility_floor",
            "near_band", "reentry", "signals"
        }
        assert set(result.keys()) == expected_keys


class TestFilterCounterMonotonicity:
    """test_each_stage_lte_previous"""

    def test_each_stage_lte_previous(self, tmp_path):
        """Each stage count must be <= the previous stage."""
        m15 = _make_enriched_m15()
        h1 = _make_enriched_h1(m15)

        m15_path = tmp_path / "EUR_USD_M15_3y.parquet"
        h1_path = tmp_path / "EUR_USD_H1_3y.parquet"
        m15.to_parquet(m15_path, engine="pyarrow", index=False)
        h1.to_parquet(h1_path, engine="pyarrow", index=False)

        config = MagicMock()
        config.DATA_DIR = tmp_path

        indicator_engine = MagicMock()
        indicator_engine.run.side_effect = lambda pair, tf, df: df

        regime_engine = MagicMock()
        regime_engine.run.side_effect = lambda pair, tf, df: df
        regime_engine.pair_configs = {"EUR_USD": {"min_bb_width": 0.0008}}

        counter = FilterCounter(
            config=config,
            indicator_engine=indicator_engine,
            regime_engine=regime_engine,
        )
        result = counter.run("EUR_USD")

        assert result["tradeable"] <= result["total"]
        assert result["ranging"] <= result["tradeable"]
        assert result["volatility_floor"] <= result["ranging"]
        assert result["near_band"] <= result["volatility_floor"]
        assert result["reentry"] <= result["near_band"]
        assert result["signals"] <= result["reentry"]
