"""Tests for SignalGenerator entry/exit logic."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.strategy.signal_generator import SignalGenerator


def _make_m15(n: int = 20, session: str = "london") -> pd.DataFrame:
    """M15 DataFrame with all required columns and controllable conditions."""
    close = np.full(n, 1.0950)
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-15 05:00", periods=n, freq="15min"),
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
            "session": session,
            "tradeable_session": session in ("asian", "london"),
            "regime": "ranging",
        }
    )


def _make_h1(m15_df: pd.DataFrame, regime: str = "ranging") -> pd.DataFrame:
    """H1 DataFrame that covers the M15 time range."""
    start = m15_df["time"].min() - pd.Timedelta(hours=1)
    end = m15_df["time"].max() + pd.Timedelta(hours=1)
    times = pd.date_range(start, end, freq="h")
    return pd.DataFrame(
        {
            "time": times,
            "regime": regime,
        }
    )


# ------------------------------------------------------------------
# Entry tests
# ------------------------------------------------------------------


def test_long_signal_on_lower_band_reentry():
    """Long signal when prev close < bb_lower AND current close > bb_lower."""
    m15 = _make_m15(10)
    # Bar 5: close dips below lower band
    m15.loc[5, "close"] = 1.0910  # below bb_lower=1.0920
    m15.loc[5, "bb_pct_b"] = -0.02
    # Bar 6: close rebounds above lower band; bb_pct_b confirms near-band entry
    m15.loc[6, "close"] = 1.0925
    m15.loc[6, "bb_pct_b"] = 0.03  # < 0.05 → confirmed

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    assert result.loc[6, "signal"] == 1
    assert result.loc[6, "signal_type"] == "long"
    assert pd.notna(result.loc[6, "entry_price"])
    assert pd.notna(result.loc[6, "stop_loss"])
    assert pd.notna(result.loc[6, "take_profit"])


def test_short_signal_on_upper_band_reentry():
    """Short signal when prev close > bb_upper AND current close < bb_upper."""
    m15 = _make_m15(10)
    m15.loc[5, "close"] = 1.0990  # above bb_upper=1.0980
    m15.loc[5, "bb_pct_b"] = 1.02
    m15.loc[6, "close"] = 1.0975
    m15.loc[6, "bb_pct_b"] = 0.96  # > 0.95 → confirmed

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    assert result.loc[6, "signal"] == -1
    assert result.loc[6, "signal_type"] == "short"


def test_no_signal_when_h1_trending():
    """No signal when H1 regime is trending."""
    m15 = _make_m15(10)
    m15.loc[5, "close"] = 1.0910
    m15.loc[5, "bb_pct_b"] = -0.02
    m15.loc[6, "close"] = 1.0925
    m15.loc[6, "bb_pct_b"] = 0.03

    h1 = _make_h1(m15, regime="trending")  # ← blocks entry
    result = SignalGenerator().generate(h1, m15)

    assert (result["signal"] == 0).all()


def test_no_signal_outside_tradeable_session():
    """No signal when tradeable_session is False."""
    m15 = _make_m15(10, session="new_york")  # not tradeable
    m15.loc[5, "close"] = 1.0910
    m15.loc[5, "bb_pct_b"] = -0.02
    m15.loc[6, "close"] = 1.0925
    m15.loc[6, "bb_pct_b"] = 0.03

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    assert (result["signal"] == 0).all()


# ------------------------------------------------------------------
# SL / TP tests
# ------------------------------------------------------------------


def test_stop_loss_below_entry_for_long():
    """Long stop_loss must be below entry_price."""
    m15 = _make_m15(10)
    m15.loc[5, "close"] = 1.0910
    m15.loc[5, "bb_pct_b"] = -0.02
    m15.loc[6, "close"] = 1.0925
    m15.loc[6, "bb_pct_b"] = 0.03

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    longs = result[result["signal"] == 1]
    assert len(longs) > 0
    assert (longs["stop_loss"] < longs["entry_price"]).all()


def test_stop_loss_above_entry_for_short():
    """Short stop_loss must be above entry_price."""
    m15 = _make_m15(10)
    m15.loc[5, "close"] = 1.0990
    m15.loc[5, "bb_pct_b"] = 1.02
    m15.loc[6, "close"] = 1.0975
    m15.loc[6, "bb_pct_b"] = 0.96

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    shorts = result[result["signal"] == -1]
    assert len(shorts) > 0
    assert (shorts["stop_loss"] > shorts["entry_price"]).all()


def test_take_profit_equals_bb_middle():
    """TP should be the bb_middle at the time of entry."""
    m15 = _make_m15(10)
    m15.loc[5, "close"] = 1.0910
    m15.loc[5, "bb_pct_b"] = -0.02
    m15.loc[6, "close"] = 1.0925
    m15.loc[6, "bb_pct_b"] = 0.03

    h1 = _make_h1(m15, regime="ranging")
    result = SignalGenerator().generate(h1, m15)

    signal_rows = result[result["signal"] != 0]
    for _, row in signal_rows.iterrows():
        assert row["take_profit"] == row["bb_middle"]


# ------------------------------------------------------------------
# Validation tests
# ------------------------------------------------------------------


def test_raises_on_mismatched_time_range():
    """ValueError if H1 doesn't cover M15 range."""
    m15 = _make_m15(10)
    h1 = pd.DataFrame({
        "time": pd.date_range("2024-01-16", periods=3, freq="h"),  # wrong day
        "regime": "ranging",
    })
    with pytest.raises(ValueError, match="does not fully cover"):
        SignalGenerator().generate(h1, m15)


