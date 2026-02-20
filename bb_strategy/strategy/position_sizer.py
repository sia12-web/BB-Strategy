"""Position sizer: risk-based unit calculation for Oanda orders."""

from __future__ import annotations


class PositionSizer:
    """Calculate trade size based on fixed-percentage risk.

    Formula::

        units = (balance × risk_pct) / |entry_price − stop_loss|
    """

    def calculate(
        self,
        account_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss: float,
        pair: str = "",
    ) -> int:
        """Return the number of units to trade.

        Args:
            account_balance: Current account balance in base currency.
            risk_pct: Fraction of balance to risk (e.g. 0.01 = 1%).
            entry_price: Expected fill price.
            stop_loss: Stop-loss price.
            pair: Instrument name (reserved for future pip-value adjustment).

        Returns:
            Integer number of units (always ≥ 0).

        Raises:
            ValueError: If inputs are invalid.
        """
        if account_balance <= 0:
            raise ValueError(f"account_balance must be positive, got {account_balance}")
        if not (0 < risk_pct <= 1):
            raise ValueError(f"risk_pct must be in (0, 1], got {risk_pct}")

        distance = abs(entry_price - stop_loss)
        if distance == 0:
            raise ValueError("entry_price and stop_loss cannot be equal")

        risk_amount = account_balance * risk_pct
        units = risk_amount / distance

        return int(round(units))
