"""Tests for DataStore parquet persistence."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from bb_strategy.data.data_store import DataStore


@pytest.fixture
def tmp_store(tmp_path):
    """DataStore backed by a temporary directory."""
    return DataStore(data_dir=tmp_path)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(["2024-01-15T10:00:00Z", "2024-01-15T11:00:00Z"]),
            "open": [1.095, 1.096],
            "high": [1.097, 1.098],
            "low": [1.094, 1.095],
            "close": [1.096, 1.097],
            "volume": [1234.0, 5678.0],
        }
    )


def test_save_and_load_roundtrip(tmp_store):
    """Save a DataFrame and load it back — contents must match."""
    original = _sample_df()
    tmp_store.save("EUR_USD", "H1", original)

    loaded = tmp_store.load("EUR_USD", "H1")
    pd.testing.assert_frame_equal(loaded, original)


def test_exists_returns_false_when_missing(tmp_store):
    """exists() returns False for a pair/timeframe that was never saved."""
    assert tmp_store.exists("FAKE_PAIR", "H1") is False


def test_exists_returns_true_after_save(tmp_store):
    """exists() returns True after saving."""
    tmp_store.save("GBP_USD", "M15", _sample_df())
    assert tmp_store.exists("GBP_USD", "M15") is True


def test_load_raises_when_missing(tmp_store):
    """load() raises FileNotFoundError for missing data."""
    with pytest.raises(FileNotFoundError):
        tmp_store.load("MISSING", "H1")
