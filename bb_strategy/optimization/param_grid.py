"""Parameter grid definitions for grid search optimization."""

from __future__ import annotations

import itertools
from typing import Any

# Default search space — 3×3×1×3×3×3 = 243 combinations
PARAM_GRID: dict[str, list] = {
    "bb_period": [15, 20, 25],
    "bb_std_dev": [1.8, 2.0, 2.2],
    "atr_period": [14],
    "bb_width_threshold": [0.0015, 0.002, 0.0025],
    "min_bb_width": [0.0005, 0.0008, 0.0012],
    "atr_ratio_threshold": [0.8, 0.9, 1.0],
}

# Overrides for JPY pairs and high-volatility pairs
PAIR_GRID_OVERRIDES: dict[str, dict[str, list]] = {
    "GBP_JPY": {
        "bb_std_dev": [2.0, 2.5, 3.0],
    },
    "USD_JPY": {
        "min_bb_width": [0.0004, 0.0006, 0.0009],
    },
}
# Need to add JPY floor to GBP_JPY as well
PAIR_GRID_OVERRIDES["GBP_JPY"]["min_bb_width"] = [0.0004, 0.0006, 0.0009]

# Fixed params not included in grid search
FIXED_PARAMS: dict[str, Any] = {
    "ema_fast": 8,
    "ema_slow": 21,
}

MAX_COMBINATIONS = 500


def get_grid_for_pair(pair: str) -> list[dict[str, Any]]:
    """Return all parameter combinations for a pair.

    Raises:
        ValueError: If combinations exceed MAX_COMBINATIONS.
    """
    grid = PARAM_GRID.copy()

    # Apply pair-specific overrides
    if pair in PAIR_GRID_OVERRIDES:
        for key, values in PAIR_GRID_OVERRIDES[pair].items():
            grid[key] = values

    keys = list(grid.keys())
    values = list(grid.values())
    combos = []

    for vals in itertools.product(*values):
        params = dict(zip(keys, vals))
        params.update(FIXED_PARAMS)
        combos.append(params)

    if len(combos) > MAX_COMBINATIONS:
        raise ValueError(
            f"Grid for {pair} has {len(combos)} combinations, "
            f"exceeding cap of {MAX_COMBINATIONS}"
        )

    return combos
