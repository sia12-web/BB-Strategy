"""Indicator engine that applies all indicators to a DataFrame."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.indicators.bollinger import BollingerBands
from bb_strategy.indicators.atr import ATR
from bb_strategy.indicators.ema import EMA
from bb_strategy.indicators.pair_configs import DEFAULT_PAIR_CONFIGS

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """Apply Bollinger Bands, ATR, and EMA to OHLCV data using per-pair configs.

    Usage::

        engine = IndicatorEngine()
        enriched = engine.run("EUR_USD", "H1", df)
    """

    # All columns added by this engine
    INDICATOR_COLUMNS = [
        "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pct_b",
        "atr", "atr_ratio",
        "ema_fast", "ema_slow", "ema_cross",
    ]

    def __init__(self, pair_configs: Optional[dict[str, dict]] = None) -> None:
        self.pair_configs = pair_configs or DEFAULT_PAIR_CONFIGS

    def run(self, pair: str, timeframe: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all indicators to *df* using the config for *pair*.

        Args:
            pair: Instrument name (e.g. "EUR_USD"). Used to look up params.
            timeframe: Granularity string (for logging only).
            df: OHLCV DataFrame.

        Returns:
            DataFrame with all indicator columns added.

        Raises:
            ValueError: If *pair* has no config entry.
        """
        cfg = self.pair_configs.get(pair)
        if cfg is None:
            raise ValueError(
                f"No indicator config for pair '{pair}'. "
                f"Available: {list(self.pair_configs.keys())}"
            )

        logger.info("Computing indicators for %s %s (%d rows)", pair, timeframe, len(df))

        df = BollingerBands(period=cfg["bb_period"], std_dev=cfg["bb_std_dev"]).calculate(df)
        df = ATR(period=cfg["atr_period"]).calculate(df)
        df = EMA(fast=cfg["ema_fast"], slow=cfg["ema_slow"]).calculate(df)

        return df
