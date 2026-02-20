"""Tests for PerformanceTracker metrics and comparison logic."""

import json
import pytest
import pandas as pd
from bb_strategy.live.performance_tracker import PerformanceTracker

@pytest.fixture
def tracker(tmp_path):
    from bb_strategy.config import Config
    cfg = Config()
    cfg.DATA_DIR = tmp_path
    return PerformanceTracker(config=cfg)

def test_update_calculates_win_rate(tracker, tmp_path):
    """Verify win_rate calculation with synthetic closed trades."""
    trades = [
        {"signal": 1,  "entry_price": 1.1000, "exit_price": 1.1020}, # Win (20 pips)
        {"signal": 1,  "entry_price": 1.1000, "exit_price": 1.1010}, # Win (10 pips)
        {"signal": -1, "entry_price": 1.0500, "exit_price": 1.0490}, # Win (10 pips)
        {"signal": -1, "entry_price": 1.0500, "exit_price": 1.0480}, # Win (20 pips)
        {"signal": 1,  "entry_price": 1.1000, "exit_price": 1.0990}, # Loss (-10 pips)
        {"signal": -1, "entry_price": 1.0500, "exit_price": 1.0510}, # Loss (-10 pips)
    ]
    # 4 wins, 2 losses -> win_rate = 4/6 = 0.6667
    
    path = tmp_path / "paper_trades.json"
    with open(path, "w") as f:
        json.dump(trades, f)
        
    stats = tracker.update(path)
    assert stats["win_rate"] == 0.6667
    assert stats["trades_count"] == 6
    assert stats["avg_pips"] == 6.67 # (20+10+10+20-10-10)/6 = 40/6 = 6.666...

def test_sharpe_requires_10_trades(tracker, tmp_path):
    """Sharpe should be None if fewer than 10 trades exist."""
    trades = [{"signal": 1, "entry_price": 1.0, "exit_price": 1.1}] * 9
    path = tmp_path / "paper_trades.json"
    with open(path, "w") as f:
        json.dump(trades, f)
        
    stats = tracker.update(path)
    assert stats["sharpe"] is None

def test_compare_returns_delta_keys(tracker, tmp_path):
    """Verify comparison dictionary keys and delta calculation."""
    # 1. Create live performance
    live_stats = {"trades_count": 5, "win_rate": 0.60, "avg_pips": 5.0, "sharpe": None}
    with open(tracker.output_path, "w") as f:
        json.dump(live_stats, f)
        
    # 2. Create optimization results
    opt_results = {
        "EUR_USD": {
            "out_of_sample_trades": 16,
            "out_of_sample_win_rate": 0.8125,
            "out_of_sample_sharpe": 0.231
        }
    }
    opt_path = tmp_path / "optimization_results.json"
    with open(opt_path, "w") as f:
        json.dump(opt_results, f)
        
    comparison = tracker.compare_to_backtest(opt_path)
    
    assert "win_rate_delta" in comparison
    assert "trades_live" in comparison
    assert "trades_oos" in comparison
    assert comparison["trades_live"] == 5
    assert comparison["trades_oos"] == 16
    assert comparison["win_rate_delta"] == round(0.60 - 0.8125, 4)
