"""Signal monitor: polls candles and detects BB strategy signals."""

from __future__ import annotations

import logging
import time
from typing import Optional

import schedule

from bb_strategy.live.candle_fetcher import CandleFetcher
from bb_strategy.strategy.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)


class SignalMonitor:
    """Poll Oanda for candle data and detect trade signals.

    Loops forever, fetching H1 + M15 candles for each pair on a schedule,
    running StrategyEngine, and invoking a callback when signal != 0.
    """

    def __init__(
        self,
        pairs: list[str],
        poll_interval_seconds: int = 60,
        candle_fetcher: Optional[CandleFetcher] = None,
        strategy_engine: Optional[StrategyEngine] = None,
        on_signal: Optional[callable] = None,
    ) -> None:
        """
        Args:
            pairs: List of instrument names to monitor.
            poll_interval_seconds: Seconds between polling cycles.
            candle_fetcher: Injected CandleFetcher (default creates one).
            strategy_engine: Injected StrategyEngine (default creates one).
            on_signal: Callback(pair, signal, row) invoked when signal != 0.
        """
        self.pairs = pairs
        self.poll_interval_seconds = poll_interval_seconds
        self.candle_fetcher = candle_fetcher or CandleFetcher()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.on_signal = on_signal
        self._running = False

    def _check_pair(self, pair: str) -> None:
        """Fetch candles for a pair and check the last bar for signals."""
        try:
            h1_df = self.candle_fetcher.fetch_latest(pair, "H1", count=100)
            m15_df = self.candle_fetcher.fetch_latest(pair, "M15", count=100)

            if h1_df.empty or m15_df.empty:
                logger.warning("Empty candle data for %s — skipping", pair)
                return

            # Run strategy to get signals
            result = self.strategy_engine.run(pair, h1_df, m15_df)

            if result.empty:
                return

            # Check last bar only
            last_row = result.iloc[-1]
            signal = int(last_row.get("signal", 0))

            if signal != 0:
                logger.info(
                    "Signal detected: %s %s @ %s",
                    pair,
                    "LONG" if signal == 1 else "SHORT",
                    last_row.get("entry_price", "N/A"),
                )
                if self.on_signal:
                    self.on_signal(pair, signal, last_row)

        except Exception:
            logger.exception("Error checking pair %s", pair)

    def _poll_all(self) -> None:
        """Run a single poll cycle across all pairs."""
        logger.debug("Starting poll cycle for %d pairs", len(self.pairs))
        for pair in self.pairs:
            self._check_pair(pair)
        logger.debug("Poll cycle complete")

    def run(self) -> None:
        """Start the polling loop. Blocks forever.

        Uses the ``schedule`` library to run _poll_all every
        ``poll_interval_seconds``. Can be stopped by setting
        ``self._running = False`` from another thread.
        """
        self._running = True
        logger.info(
            "Signal monitor starting — polling %d pairs every %ds",
            len(self.pairs), self.poll_interval_seconds,
        )

        # Run immediately on start
        self._poll_all()

        # Schedule subsequent runs
        schedule.every(self.poll_interval_seconds).seconds.do(self._poll_all)

        while self._running:
            schedule.run_pending()
            time.sleep(1)
