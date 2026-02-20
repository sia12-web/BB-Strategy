"""Default indicator parameters per currency pair."""

from __future__ import annotations

# Each pair maps to a dict consumed by IndicatorEngine.
# Keys: bb_period, bb_std_dev, atr_period, ema_fast, ema_slow

DEFAULT_PAIR_CONFIGS: dict[str, dict] = {
    "EUR_USD": {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "atr_period": 14,
        "ema_fast": 8,
        "ema_slow": 21,
    },
    "GBP_USD": {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "atr_period": 14,
        "ema_fast": 8,
        "ema_slow": 21,
    },
    "USD_JPY": {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "atr_period": 14,
        "ema_fast": 8,
        "ema_slow": 21,
    },
    "GBP_JPY": {
        "bb_period": 20,
        "bb_std_dev": 2.5,  # wider bands — higher volatility pair
        "atr_period": 14,
        "ema_fast": 8,
        "ema_slow": 21,
    },
}
