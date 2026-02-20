"""Standalone script to compare live paper trading results against backtest OOS results."""

import json
import sys
from pathlib import Path
from tabulate import tabulate

from bb_strategy.config import Config
from bb_strategy.live.performance_tracker import PerformanceTracker

def main():
    config = Config()
    paper_trades_path = config.DATA_DIR / "paper_trades.json"
    opt_results_path = config.DATA_DIR / "optimization_results.json"
    
    if not paper_trades_path.exists():
        print(f"No paper trades file found at {paper_trades_path}")
        return

    try:
        with open(paper_trades_path, "r", encoding="utf-8") as f:
            trades = json.load(f)
    except Exception as e:
        print(f"Error reading paper_trades.json: {e}")
        return

    if len(trades) < 5:
        print(f"Insufficient data — need at least 5 trades to run tracker. Current count: {len(trades)}")
        return

    # Initialize tracker and force an update of live_performance.json
    tracker = PerformanceTracker(config=config)
    tracker.update(paper_trades_path)
    
    comparison = tracker.compare_to_backtest(opt_results_path)
    if not comparison:
        print("Insufficient data or missing optimization results for comparison Table.")
        # Try to print whatever we have
        print(f"Live trades count: {len(trades)}")
        return

    # Build the display table
    table_data = [
        ["Metric", "Live (Paper)", "OOS Backtest", "Delta"],
        [
            "Trade Count", 
            comparison["trades_live"], 
            comparison["trades_oos"], 
            comparison["trades_live"] - comparison["trades_oos"]
        ],
        [
            "Win Rate", 
            f"{comparison['win_rate_live']:.2%}", 
            f"{comparison['win_rate_oos']:.2%}", 
            f"{comparison['win_rate_delta']:.2%}"
        ],
        [
            "Sharpe Ratio", 
            f"{comparison['sharpe_live']:.3f}" if comparison['sharpe_live'] else "N/A (<10 trds)", 
            f"{comparison['sharpe_oos']:.3f}" if comparison['sharpe_oos'] else "N/A",
            f"{comparison['sharpe_live'] - comparison['sharpe_oos']:.3f}" if comparison['sharpe_live'] and comparison['sharpe_oos'] else "N/A"
        ]
    ]
    
    print("\n" + "="*50)
    print(f" LIVE PERFORMANCE COMPARISON: {comparison['pair']} ".center(50, "="))
    print("="*50)
    print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
    print(f"\nLast update: {config.DATA_DIR / 'live_performance.json'}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
