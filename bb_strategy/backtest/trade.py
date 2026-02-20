"""Trade dataclass representing a single completed or open trade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Trade:
    """Record of a single trade lifecycle."""

    pair: str
    direction: int                       # 1 = long, -1 = short
    entry_time: pd.Timestamp
    entry_price: float
    stop_loss: float
    take_profit: float
    units: int

    # Filled on close
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None    # "stop_loss", "take_profit", "exit_signal"
    pnl_pips: float = 0.0
    pnl_usd: float = 0.0
    status: str = "open"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def close(
        self,
        exit_time: pd.Timestamp,
        exit_price: float,
        exit_reason: str,
    ) -> None:
        """Close the trade and compute P&L."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.status = "closed"

        price_diff = (exit_price - self.entry_price) * self.direction
        pip_divisor = _pip_divisor(self.pair)

        self.pnl_pips = price_diff / pip_divisor
        self.pnl_usd = self._calc_pnl_usd(price_diff)

    def _calc_pnl_usd(self, price_diff: float) -> float:
        """Convert price difference to USD P&L.

        - USD-quoted pairs (EUR_USD, GBP_USD): pnl = price_diff * units
          (each unit move of 0.0001 = $0.0001 per unit → standard lot = $10/pip)
        - JPY pairs (USD_JPY, GBP_JPY): pnl = (price_diff / exit_price) * units
          (convert from quote currency to USD at exit price)
        """
        if _is_jpy_pair(self.pair):
            # price_diff already in JPY terms; convert to USD
            return (price_diff / self.exit_price) * self.units
        else:
            # USD is the quote currency
            return price_diff * self.units

    @property
    def is_winner(self) -> bool:
        return self.pnl_usd > 0


def _pip_divisor(pair: str) -> float:
    """Return pip size: 0.01 for JPY pairs, 0.0001 for all others."""
    return 0.01 if _is_jpy_pair(pair) else 0.0001


def _is_jpy_pair(pair: str) -> bool:
    return "JPY" in pair
