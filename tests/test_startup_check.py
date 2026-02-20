"""Tests for startup_check.py gatekeeper logic."""

import json
import pytest
from unittest.mock import patch, MagicMock
from bb_strategy.live.startup_check import run_startup_check

@pytest.fixture
def mock_config(tmp_path):
    with patch("bb_strategy.live.startup_check.Config") as mock:
        cfg = MagicMock()
        cfg.DATA_DIR = tmp_path
        cfg.PAIRS = ["EUR_USD"]
        mock.return_value = cfg
        yield cfg

def test_fails_if_optimization_missing(mock_config):
    """Fails if optimization_results.json is not found."""
    # Ensure file does not exist
    path = mock_config.DATA_DIR / "optimization_results.json"
    if path.exists():
        path.unlink()
    assert run_startup_check() is False

def test_fails_if_no_validated_pairs(mock_config):
    """Fails if EUR_USD passed_validation is False."""
    results = {
        "EUR_USD": {"passed_validation": False}
    }
    path = mock_config.DATA_DIR / "optimization_results.json"
    with open(path, "w") as f:
        json.dump(results, f)
    
    assert run_startup_check() is False

@patch("bb_strategy.live.startup_check.OandaClient")
def test_passes_if_all_valid(mock_oanda, mock_config):
    """Returns True if files, validation, and API ping are all correct."""
    # 1. results exists and EUR_USD is validated
    results = {
        "EUR_USD": {"passed_validation": True}
    }
    path = mock_config.DATA_DIR / "optimization_results.json"
    with open(path, "w") as f:
        json.dump(results, f)
    
    # 2. 3y parquet data exists
    for tf in ["M15", "H1"]:
        (mock_config.DATA_DIR / f"EUR_USD_{tf}_3y.parquet").touch()
    
    # 3. Mock API ping
    mock_client = MagicMock()
    mock_oanda.return_value = mock_client
    
    assert run_startup_check() is True
    
    # Verify safety requirement: ping used practice environment
    mock_oanda.assert_any_call(environment="practice")
