"""Regime classifier: labels candles as ranging, trending, or neutral."""

from __future__ import annotations

import pandas as pd


_REQUIRED_COLUMNS = {"bb_width", "atr_ratio", "ema_cross"}


class RegimeClassifier:
    """Classify market regime from indicator columns.

    Regime rules
    -------------
    **Ranging**: bb_width < threshold AND atr_ratio < threshold AND
                 ema_cross unchanged for last 3 bars.
    **Trending**: ema_cross changed in last 2 bars OR
                  atr_ratio > atr_ratio_threshold × 1.5.
    **Neutral**: everything else.
    """

    VALID_REGIMES = {"ranging", "trending", "neutral"}

    def __init__(
        self,
        bb_width_threshold: float = 0.002,
        atr_ratio_threshold: float = 0.9,
        min_bb_width: float = 0.0008,
    ) -> None:
        if min_bb_width >= bb_width_threshold:
            raise ValueError(
                f"min_bb_width ({min_bb_width}) must be less than "
                f"bb_width_threshold ({bb_width_threshold})"
            )
        self.bb_width_threshold = bb_width_threshold
        self.atr_ratio_threshold = atr_ratio_threshold
        self.min_bb_width = min_bb_width

    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add a ``regime`` column to *df*.

        Raises:
            ValueError: If required indicator columns are missing.
        """
        self._validate(df)
        df = df.copy()

        # Helpers
        # Volatility ceiling (high width = trending or erratic)
        ceiling_bb = df["bb_width"] < self.bb_width_threshold
        # Volatility floor (very low width = dead market noise)
        floor_bb = df["bb_width"] > self.min_bb_width
        
        low_atr = df["atr_ratio"] < self.atr_ratio_threshold

        # ema_cross unchanged for last 3 bars → rolling std == 0
        ema_stable_3 = df["ema_cross"].rolling(3, min_periods=3).std() == 0

        # ema_cross changed in last 2 bars → rolling std > 0
        ema_changed_2 = df["ema_cross"].rolling(2, min_periods=2).std() > 0

        high_atr = df["atr_ratio"] > (self.atr_ratio_threshold * 1.5)

        # Default: neutral
        regime = pd.Series("neutral", index=df.index)

        # Trending takes priority over neutral
        regime[ema_changed_2 | high_atr] = "trending"

        # Ranging overrides when all four conditions are met
        regime[ceiling_bb & floor_bb & low_atr & ema_stable_3] = "ranging"

        df["regime"] = regime
        return df

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required indicator columns: {missing}")
