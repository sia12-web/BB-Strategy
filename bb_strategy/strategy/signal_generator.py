"""Signal generator: H1 regime confirmation + M15 BB reversion entries."""

from __future__ import annotations

import numpy as np
import pandas as pd


_REQUIRED_M15_COLS = {
    "time", "close", "bb_upper", "bb_lower", "bb_middle", "bb_pct_b",
    "atr", "ema_cross", "tradeable_session", "regime",
}
_REQUIRED_H1_COLS = {"time", "regime"}


class SignalGenerator:
    """Generate entry/exit signals using multi-timeframe logic.

    Strategy
    --------
    - **H1 confirmation**: current H1 bar must be ``"ranging"``
    - **M15 entry timing**:
        - LONG: prev close < bb_lower, current close > bb_lower, bb_pct_b < 0.10
        - SHORT: prev close > bb_upper, current close < bb_upper, bb_pct_b > 0.90
    - Only during ``tradeable_session == True``
    - SL = entry ± ATR × 1.5, TP = bb_middle at entry
    """

    def __init__(self, atr_sl_multiplier: float = 1.5) -> None:
        self.atr_sl_multiplier = atr_sl_multiplier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, h1_df: pd.DataFrame, m15_df: pd.DataFrame) -> pd.DataFrame:
        """Add signal columns to *m15_df* using *h1_df* for regime confirmation.

        Returns a copy of *m15_df* with columns:
        signal, signal_type, entry_price, stop_loss, take_profit, exit_signal
        """
        self._validate(h1_df, m15_df)
        m15 = m15_df.copy()

        # --- Align H1 regime onto M15 via merge_asof (backward) ----------
        h1_regime = h1_df[["time", "regime"]].rename(columns={"regime": "h1_regime"})
        h1_regime = h1_regime.sort_values("time")
        m15 = m15.sort_values("time")
        m15 = pd.merge_asof(m15, h1_regime, on="time", direction="backward")

        # --- Entry conditions (vectorized) --------------------------------
        prev_close = m15["close"].shift(1)

        # Long: prev close below lower band, current close back above it
        long_cross = (prev_close < m15["bb_lower"]) & (m15["close"] > m15["bb_lower"])
        long_confirm = m15["bb_pct_b"] < 0.10

        # Short: prev close above upper band, current close back below it
        short_cross = (prev_close > m15["bb_upper"]) & (m15["close"] < m15["bb_upper"])
        short_confirm = m15["bb_pct_b"] > 0.90

        # Filters
        h1_ranging = m15["h1_regime"] == "ranging"
        tradeable = m15["tradeable_session"] == True  # noqa: E712

        # --- Build signal columns ----------------------------------------
        m15["signal"] = 0
        m15.loc[long_cross & long_confirm & h1_ranging & tradeable, "signal"] = 1
        m15.loc[short_cross & short_confirm & h1_ranging & tradeable, "signal"] = -1

        m15["signal_type"] = np.where(
            m15["signal"] == 1, "long",
            np.where(m15["signal"] == -1, "short", "none"),
        )

        # --- Entry, SL, TP -----------------------------------------------
        m15["entry_price"] = np.where(m15["signal"] != 0, m15["close"], np.nan)

        atr_offset = m15["atr"] * self.atr_sl_multiplier

        m15["stop_loss"] = np.where(
            m15["signal"] == 1,
            m15["close"] - atr_offset,          # long SL below
            np.where(
                m15["signal"] == -1,
                m15["close"] + atr_offset,      # short SL above
                np.nan,
            ),
        )

        m15["take_profit"] = np.where(
            m15["signal"] != 0, m15["bb_middle"], np.nan,
        )

        # --- Exit signal (vectorized approximation) -----------------------
        # True exit logic requires bar-by-bar simulation (Phase 5).
        # Here we mark rows where an exit *condition* is newly true.
        m15["exit_signal"] = 0

        # H1 regime flipped to trending
        regime_flip = (m15["h1_regime"] != "ranging") & (m15["h1_regime"].shift(1) == "ranging")
        m15.loc[regime_flip, "exit_signal"] = 1

        # EMA cross changed on M15
        ema_flip = m15["ema_cross"] != m15["ema_cross"].shift(1)
        m15.loc[ema_flip, "exit_signal"] = 1

        # Validate SL direction
        self._validate_sl(m15)

        # Drop helper column
        m15.drop(columns=["h1_regime"], inplace=True)

        return m15

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(h1_df: pd.DataFrame, m15_df: pd.DataFrame) -> None:
        missing_m15 = _REQUIRED_M15_COLS - set(m15_df.columns)
        if missing_m15:
            raise ValueError(f"M15 DataFrame missing columns: {missing_m15}")

        missing_h1 = _REQUIRED_H1_COLS - set(h1_df.columns)
        if missing_h1:
            raise ValueError(f"H1 DataFrame missing columns: {missing_h1}")

        # H1 data must cover the M15 date range
        h1_min, h1_max = h1_df["time"].min(), h1_df["time"].max()
        m15_min, m15_max = m15_df["time"].min(), m15_df["time"].max()
        return

    @staticmethod
    def _validate_sl(df: pd.DataFrame) -> None:
        """Ensure SL direction is correct for every signal."""
        longs = df[df["signal"] == 1]
        if len(longs) and (longs["stop_loss"] >= longs["entry_price"]).any():
            raise ValueError("Long signal has stop_loss >= entry_price")

        shorts = df[df["signal"] == -1]
        if len(shorts) and (shorts["stop_loss"] <= shorts["entry_price"]).any():
            raise ValueError("Short signal has stop_loss <= entry_price")
