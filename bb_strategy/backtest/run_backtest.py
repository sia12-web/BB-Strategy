"""Run a full backtest across all pairs using stored data."""

from __future__ import annotations

import logging
from typing import Optional

from bb_strategy.config import Config
from bb_strategy.data.data_store import DataStore
from bb_strategy.strategy.strategy_engine import StrategyEngine
from bb_strategy.backtest.backtest_engine import BacktestEngine
from bb_strategy.backtest.backtest_result import BacktestResult

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = ["", "_3y"]


def run_backtest(
    pair: str,
    initial_balance: float = 10_000.0,
    risk_pct: float = 0.01,
    data_suffix: str = "_3y",
    config: Optional[Config] = None,
) -> BacktestResult:
    """Load data, run strategy, and backtest a single pair.

    Args:
        pair: Instrument to test.
        initial_balance: Starting account balance.
        risk_pct: Risk per trade.
        data_suffix: Suffix for data files (e.g. "_3y").
        config: Optional Config override.

    Returns:
        BacktestResult object.
    """
    if data_suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"data_suffix must be one of {ALLOWED_SUFFIXES}, got {data_suffix}")

    cfg = config or Config()
    store = DataStore(cfg.DATA_DIR)
    strategy = StrategyEngine()

    # Load both timeframes
    h1_df = store.load(pair, "H1", suffix=data_suffix)
    m15_df = store.load(pair, "M15", suffix=data_suffix)

    # Run full strategy stack
    signals_df = strategy.run(pair, h1_df, m15_df)

    # Backtest
    bt = BacktestEngine(initial_balance=initial_balance, risk_pct=risk_pct)
    result = bt.run(pair, signals_df)

    return result
def run_full_backtest(
    pairs: Optional[list[str]] = None,
    initial_balance: float = 10_000.0,
    risk_pct: float = 0.01,
    data_suffix: str = "_3y",
    config: Optional[Config] = None,
) -> dict[str, BacktestResult]:
    """Load data, run strategy, and backtest for every pair.

    Args:
        pairs: List of pairs to test. Defaults to config.PAIRS.
        initial_balance: Starting account balance.
        risk_pct: Risk per trade as fraction.
        data_suffix: Suffix for data files.
        config: Optional Config override.

    Returns:
        Dict mapping pair name → BacktestResult.
    """
    cfg = config or Config()
    pairs = pairs or cfg.PAIRS
    results: dict[str, BacktestResult] = {}

    for pair in pairs:
        logger.info("Backtesting %s ...", pair)

        result = run_backtest(
            pair=pair,
            initial_balance=initial_balance,
            risk_pct=risk_pct,
            data_suffix=data_suffix,
            config=cfg,
        )
        results[pair] = result

        summary = result.summary()
        logger.info(
            "%s: %d trades | win_rate=%.1f%% | return=%.2f%% | max_dd=%.2f%%",
            pair,
            summary["total_trades"],
            summary["win_rate"] * 100,
            summary["total_return_pct"],
            summary["max_drawdown_pct"],
        )

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_full_backtest()
