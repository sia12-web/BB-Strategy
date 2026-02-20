"""Candle fetcher: pulls latest candles and enriches with indicators + regime."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.config import Config
from bb_strategy.data.oanda_client import OandaClient
from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.regime.regime_engine import RegimeEngine

logger = logging.getLogger(__name__)


class CandleFetcher:
    """Fetch live candles from Oanda and enrich with indicators + regime.

    This is a scheduled fetcher, not a streaming connection.
    """

    def __init__(
        self,
        oanda_client: Optional[OandaClient] = None,
        indicator_engine: Optional[IndicatorEngine] = None,
        regime_engine: Optional[RegimeEngine] = None,
    ) -> None:
        self.client = oanda_client or OandaClient()
        
        # Load optimized parameters where available
        ind_cfgs, reg_cfgs = self._load_optimized_configs()
        
        self.indicator_engine = indicator_engine or IndicatorEngine(pair_configs=ind_cfgs)
        self.regime_engine = regime_engine or RegimeEngine(pair_configs=reg_cfgs)

    def _load_optimized_configs(self) -> tuple[dict, dict]:
        """Load optimization_results.json and merge into defaults for validated pairs."""
        from bb_strategy.optimization.run_optimization import update_configs_from_optimization
        from bb_strategy.indicators.pair_configs import DEFAULT_PAIR_CONFIGS
        from bb_strategy.regime.regime_configs import DEFAULT_REGIME_CONFIGS
        
        results_path = Config().DATA_DIR / "optimization_results.json"
        if not results_path.exists():
            logger.warning("No optimization results found at %s. Using defaults.", results_path)
            return DEFAULT_PAIR_CONFIGS, DEFAULT_REGIME_CONFIGS
            
        try:
            return update_configs_from_optimization(results_path)
        except Exception as e:
            logger.error("Error loading optimized configs: %s. Using defaults.", e)
            return DEFAULT_PAIR_CONFIGS, DEFAULT_REGIME_CONFIGS

    def fetch_latest(
        self,
        pair: str,
        timeframe: str,
        count: int = 100,
    ) -> pd.DataFrame:
        """Fetch the latest candles and apply indicators + regime.

        Args:
            pair: Instrument name, e.g. "EUR_USD".
            timeframe: Granularity, e.g. "M15" or "H1".
            count: Number of candles to fetch (default 100).

        Returns:
            DataFrame with OHLCV + indicator + regime columns.
        """
        logger.debug("Fetching %d %s candles for %s", count, timeframe, pair)

        df = self.client.get_candles(pair=pair, timeframe=timeframe, count=count)

        if df.empty:
            logger.warning("No candles returned for %s %s", pair, timeframe)
            return df

        # Enrich with indicators
        df = self.indicator_engine.run(pair, timeframe, df)

        # Enrich with regime classification
        df = self.regime_engine.run(pair, timeframe, df)

        logger.debug(
            "Fetched %d enriched rows for %s %s (last: %s)",
            len(df), pair, timeframe,
            df["time"].iloc[-1] if "time" in df.columns else "N/A",
        )

        return df
