"""Track and analyze paper trade performance against backtest expectations."""

import json
import logging
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd
from bb_strategy.config import Config

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Class to manage paper trading metrics and comparison with optimization results."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.output_path = self.config.DATA_DIR / "live_performance.json"

    def update(self, paper_trades_path: Path) -> dict[str, Any]:
        """Read paper_trades.json, compute metrics, and save to live_performance.json.
        
        Note: Requires 'exit_price' to be present in trades to calculate PnL/Sharpe.
        """
        if not paper_trades_path.exists():
            return {}

        try:
            with open(paper_trades_path, "r", encoding="utf-8") as f:
                trades = json.load(f)
        except Exception as e:
            logger.error("Failed to read paper trades: %s", e)
            return {}

        if not trades:
            return {}

        df = pd.DataFrame(trades)
        
        # Performance needs completed trades (with exit prices)
        if "exit_price" not in df.columns:
            logger.debug("No 'exit_price' column in paper trades yet.")
            return {}
            
        closed = df.dropna(subset=["exit_price"]).copy()
        if len(closed) == 0:
            return {}

        # Calculate Pips: (exit - entry) * signal * 10000
        closed["pips"] = (closed["exit_price"] - closed["entry_price"]) * closed["signal"] * 10000
        
        win_rate = (closed["pips"] > 0).mean()
        avg_pips = closed["pips"].mean()
        
        sharpe = None
        if len(closed) >= 10:
            std_pips = closed["pips"].std()
            if std_pips > 0:
                # Annualized from per-trade std (rough approximation)
                sharpe = (avg_pips / std_pips) * np.sqrt(252)
        
        stats = {
            "trades_count": len(closed),
            "win_rate": float(round(win_rate, 4)),
            "avg_pips": float(round(avg_pips, 2)),
            "sharpe": float(round(sharpe, 4)) if sharpe is not None else None,
        }

        # Save to file
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            logger.debug("Updated live performance metrics.")
        except Exception as e:
            logger.error("Failed to save live performance: %s", e)

        return stats

    def compare_to_backtest(self, optimization_results_path: Path) -> dict[str, Any]:
        """Compare current live performance against OOS backtest results."""
        if not self.output_path.exists() or not optimization_results_path.exists():
            return {}

        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                live = json.load(f)
            with open(optimization_results_path, "r", encoding="utf-8") as f:
                opt = json.load(f)
        except Exception as e:
            logger.error("Error loading files for comparison: %s", e)
            return {}

        # Default comparison for EUR_USD
        eur_oos = opt.get("EUR_USD", {})
        if not eur_oos:
            return {}

        live_wr = live.get("win_rate", 0.0)
        oos_wr = eur_oos.get("out_of_sample_win_rate", 0.0)
        
        return {
            "pair": "EUR_USD",
            "trades_live": live.get("trades_count", 0),
            "trades_oos": eur_oos.get("out_of_sample_trades", 0),
            "win_rate_live": live_wr,
            "win_rate_oos": oos_wr,
            "win_rate_delta": round(live_wr - oos_wr, 4),
            "sharpe_live": live.get("sharpe"),
            "sharpe_oos": eur_oos.get("out_of_sample_sharpe"),
        }
