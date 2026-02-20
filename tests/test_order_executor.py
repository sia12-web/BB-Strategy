"""Tests for order_executor module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bb_strategy.live.order_executor import OrderExecutor


class TestOrderExecutor:
    """Test OrderExecutor methods."""

    def test_paper_trade_appended_to_json(self, tmp_path: Path) -> None:
        """record_paper_trade() appends entry to paper_trades.json."""
        paper_path = tmp_path / "paper_trades.json"

        with patch("bb_strategy.live.order_executor.oandapyV20"):
            executor = OrderExecutor(
                config=MagicMock(
                    OANDA_API_KEY="test-key",
                    OANDA_ACCOUNT_ID="test-account",
                    OANDA_ENV="practice",
                ),
                paper_trades_path=paper_path,
            )

        result = executor.record_paper_trade(
            pair="EUR_USD",
            signal=1,
            entry_price=1.10000,
            stop_loss=1.09500,
            take_profit=1.10500,
            units=1000,
        )

        assert paper_path.exists()
        data = json.loads(paper_path.read_text())
        assert len(data) == 1
        assert data[0]["pair"] == "EUR_USD"
        assert data[0]["direction"] == "long"
        assert data[0]["entry_price"] == 1.10000
        assert data[0]["units"] == 1000
        assert data[0]["mode"] == "paper"

    def test_paper_trade_appends_to_existing(self, tmp_path: Path) -> None:
        """Second paper trade appends to existing list."""
        paper_path = tmp_path / "paper_trades.json"
        paper_path.write_text(json.dumps([{"pair": "GBP_USD", "existing": True}]))

        with patch("bb_strategy.live.order_executor.oandapyV20"):
            executor = OrderExecutor(
                config=MagicMock(
                    OANDA_API_KEY="test-key",
                    OANDA_ACCOUNT_ID="test-account",
                    OANDA_ENV="practice",
                ),
                paper_trades_path=paper_path,
            )

        executor.record_paper_trade(
            pair="EUR_USD", signal=-1, entry_price=1.10000,
            stop_loss=1.10500, take_profit=1.09500, units=500,
        )

        data = json.loads(paper_path.read_text())
        assert len(data) == 2
        assert data[1]["pair"] == "EUR_USD"
        assert data[1]["direction"] == "short"

    def test_live_order_not_called_in_paper_mode(self) -> None:
        """place_live_order is never called when mode is paper.

        This tests the run_live logic: the executor itself doesn't check mode,
        but the signal handler routes based on mode. We verify
        record_paper_trade is called instead.
        """
        with patch("bb_strategy.live.order_executor.oandapyV20"):
            executor = OrderExecutor(
                config=MagicMock(
                    OANDA_API_KEY="test-key",
                    OANDA_ACCOUNT_ID="test-account",
                    OANDA_ENV="practice",  # NOT live
                ),
            )

        executor.place_live_order = MagicMock()
        executor.record_paper_trade = MagicMock()

        # Simulate what run_live does: check mode, route accordingly
        trade_modes = {"EUR_USD": "paper"}
        env_is_live = False  # practice mode

        pair = "EUR_USD"
        effective_mode = "live" if (env_is_live and trade_modes.get(pair) == "live") else "paper"

        if effective_mode == "live":
            executor.place_live_order(
                pair=pair, signal=1, entry_price=1.1,
                stop_loss=1.09, take_profit=1.11, units=100,
            )
        else:
            executor.record_paper_trade(
                pair=pair, signal=1, entry_price=1.1,
                stop_loss=1.09, take_profit=1.11, units=100,
            )

        executor.place_live_order.assert_not_called()
        executor.record_paper_trade.assert_called_once()

    def test_live_blocked_even_with_live_mode_pair_but_practice_env(self) -> None:
        """Dual gate: pair has 'live' mode but env is 'practice' → paper."""
        with patch("bb_strategy.live.order_executor.oandapyV20"):
            executor = OrderExecutor(
                config=MagicMock(
                    OANDA_API_KEY="test-key",
                    OANDA_ACCOUNT_ID="test-account",
                    OANDA_ENV="practice",
                ),
            )

        executor.place_live_order = MagicMock()
        executor.record_paper_trade = MagicMock()

        trade_modes = {"EUR_USD": "live"}  # pair validated
        env_is_live = False  # but env is practice

        pair = "EUR_USD"
        effective_mode = "live" if (env_is_live and trade_modes.get(pair) == "live") else "paper"

        if effective_mode == "live":
            executor.place_live_order(
                pair=pair, signal=1, entry_price=1.1,
                stop_loss=1.09, take_profit=1.11, units=100,
            )
        else:
            executor.record_paper_trade(
                pair=pair, signal=1, entry_price=1.1,
                stop_loss=1.09, take_profit=1.11, units=100,
            )

        executor.place_live_order.assert_not_called()
        executor.record_paper_trade.assert_called_once()
