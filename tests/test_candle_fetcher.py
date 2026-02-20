"""Tests for candle_fetcher module."""

from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from bb_strategy.live.candle_fetcher import CandleFetcher


def _make_ohlcv(n: int = 50) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame."""
    np.random.seed(42)
    close = 1.1000 + np.cumsum(np.random.randn(n) * 0.001)
    return pd.DataFrame({
        "time": pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC"),
        "open": close - 0.0005,
        "high": close + 0.001,
        "low": close - 0.001,
        "close": close,
        "volume": np.random.randint(100, 1000, size=n).astype(float),
    })


class TestCandleFetcher:
    """Test CandleFetcher.fetch_latest()."""

    def test_fetch_returns_indicator_columns(self) -> None:
        """Mock OandaClient, assert output has bb_upper and regime columns."""
        mock_client = MagicMock()
        mock_client.get_candles.return_value = _make_ohlcv(50)

        fetcher = CandleFetcher(oanda_client=mock_client)
        result = fetcher.fetch_latest("EUR_USD", "H1", count=50)

        # Should have indicator columns
        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns
        assert "atr" in result.columns
        assert "ema_fast" in result.columns

        # Should have regime columns
        assert "regime" in result.columns
        assert "session" in result.columns
        assert "tradeable_session" in result.columns

        # Data should not be empty
        assert len(result) == 50

    def test_empty_candles_returns_empty(self) -> None:
        """Empty candle data returns empty DataFrame."""
        mock_client = MagicMock()
        mock_client.get_candles.return_value = pd.DataFrame()

        fetcher = CandleFetcher(oanda_client=mock_client)
        result = fetcher.fetch_latest("EUR_USD", "H1")

        assert result.empty
