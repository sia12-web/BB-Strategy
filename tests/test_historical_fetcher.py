"""Tests for HistoricalFetcher batching and deduplication."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from bb_strategy.data.historical_fetcher import HistoricalFetcher


def _make_candle_df(start: str, periods: int, freq: str = "h") -> pd.DataFrame:
    """Create a synthetic candle DataFrame."""
    times = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    close = np.linspace(1.10, 1.12, periods)
    return pd.DataFrame({
        "time": times,
        "open": close - 0.001,
        "high": close + 0.002,
        "low": close - 0.002,
        "close": close,
        "volume": np.full(periods, 500.0),
    })


class TestBatchingDeduplication:
    """test_batching_deduplicates_overlapping_candles"""

    @patch("bb_strategy.data.historical_fetcher.time.sleep")
    def test_batching_deduplicates_overlapping_candles(self, mock_sleep):
        """Two batches with 10 overlapping rows → final df has no duplicate timestamps."""
        # Create overlapping data explicitly
        base = _make_candle_df("2024-01-01", 100)
        batch1 = base.iloc[:60].copy()  # rows 0-59
        batch2 = base.iloc[50:].copy()  # rows 50-99 → 10 overlap

        with patch.object(HistoricalFetcher, "__init__", return_value=None):
            fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
            fetcher.config = MagicMock()
            fetcher.config.DATA_DIR = MagicMock()
            fetcher.config.DATA_DIR.__truediv__ = MagicMock(return_value=MagicMock())
            fetcher.client = MagicMock()

            # First call returns batch1 (most recent), second returns batch2 (older),
            # third returns empty to stop
            fetcher.client.get_candles.side_effect = [batch1, batch2, pd.DataFrame()]

            # Mock save path
            mock_path = MagicMock()
            mock_path.parent.mkdir = MagicMock()
            fetcher._save_path = MagicMock(return_value=mock_path)

            # Patch pd.DataFrame.to_parquet to avoid actual file writes
            with patch.object(pd.DataFrame, "to_parquet"):
                result = fetcher.fetch_years("EUR_USD", "H1", years=3)

        # Should have 100 unique rows, not 110
        assert len(result) == len(result.drop_duplicates(subset=["time"]))
        # No duplicate timestamps
        assert result["time"].is_unique

    @patch("bb_strategy.data.historical_fetcher.time.sleep")
    def test_result_sorted_ascending(self, mock_sleep):
        """Result DataFrame must be sorted ascending by time."""
        base = _make_candle_df("2024-01-01", 100)
        batch1 = base.iloc[50:].copy()  # later data first (simulating backward walk)
        batch2 = base.iloc[:60].copy()  # earlier data second, 10 overlap

        with patch.object(HistoricalFetcher, "__init__", return_value=None):
            fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
            fetcher.config = MagicMock()
            fetcher.config.DATA_DIR = MagicMock()
            fetcher.config.DATA_DIR.__truediv__ = MagicMock(return_value=MagicMock())
            fetcher.client = MagicMock()
            fetcher.client.get_candles.side_effect = [batch1, batch2, pd.DataFrame()]

            mock_path = MagicMock()
            mock_path.parent.mkdir = MagicMock()
            fetcher._save_path = MagicMock(return_value=mock_path)

            with patch.object(pd.DataFrame, "to_parquet"):
                result = fetcher.fetch_years("EUR_USD", "H1", years=3)

        assert result["time"].is_monotonic_increasing
