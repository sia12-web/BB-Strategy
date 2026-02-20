"""Signal pipeline filter diagnostics — counts bars surviving each stage."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from bb_strategy.config import Config
from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.regime.regime_engine import RegimeEngine

logger = logging.getLogger(__name__)


class FilterCounter:
    """Count bars passing each filter stage for a single pair.

    Stages
    ------
    1. total — all bars in the dataset
    2. tradeable — bars where ``tradeable_session == True``
    3. ranging — bars where the merged H1 regime is ``"ranging"``
    4. near_band — bars where ``bb_pct_b < 0.1`` OR ``bb_pct_b > 0.9``
    5. reentry — bars where close re-enters from outside a band
    6. signals — bars with both near_band + reentry + tradeable + ranging
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        indicator_engine: Optional[IndicatorEngine] = None,
        regime_engine: Optional[RegimeEngine] = None,
    ) -> None:
        self.config = config or Config()
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.regime_engine = regime_engine or RegimeEngine()

    def run(self, pair: str, timeframe: str = "M15", years: int = 3) -> dict:
        """Load 3y data, apply full stack, count bars per filter stage.

        Args:
            pair: Instrument name.
            timeframe: Entry timeframe (default M15).
            years: Years of data to load.

        Returns:
            Dict with keys: total, tradeable, ranging, near_band, reentry, signals
        """
        data_dir = self.config.DATA_DIR

        # Load parquet files
        m15_path = data_dir / f"{pair}_{timeframe}_{years}y.parquet"
        h1_path = data_dir / f"{pair}_H1_{years}y.parquet"

        if not m15_path.exists():
            raise FileNotFoundError(f"Missing {m15_path}")
        if not h1_path.exists():
            raise FileNotFoundError(f"Missing {h1_path}")

        m15_raw = pd.read_parquet(m15_path, engine="pyarrow")
        h1_raw = pd.read_parquet(h1_path, engine="pyarrow")

        # Apply indicators
        m15 = self.indicator_engine.run(pair, timeframe, m15_raw)
        h1 = self.indicator_engine.run(pair, "H1", h1_raw)

        # Apply regime + sessions
        m15 = self.regime_engine.run(pair, timeframe, m15)
        h1 = self.regime_engine.run(pair, "H1", h1)

        # Merge H1 regime onto M15
        h1_regime = h1[["time", "regime"]].rename(columns={"regime": "h1_regime"})
        h1_regime = h1_regime.sort_values("time")
        m15 = m15.sort_values("time")
        m15 = pd.merge_asof(m15, h1_regime, on="time", direction="backward")

        # --- Stage counts ---
        total = len(m15)

        tradeable_mask = m15["tradeable_session"] == True  # noqa: E712
        tradeable = int(tradeable_mask.sum())

        ranging_mask = m15["h1_regime"] == "ranging"
        ranging = int((tradeable_mask & ranging_mask).sum())

        # New stage: volatility floor (M15 width must be above floor)
        cfg = self.regime_engine.pair_configs.get(pair, {})
        min_width = cfg.get("min_bb_width", 0.0)
        floor_mask = m15["bb_width"] > min_width
        volatility_floor = int((tradeable_mask & ranging_mask & floor_mask).sum())

        # Relaxed thresholds: 0.1 / 0.9
        near_band_mask = (m15["bb_pct_b"] < 0.1) | (m15["bb_pct_b"] > 0.9)
        near_band = int((tradeable_mask & ranging_mask & floor_mask & near_band_mask).sum())

        # Re-entry: prev close outside band, current close back inside
        prev_close = m15["close"].shift(1)
        long_reentry = (prev_close < m15["bb_lower"]) & (m15["close"] > m15["bb_lower"])
        short_reentry = (prev_close > m15["bb_upper"]) & (m15["close"] < m15["bb_upper"])
        reentry_mask = long_reentry | short_reentry
        reentry = int(
            (tradeable_mask & ranging_mask & floor_mask & near_band_mask & reentry_mask).sum()
        )

        # Final signal count (all filters combined)
        signals = reentry  # reentry already includes all upstream filters

        result = {
            "total": total,
            "tradeable": tradeable,
            "ranging": ranging,
            "volatility_floor": volatility_floor,
            "near_band": near_band,
            "reentry": reentry,
            "signals": signals,
        }

        logger.info("[%s] Filter counts: %s", pair, result)
        return result
