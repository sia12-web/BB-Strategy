"""Tests for the run_pipeline orchestrator."""

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from bb_strategy.config import Config
from bb_strategy.pipeline import run_pipeline


def _fake_candles_df():
    return pd.DataFrame(
        {
            "time": pd.to_datetime(["2024-01-15T10:00:00Z"]),
            "open": [1.095],
            "high": [1.097],
            "low": [1.094],
            "close": [1.096],
            "volume": [1234.0],
        }
    )


@patch("bb_strategy.pipeline.OandaClient")
def test_run_pipeline_creates_all_files(mock_client_cls, tmp_path):
    """Pipeline creates one parquet file per pair × timeframe."""
    mock_client = MagicMock()
    mock_client.get_candles.return_value = _fake_candles_df()
    mock_client_cls.return_value = mock_client

    cfg = Config(
        OANDA_API_KEY="fake-key",
        OANDA_ACCOUNT_ID="fake-acct",
        DATA_DIR=tmp_path,
    )

    pairs = ["EUR_USD", "GBP_USD"]
    timeframes = ["M15", "H1"]
    run_pipeline(pairs=pairs, timeframes=timeframes, candle_count=100, config=cfg)

    parquet_files = list(tmp_path.glob("*.parquet"))
    assert len(parquet_files) == 4

    expected_names = {f"{p}_{t}.parquet" for p in pairs for t in timeframes}
    actual_names = {f.name for f in parquet_files}
    assert actual_names == expected_names
