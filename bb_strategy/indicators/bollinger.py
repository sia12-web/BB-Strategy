"""Bollinger Bands indicator."""

from __future__ import annotations

import pandas as pd


class BollingerBands:
    """Calculate Bollinger Bands from OHLCV data.

    Adds columns: bb_upper, bb_middle, bb_lower, bb_width, bb_pct_b
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self.period = period
        self.std_dev = std_dev

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Band columns to *df* (in-place copy returned).

        Raises:
            ValueError: If required columns are missing.
        """
        self._validate(df)
        df = df.copy()

        rolling = df["close"].rolling(window=self.period)
        df["bb_middle"] = rolling.mean()
        std = rolling.std(ddof=0)

        df["bb_upper"] = df["bb_middle"] + self.std_dev * std
        df["bb_lower"] = df["bb_middle"] - self.std_dev * std

        # Normalized width
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        # %B — 0-1 when price inside bands, outside that range when price breaks out
        band_range = df["bb_upper"] - df["bb_lower"]
        df["bb_pct_b"] = (df["close"] - df["bb_lower"]) / band_range

        return df

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
