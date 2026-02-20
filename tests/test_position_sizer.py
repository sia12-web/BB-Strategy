"""Tests for PositionSizer risk calculation."""

import pytest

from bb_strategy.strategy.position_sizer import PositionSizer


def test_risk_1pct_of_balance():
    """1% of 10,000 = 100 risk. units = 100 / distance."""
    sizer = PositionSizer()
    # entry=1.1000, SL=1.0990 → distance=0.001 → units = 100 / 0.001 = 100,000
    units = sizer.calculate(
        account_balance=10_000,
        risk_pct=0.01,
        entry_price=1.1000,
        stop_loss=1.0990,
    )
    assert units == 100_000
    # Risk exposure = units * distance = 100,000 * 0.001 = 100.0
    risk_exposure = units * abs(1.1000 - 1.0990)
    assert abs(risk_exposure - 100.0) < 0.01


def test_units_always_positive():
    """Units must be positive regardless of long/short direction."""
    sizer = PositionSizer()
    # Short: SL above entry
    units = sizer.calculate(10_000, 0.01, 1.1000, 1.1020)
    assert units > 0


def test_returns_integer():
    """Units are truncated to int for Oanda."""
    sizer = PositionSizer()
    units = sizer.calculate(10_000, 0.01, 1.1000, 1.0993)
    assert isinstance(units, int)


def test_raises_on_zero_distance():
    """Entry == SL → division by zero → ValueError."""
    sizer = PositionSizer()
    with pytest.raises(ValueError, match="cannot be equal"):
        sizer.calculate(10_000, 0.01, 1.1000, 1.1000)


def test_raises_on_negative_balance():
    """Negative balance → ValueError."""
    with pytest.raises(ValueError, match="positive"):
        PositionSizer().calculate(-5000, 0.01, 1.1, 1.09)


def test_raises_on_invalid_risk():
    """Risk > 1 or ≤ 0 → ValueError."""
    with pytest.raises(ValueError, match="risk_pct"):
        PositionSizer().calculate(10_000, 1.5, 1.1, 1.09)
    with pytest.raises(ValueError, match="risk_pct"):
        PositionSizer().calculate(10_000, 0, 1.1, 1.09)
