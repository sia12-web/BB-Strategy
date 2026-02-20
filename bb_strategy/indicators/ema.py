"""Exponential Moving Average crossover indicator."""

from __future__ import annotations

import numpy as np
import pandas as pd


class EMA:
    """Calculate fast/slow EMA and crossover signal from OHLCV data.

    Adds columns: ema_fast, ema_slow, ema_cross
    """

    def __init__(self, fast: int = 8, slow: int = 21) -> None:
        self.fast = fast
        self.slow = slow

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add EMA columns to *df* (in-place copy returned).

        Raises:
            ValueError: If required columns are missing.
        """
        self._validate(df)
        df = df.copy()

        df["ema_fast"] = df["close"].ewm(span=self.fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.slow, adjust=False).mean()

        # +1 when fast above slow, -1 when below
        df["ema_cross"] = np.where(df["ema_fast"] >= df["ema_slow"], 1, -1)

        return df

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
