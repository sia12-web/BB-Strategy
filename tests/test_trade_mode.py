"""Tests for trade_mode module."""

import json
import tempfile
from pathlib import Path

from bb_strategy.live.trade_mode import get_trade_modes


class TestGetTradeModes:
    """Test get_trade_modes()."""

    def test_validated_pair_gets_live_mode(self, tmp_path: Path) -> None:
        """Pair with passed_validation=True gets mode 'live'."""
        results = [
            {"pair": "EUR_USD", "passed_validation": True, "oos_sharpe": 0.8},
            {"pair": "GBP_USD", "passed_validation": False, "oos_sharpe": 0.1},
            {"pair": "USD_JPY", "passed_validation": True, "oos_sharpe": 0.5},
            {"pair": "GBP_JPY", "passed_validation": False, "oos_sharpe": -0.2},
        ]
        results_path = tmp_path / "optimization_results.json"
        results_path.write_text(json.dumps(results))

        modes = get_trade_modes(results_path)

        assert modes["EUR_USD"] == "live"
        assert modes["GBP_USD"] == "paper"
        assert modes["USD_JPY"] == "live"
        assert modes["GBP_JPY"] == "paper"

    def test_missing_file_defaults_to_paper(self, tmp_path: Path) -> None:
        """All pairs return 'paper' when file is missing."""
        missing_path = tmp_path / "nonexistent.json"

        modes = get_trade_modes(missing_path)

        assert all(mode == "paper" for mode in modes.values())
        assert set(modes.keys()) == {"EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"}

    def test_corrupt_json_defaults_to_paper(self, tmp_path: Path) -> None:
        """All pairs return 'paper' when JSON is corrupt."""
        bad_path = tmp_path / "optimization_results.json"
        bad_path.write_text("not valid json {{{")

        modes = get_trade_modes(bad_path)

        assert all(mode == "paper" for mode in modes.values())

    def test_dict_format_results(self, tmp_path: Path) -> None:
        """Handles dict-keyed format: {"EUR_USD": {...}, ...}."""
        results = {
            "EUR_USD": {"passed_validation": True},
            "GBP_USD": {"passed_validation": False},
        }
        results_path = tmp_path / "optimization_results.json"
        results_path.write_text(json.dumps(results))

        modes = get_trade_modes(results_path)

        assert modes["EUR_USD"] == "live"
        assert modes["GBP_USD"] == "paper"

    def test_custom_pairs(self, tmp_path: Path) -> None:
        """Custom pairs list works."""
        results = [
            {"pair": "EUR_USD", "passed_validation": True},
        ]
        results_path = tmp_path / "optimization_results.json"
        results_path.write_text(json.dumps(results))

        modes = get_trade_modes(results_path, pairs=["EUR_USD"])

        assert modes == {"EUR_USD": "live"}
