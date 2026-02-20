"""Regime engine: applies session tagging + regime classification."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.regime.session_filter import SessionFilter
from bb_strategy.regime.regime_classifier import RegimeClassifier
from bb_strategy.regime.regime_configs import DEFAULT_REGIME_CONFIGS

logger = logging.getLogger(__name__)


class RegimeEngine:
    """Orchestrate session tagging and regime classification.

    Usage::

        engine = RegimeEngine()
        enriched = engine.run("EUR_USD", "H1", df_with_indicators)
    """

    REGIME_COLUMNS = ["session", "tradeable_session", "regime"]

    def __init__(self, pair_configs: Optional[dict[str, dict]] = None) -> None:
        self.pair_configs = pair_configs or DEFAULT_REGIME_CONFIGS
        self.session_filter = SessionFilter()

    def run(self, pair: str, timeframe: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply session filter then regime classifier.

        Args:
            pair: Instrument name for config lookup.
            timeframe: Granularity (for logging).
            df: DataFrame with indicator columns already computed.

        Returns:
            DataFrame with ``session``, ``tradeable_session``, and ``regime`` columns.

        Raises:
            ValueError: If *pair* has no config or required columns are missing.
        """
        cfg = self.pair_configs.get(pair)
        if cfg is None:
            raise ValueError(
                f"No regime config for pair '{pair}'. "
                f"Available: {list(self.pair_configs.keys())}"
            )

        logger.info("Classifying regime for %s %s (%d rows)", pair, timeframe, len(df))

        df = self.session_filter.tag_sessions(df)

        classifier = RegimeClassifier(
            bb_width_threshold=cfg["bb_width_threshold"],
            atr_ratio_threshold=cfg["atr_ratio_threshold"],
            min_bb_width=cfg.get("min_bb_width", 0.0),
        )
        df = classifier.classify(df)

        return df
