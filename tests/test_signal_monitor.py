"""Tests for signal_monitor module."""

from unittest.mock import MagicMock, patch, call
import pandas as pd
import numpy as np

from bb_strategy.live.signal_monitor import SignalMonitor


def _make_result_df(signal_value: int = 0) -> pd.DataFrame:
    """Create a minimal strategy result DataFrame."""
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=5, freq="15min", tz="UTC"),
        "close": [1.1000, 1.1005, 1.1010, 1.1015, 1.1020],
        "signal": [0, 0, 0, 0, signal_value],
        "entry_price": [np.nan, np.nan, np.nan, np.nan, 1.1020 if signal_value != 0 else np.nan],
        "stop_loss": [np.nan, np.nan, np.nan, np.nan, 1.0950 if signal_value != 0 else np.nan],
        "take_profit": [np.nan, np.nan, np.nan, np.nan, 1.1050 if signal_value != 0 else np.nan],
    })


class TestSignalMonitor:
    """Test SignalMonitor._check_pair() behavior."""

    def test_no_alert_when_signal_zero(self) -> None:
        """OrderExecutor callback never called when signal=0."""
        mock_fetcher = MagicMock()
        # Return valid OHLCV data (will be passed through StrategyEngine)
        mock_fetcher.fetch_latest.return_value = _make_result_df(signal_value=0)

        mock_strategy = MagicMock()
        mock_strategy.run.return_value = _make_result_df(signal_value=0)

        on_signal = MagicMock()

        monitor = SignalMonitor(
            pairs=["EUR_USD"],
            candle_fetcher=mock_fetcher,
            strategy_engine=mock_strategy,
            on_signal=on_signal,
        )

        # Run a single check
        monitor._check_pair("EUR_USD")

        # Callback should NOT have been called
        on_signal.assert_not_called()

    def test_alert_fires_when_signal_nonzero(self) -> None:
        """on_signal callback fires when last bar has signal=1."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = _make_result_df(signal_value=1)

        mock_strategy = MagicMock()
        mock_strategy.run.return_value = _make_result_df(signal_value=1)

        on_signal = MagicMock()

        monitor = SignalMonitor(
            pairs=["EUR_USD"],
            candle_fetcher=mock_fetcher,
            strategy_engine=mock_strategy,
            on_signal=on_signal,
        )

        monitor._check_pair("EUR_USD")

        on_signal.assert_called_once()
        args = on_signal.call_args
        assert args[0][0] == "EUR_USD"  # pair
        assert args[0][1] == 1  # signal

    def test_short_signal_fires(self) -> None:
        """on_signal callback fires for short signals too."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = _make_result_df(signal_value=-1)

        mock_strategy = MagicMock()
        mock_strategy.run.return_value = _make_result_df(signal_value=-1)

        on_signal = MagicMock()

        monitor = SignalMonitor(
            pairs=["GBP_JPY"],
            candle_fetcher=mock_fetcher,
            strategy_engine=mock_strategy,
            on_signal=on_signal,
        )

        monitor._check_pair("GBP_JPY")

        on_signal.assert_called_once()
        assert on_signal.call_args[0][1] == -1

    def test_empty_data_skips(self) -> None:
        """Empty candle data is handled gracefully without crash."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = pd.DataFrame()

        on_signal = MagicMock()

        monitor = SignalMonitor(
            pairs=["EUR_USD"],
            candle_fetcher=mock_fetcher,
            on_signal=on_signal,
        )

        monitor._check_pair("EUR_USD")  # Should not raise

        on_signal.assert_not_called()

    def test_poll_all_checks_all_pairs(self) -> None:
        """_poll_all iterates over all configured pairs."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = _make_result_df(0)

        mock_strategy = MagicMock()
        mock_strategy.run.return_value = _make_result_df(0)

        pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]
        monitor = SignalMonitor(
            pairs=pairs,
            candle_fetcher=mock_fetcher,
            strategy_engine=mock_strategy,
        )

        monitor._poll_all()

        # Should have fetched both H1 and M15 for each pair = 8 calls
        assert mock_fetcher.fetch_latest.call_count == len(pairs) * 2
