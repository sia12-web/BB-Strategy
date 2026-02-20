"""Bar-by-bar backtesting engine with SL/TP simulation."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.backtest.trade import Trade
from bb_strategy.backtest.backtest_result import BacktestResult
from bb_strategy.strategy.position_sizer import PositionSizer

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Simulate trade lifecycle bar-by-bar on a signals DataFrame.

    Rules
    -----
    - One open trade at a time (no pyramiding).
    - On a signal bar (signal ≠ 0): open a trade if none open.
    - Each bar: check if SL or TP is hit using bar high/low.
      - SL is checked **before** TP (conservative — same-bar priority to SL).
    - exit_signal == 1 also closes the trade.
    - Balance compounds across trades.
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        risk_pct: float = 0.01,
    ) -> None:
        if initial_balance <= 0:
            raise ValueError(f"initial_balance must be > 0, got {initial_balance}")
        if not (0.001 <= risk_pct <= 0.05):
            raise ValueError(f"risk_pct must be in [0.001, 0.05], got {risk_pct}")

        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.sizer = PositionSizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, pair: str, signals_df: pd.DataFrame) -> BacktestResult:
        """Execute a bar-by-bar backtest.

        Args:
            pair: Instrument name.
            signals_df: M15 DataFrame with signal columns from StrategyEngine.

        Returns:
            BacktestResult with all trades and metrics.
        """
        df = signals_df.copy()
        self._validate(df)

        balance = self.initial_balance
        equity_curve: list[float] = [balance]
        trades: list[Trade] = []
        open_trade: Optional[Trade] = None

        for row in df.itertuples(index=False):
            if open_trade is not None:
                # --- Check exits on current bar ---
                closed = self._check_exit(open_trade, row)
                if closed:
                    balance += open_trade.pnl_usd
                    trades.append(open_trade)
                    open_trade = None

            # --- Check new entry (only if no open trade) ---
            if open_trade is None and row.signal != 0:
                open_trade = self._open_trade(pair, row, balance)

            equity_curve.append(balance)

        # Close any remaining open trade at last bar's close
        if open_trade is not None:
            last = df.iloc[-1]
            open_trade.close(
                exit_time=last["time"],
                exit_price=last["close"],
                exit_reason="end_of_data",
            )
            balance += open_trade.pnl_usd
            trades.append(open_trade)
            equity_curve.append(balance)

        return BacktestResult(
            pair=pair,
            trades=trades,
            initial_balance=self.initial_balance,
            final_balance=balance,
            equity_curve=equity_curve,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _open_trade(self, pair: str, row, balance: float) -> Trade:
        """Create a new Trade from a signal row."""
        units = self.sizer.calculate(
            account_balance=balance,
            risk_pct=self.risk_pct,
            entry_price=row.entry_price,
            stop_loss=row.stop_loss,
            pair=pair,
        )
        return Trade(
            pair=pair,
            direction=row.signal,
            entry_time=row.time,
            entry_price=row.entry_price,
            stop_loss=row.stop_loss,
            take_profit=row.take_profit,
            units=units,
        )

    @staticmethod
    def _check_exit(trade: Trade, row) -> bool:
        """Check SL, TP, and exit_signal. Returns True if trade was closed."""
        bar_high = row.high
        bar_low = row.low

        if trade.direction == 1:  # Long
            # SL first (conservative)
            if bar_low <= trade.stop_loss:
                trade.close(row.time, trade.stop_loss, "stop_loss")
                return True
            if bar_high >= trade.take_profit:
                trade.close(row.time, trade.take_profit, "take_profit")
                return True
        else:  # Short
            if bar_high >= trade.stop_loss:
                trade.close(row.time, trade.stop_loss, "stop_loss")
                return True
            if bar_low <= trade.take_profit:
                trade.close(row.time, trade.take_profit, "take_profit")
                return True

        # Exit signal (regime flip, ema cross change)
        if getattr(row, "exit_signal", 0) == 1:
            trade.close(row.time, row.close, "exit_signal")
            return True

        return False

    @staticmethod
    def _validate(df: pd.DataFrame) -> None:
        required = {
            "time", "high", "low", "close",
            "signal", "entry_price", "stop_loss", "take_profit", "exit_signal",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"signals_df missing columns: {missing}")
