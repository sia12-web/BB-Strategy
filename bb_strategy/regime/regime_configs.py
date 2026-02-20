"""Default regime detection thresholds per currency pair."""

from __future__ import annotations

# Keys: bb_width_threshold, atr_ratio_threshold

DEFAULT_REGIME_CONFIGS: dict[str, dict] = {
    "EUR_USD": {
        "bb_width_threshold": 0.002,
        "atr_ratio_threshold": 0.9,
        "min_bb_width": 0.0008,
    },
    "GBP_USD": {
        "bb_width_threshold": 0.0025,
        "atr_ratio_threshold": 0.95,
        "min_bb_width": 0.0010,
    },
    "USD_JPY": {
        "bb_width_threshold": 0.002,
        "atr_ratio_threshold": 0.9,
        "min_bb_width": 0.0006,
    },
    "GBP_JPY": {
        "bb_width_threshold": 0.003,
        "atr_ratio_threshold": 1.0,
        "min_bb_width": 0.0012,
    },
}
