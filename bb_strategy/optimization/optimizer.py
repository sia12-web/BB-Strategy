"""Grid search optimizer with in-sample/out-of-sample validation."""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from bb_strategy.indicators.indicator_engine import IndicatorEngine
from bb_strategy.indicators.pair_configs import DEFAULT_PAIR_CONFIGS
from bb_strategy.indicators.bollinger import BollingerBands
from bb_strategy.indicators.atr import ATR
from bb_strategy.indicators.ema import EMA
from bb_strategy.regime.regime_engine import RegimeEngine
from bb_strategy.regime.regime_configs import DEFAULT_REGIME_CONFIGS
from bb_strategy.regime.session_filter import SessionFilter
from bb_strategy.regime.regime_classifier import RegimeClassifier
from bb_strategy.strategy.signal_generator import SignalGenerator
from bb_strategy.backtest.backtest_engine import BacktestEngine
from bb_strategy.optimization.param_grid import get_grid_for_pair, FIXED_PARAMS
from bb_strategy.optimization.optimization_result import OptimizationResult

logger = logging.getLogger(__name__)

# Validation thresholds
MIN_OOS_SHARPE = 0.3
MIN_OOS_WIN_RATE = 0.4
MIN_IS_TRADES = 20


class Optimizer:
    """Grid search optimizer for a single pair.

    Splits data chronologically (70/30 by default), runs every parameter
    combination on in-sample, picks best by Sharpe, then validates on
    out-of-sample.
    """

    def __init__(
        self,
        pair: str,
        h1_df: pd.DataFrame,
        m15_df: pd.DataFrame,
        data_split: float = 0.7,
        initial_balance: float = 10_000.0,
        risk_pct: float = 0.01,
    ) -> None:
        self.pair = pair
        self.data_split = data_split
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct

        # Pre-compute fixed indicators (EMA, ATR) and sessions to save time in grid loop
        cfg = DEFAULT_PAIR_CONFIGS.get(pair, {})
        if not cfg:
            raise ValueError(f"No config for {pair}")

        atr = ATR(period=cfg["atr_period"])
        ema = EMA(fast=cfg["ema_fast"], slow=cfg["ema_slow"])
        session = SessionFilter()

        # Enriched basics
        h1 = df_with_ema_atr = ema.calculate(atr.calculate(h1_df.copy()))
        self.h1_base = session.tag_sessions(h1)

        m15 = df_with_ema_atr_m15 = ema.calculate(atr.calculate(m15_df.copy()))
        self.m15_base = session.tag_sessions(m15)

        # Re-use engine objects
        self.sig_gen = SignalGenerator()
        self.bt = BacktestEngine(initial_balance=initial_balance, risk_pct=risk_pct)

    def run(self, min_oos_sharpe: float = 0.3) -> OptimizationResult:
        """Execute grid search and return optimization result."""
        # --- Split data chronologically by time to ensure alignment ---
        h1_is, h1_oos, m15_is, m15_oos = self._split_data()

        grid = get_grid_for_pair(self.pair)
        logger.info(
            "%s: searching %d parameter combinations (split=%.0f%%/%.0f%%)",
            self.pair, len(grid), self.data_split * 100, (1 - self.data_split) * 100,
        )

        # --- Grid search on in-sample ---
        best_sharpe = -float("inf")
        best_params: dict[str, Any] = {}
        best_is_trades = 0

        for i, params in enumerate(grid):
            try:
                result = self._backtest_with_params(
                    params, h1_is, m15_is,
                )
            except Exception as e:
                logger.debug("Params %d failed: %s", i, e)
                continue

            if result.total_trades < MIN_IS_TRADES:
                continue

            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_params = params
                best_is_trades = result.total_trades

        # --- Handle no valid results ---
        if not best_params:
            return OptimizationResult(
                pair=self.pair,
                best_params={},
                in_sample_sharpe=0.0,
                out_of_sample_sharpe=0.0,
                out_of_sample_win_rate=0.0,
                out_of_sample_profit_factor=0.0,
                total_combinations_tested=len(grid),
                in_sample_trades=0,
                out_of_sample_trades=0,
                passed_validation=False,
                rejection_reason=f"No parameter set produced >= {MIN_IS_TRADES} trades in-sample",
            )

        # --- Validate on out-of-sample ---
        try:
            oos_result = self._backtest_with_params(best_params, h1_oos, m15_oos)
        except Exception as e:
            return OptimizationResult(
                pair=self.pair,
                best_params=best_params,
                in_sample_sharpe=best_sharpe,
                out_of_sample_sharpe=0.0,
                out_of_sample_win_rate=0.0,
                out_of_sample_profit_factor=0.0,
                total_combinations_tested=len(grid),
                in_sample_trades=best_is_trades,
                out_of_sample_trades=0,
                passed_validation=False,
                rejection_reason=f"OOS backtest failed: {e}",
            )

        # --- Check validation criteria ---
        passed = True
        rejection_reason = None

        if oos_result.sharpe_ratio < min_oos_sharpe:
            passed = False
            rejection_reason = (
                f"OOS Sharpe {oos_result.sharpe_ratio:.4f} < {min_oos_sharpe}"
            )
        elif oos_result.win_rate < MIN_OOS_WIN_RATE:
            passed = False
            rejection_reason = (
                f"OOS win_rate {oos_result.win_rate:.4f} < {MIN_OOS_WIN_RATE}"
            )

        logger.info(
            "%s: best IS Sharpe=%.4f | OOS Sharpe=%.4f | OOS WR=%.2f%% | %s",
            self.pair, best_sharpe, oos_result.sharpe_ratio,
            oos_result.win_rate * 100,
            "PASSED" if passed else f"REJECTED ({rejection_reason})",
        )

        return OptimizationResult(
            pair=self.pair,
            best_params=best_params,
            in_sample_sharpe=best_sharpe,
            out_of_sample_sharpe=oos_result.sharpe_ratio,
            out_of_sample_win_rate=oos_result.win_rate,
            out_of_sample_profit_factor=oos_result.profit_factor,
            total_combinations_tested=len(grid),
            in_sample_trades=best_is_trades,
            out_of_sample_trades=oos_result.total_trades,
            passed_validation=passed,
            rejection_reason=rejection_reason,
        )

    def _split_data(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split both timeframes using a common timestamp from M15."""
        split_idx = int(len(self.m15_base) * self.data_split)
        split_time = self.m15_base["time"].iloc[split_idx]

        h1_is = self.h1_base[self.h1_base["time"] <= split_time].copy()
        h1_oos = self.h1_base[self.h1_base["time"] > split_time].copy()

        m15_is = self.m15_base[self.m15_base["time"] <= split_time].copy()
        m15_oos = self.m15_base[self.m15_base["time"] > split_time].copy()

        return h1_is, h1_oos, m15_is, m15_oos


    def _backtest_with_params(
        self,
        params: dict[str, Any],
        h1_df: pd.DataFrame,
        m15_df: pd.DataFrame,
    ):
        """Run signals + backtest with given params using pre-computed base."""
        # 1. Bollinger (vectorized, fast)
        bb = BollingerBands(period=params["bb_period"], std_dev=params["bb_std_dev"])
        h1 = bb.calculate(h1_df)
        m15 = bb.calculate(m15_df)

        # 2. Regime (classifier only, session already tagged)
        classifier = RegimeClassifier(
            bb_width_threshold=params["bb_width_threshold"],
            atr_ratio_threshold=params["atr_ratio_threshold"],
            min_bb_width=params["min_bb_width"],
        )
        h1 = classifier.classify(h1)
        m15 = classifier.classify(m15)

        # 3. Signals
        signals = self.sig_gen.generate(h1, m15)

        # 4. Backtest
        return self.bt.run(self.pair, signals)
