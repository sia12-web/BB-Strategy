"""Average True Range indicator."""

from __future__ import annotations

import pandas as pd
import numpy as np


class ATR:
    """Calculate ATR and ATR ratio from OHLCV data.

    Adds columns: atr, atr_ratio
    """

    def __init__(self, period: int = 14) -> None:
        self.period = period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR columns to *df* (in-place copy returned).

        Raises:
            ValueError: If required columns are missing.
        """
        self._validate(df)
        df = df.copy()

        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)

        tr = pd.concat(
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        df["atr"] = tr.rolling(window=self.period).mean()

        # ATR ratio: current ATR vs its own 20-period moving average
        df["atr_ratio"] = df["atr"] / df["atr"].rolling(window=20).mean()

        return df

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