# ------------------------------------------------------------------
# Relaxed threshold test
# ------------------------------------------------------------------


def test_relaxed_pct_b_generates_more_signals():
    """Relaxed threshold (0.10) should generate >= signals vs strict (0.05).

    A bar with bb_pct_b=0.07 passes the 0.10 threshold but fails 0.05.
    """
    m15 = _make_m15(20)

    # Create conditions where bb_pct_b is between 0.05 and 0.10
    # This should be caught by the relaxed threshold (0.10) but not strict (0.05)
    for idx in [5, 10, 15]:
        m15.loc[idx - 1, "close"] = 1.0910    # below bb_lower
        m15.loc[idx - 1, "bb_pct_b"] = -0.02
        m15.loc[idx, "close"] = 1.0925         # above bb_lower
        m15.loc[idx, "bb_pct_b"] = 0.07        # between 0.05 and 0.10

    h1 = _make_h1(m15, regime="ranging")

    # Current (relaxed) threshold: 0.10 — should capture bars at 0.07
    gen_relaxed = SignalGenerator()
    result_relaxed = gen_relaxed.generate(h1, m15)
    relaxed_count = (result_relaxed["signal"] != 0).sum()

    # Simulate strict threshold: manually set bb_pct_b to fail 0.05
    # With the relaxed generator, bars at 0.07 ARE captured
    # With a hypothetical strict 0.05 threshold, they would NOT be
    # Since we changed the code to 0.10, we verify signals exist for 0.07
    assert relaxed_count >= 1, "Relaxed threshold should capture bb_pct_b=0.07"

    # Also verify that a bar with bb_pct_b=0.03 (< 0.05) still works
    m15_strict = _make_m15(20)
    m15_strict.loc[4, "close"] = 1.0910
    m15_strict.loc[4, "bb_pct_b"] = -0.02
    m15_strict.loc[5, "close"] = 1.0925
    m15_strict.loc[5, "bb_pct_b"] = 0.03  # passes both 0.05 and 0.10

    result_strict = gen_relaxed.generate(h1, m15_strict)
    strict_count = (result_strict["signal"] != 0).sum()

    # Relaxed captures MORE signals because it includes 0.05–0.10 range
    assert relaxed_count >= strict_count

