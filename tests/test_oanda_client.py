"""Tests for OandaClient candle fetching."""

from unittest.mock import patch, MagicMock
import pytest
import pandas as pd

from bb_strategy.data.oanda_client import OandaClient
from bb_strategy.config import Config


# ---------------------------------------------------------------------------
# Unit test — mocked API
# ---------------------------------------------------------------------------

def _make_mock_response():
    """Return a realistic Oanda candles response dict."""
    return {
        "candles": [
            {
                "complete": True,
                "volume": 1234,
                "time": "2024-01-15T10:00:00.000000000Z",
                "mid": {"o": "1.09500", "h": "1.09600", "l": "1.09400", "c": "1.09550"},
            },
            {
                "complete": True,
                "volume": 5678,
                "time": "2024-01-15T11:00:00.000000000Z",
                "mid": {"o": "1.09550", "h": "1.09700", "l": "1.09500", "c": "1.09650"},
            },
            {   # incomplete candle — should be skipped
                "complete": False,
                "volume": 100,
                "time": "2024-01-15T12:00:00.000000000Z",
                "mid": {"o": "1.09650", "h": "1.09700", "l": "1.09600", "c": "1.09680"},
            },
        ]
    }


@patch("bb_strategy.data.oanda_client.oandapyV20.API")
def test_get_candles_returns_correct_columns(mock_api_cls):
    """Mocked: returned DataFrame has the expected 6 columns."""
    mock_api = MagicMock()
    mock_api.request.return_value = _make_mock_response()
    mock_api_cls.return_value = mock_api

    cfg = Config(OANDA_API_KEY="fake-key", OANDA_ACCOUNT_ID="fake-acct")
    client = OandaClient(cfg)
    df = client.get_candles("EUR_USD", "H1", count=100)

    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(df) == 2  # incomplete candle excluded
    assert pd.api.types.is_datetime64_any_dtype(df["time"])
    assert df["open"].dtype == float


# ---------------------------------------------------------------------------
# Integration test — live Oanda practice API (requires .env credentials)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_get_candles_eurusd_h1():
    """Live: fetch 100 H1 candles for EUR_USD from the practice API."""
    cfg = Config()
    if not cfg.OANDA_API_KEY:
        pytest.skip("OANDA_API_KEY not set — skipping live test")

    client = OandaClient(cfg)
    df = client.get_candles("EUR_USD", "H1", count=100)

    assert len(df) > 0
    assert len(df) <= 100
    assert not df.isnull().any().any(), "DataFrame contains null values"
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
