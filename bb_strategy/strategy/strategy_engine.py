"""Strategy engine: orchestrates indicators, regime, and signals for a pair."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.regime.regime_engine import RegimeEngine
from bb_strategy.strategy.signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Full pipeline: indicators → regime → signals for a single pair.

    Usage::

        engine = StrategyEngine()
        result = engine.run("EUR_USD", h1_raw, m15_raw)
    """

    SIGNAL_COLUMNS = [
        "signal", "signal_type", "entry_price",
        "stop_loss", "take_profit", "exit_signal",
    ]

    def __init__(
        self,
        indicator_engine: Optional[IndicatorEngine] = None,
        regime_engine: Optional[RegimeEngine] = None,
        atr_sl_multiplier: float = 1.5,
    ) -> None:
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.regime_engine = regime_engine or RegimeEngine()
        self.atr_sl_multiplier = atr_sl_multiplier

    def run(
        self, pair: str, h1_df: pd.DataFrame, m15_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Run the full strategy stack for *pair*.

        Args:
            pair: Instrument name.
            h1_df: Raw OHLCV for H1 timeframe.
            m15_df: Raw OHLCV for M15 timeframe.

        Returns:
            Enriched M15 DataFrame with indicator, regime, and signal columns.
        """
        logger.info("Running strategy for %s", pair)

        # 1. Compute indicators
        h1 = self.indicator_engine.run(pair, "H1", h1_df)
        m15 = self.indicator_engine.run(pair, "M15", m15_df)

        # 2. Classify regime + sessions
        h1 = self.regime_engine.run(pair, "H1", h1)
        m15 = self.regime_engine.run(pair, "M15", m15)

        # 3. Generate signals
        sig_gen = SignalGenerator(atr_sl_multiplier=self.atr_sl_multiplier)
        result = sig_gen.generate(h1, m15)

        n_long = (result["signal"] == 1).sum()
        n_short = (result["signal"] == -1).sum()
        logger.info(
            "%s signals: %d long, %d short, %d total rows",
            pair, n_long, n_short, len(result),
        )

        return result
