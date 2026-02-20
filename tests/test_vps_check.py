"""Tests for vps_check.py utility."""

import pytest
from unittest.mock import patch, MagicMock
from bb_strategy.live.vps_check import run_vps_check

@patch("sys.version_info")
@patch("importlib.import_module")
@patch("pathlib.Path.exists")
@patch("os.access")
def test_passes_with_valid_env(mock_access, mock_exists, mock_import, mock_ver):
    """vps_check returns 0 when all conditions are met."""
    mock_ver.major = 3
    mock_ver.minor = 11
    mock_import.return_value = MagicMock()
    mock_exists.return_value = True
    mock_access.return_value = True
    
    # Mock os.getenv to return values for required keys
    with patch("os.getenv", return_value="some_value"):
        # Mock load_dotenv to avoid reading files
        with patch("dotenv.load_dotenv"):
             # We also need to mock the parquet check specifically if we want full pass
             with patch("pathlib.Path.exists", return_value=True):
                assert run_vps_check() == 0

@patch("pathlib.Path.exists")
def test_fails_with_missing_env_file(mock_exists):
    """vps_check returns 1 when .env is missing."""
    mock_exists.side_effect = lambda: False # .env check
    # Need to be careful with mock_exists side effects as it's used multiple times
    
    # simpler: mock the whole path object
    with patch("bb_strategy.live.vps_check.Path") as mock_path:
        # .env check is the third Path usage roughly, but let's just make it return False for everything
        mock_instance = mock_path.return_value
        mock_instance.exists.return_value = False
        
        assert run_vps_check() == 1
