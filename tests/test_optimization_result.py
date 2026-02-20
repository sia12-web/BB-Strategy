"""Tests for OptimizationResult serialization."""

import json
import pytest

from bb_strategy.optimization.optimization_result import OptimizationResult


def _sample_result() -> OptimizationResult:
    return OptimizationResult(
        pair="EUR_USD",
        best_params={
            "bb_period": 20, "bb_std_dev": 2.0, "atr_period": 14,
            "bb_width_threshold": 0.002, "atr_ratio_threshold": 0.9,
            "ema_fast": 8, "ema_slow": 21,
        },
        in_sample_sharpe=1.25,
        out_of_sample_sharpe=0.85,
        out_of_sample_win_rate=0.55,
        out_of_sample_profit_factor=1.8,
        total_combinations_tested=480,
        in_sample_trades=120,
        out_of_sample_trades=45,
        passed_validation=True,
    )


def test_serialization_to_json():
    """OptimizationResult serializes to JSON and deserializes back cleanly."""
    result = _sample_result()

    # to_json
    json_str = result.to_json()
    data = json.loads(json_str)

    assert data["pair"] == "EUR_USD"
    assert data["in_sample_sharpe"] == 1.25
    assert data["passed_validation"] is True
    assert data["best_params"]["bb_period"] == 20

    # from_json roundtrip
    restored = OptimizationResult.from_json(json_str)
    assert restored.pair == result.pair
    assert restored.in_sample_sharpe == result.in_sample_sharpe
    assert restored.best_params == result.best_params
    assert restored.passed_validation == result.passed_validation


def test_to_dict_is_flat():
    """to_dict produces a flat JSON-safe dict."""
    result = _sample_result()
    d = result.to_dict()

    assert isinstance(d, dict)
    # best_params is a dict, but it's a value — the top level is flat
    assert "pair" in d
    assert "best_params" in d
    assert isinstance(d["best_params"], dict)

    # Ensure json.dumps works without error
    json.dumps(d)
