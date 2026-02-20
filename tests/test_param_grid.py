"""Tests for param_grid generation and combination limits."""

import itertools
from bb_strategy.optimization.param_grid import PARAM_GRID, get_grid_for_pair, MAX_COMBINATIONS

def test_grid_under_500_combos():
    """Default grid must have < 500 combinations."""
    keys = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    combos = list(itertools.product(*values))
    assert len(combos) < MAX_COMBINATIONS
    assert len(combos) == 4 * 4 * 1 * 5 * 3 # 240

def test_get_grid_for_pair_returns_dicts():
    """get_grid_for_pair should return a list of parameter dicts."""
    grid = get_grid_for_pair("EUR_USD")
    assert isinstance(grid, list)
    assert len(grid) == 240
    assert isinstance(grid[0], dict)
    assert "bb_period" in grid[0]
    assert "ema_fast" in grid[0] # Fixed param
