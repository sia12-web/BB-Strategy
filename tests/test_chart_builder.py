"""Tests for ChartBuilder output format."""

import pandas as pd
import json
import pytest

from bb_strategy.reporting.chart_builder import ChartBuilder


def test_equity_curve_has_x_and_y():
    """Equity curve JSON has data with x and y of equal length."""
    builder = ChartBuilder()
    equity = [10000, 10050, 10020, 10100, 10080]
    result_json = builder.equity_curve("EUR_USD", equity)
    result = json.loads(result_json)

    # Plotly JSON has 'data' array with traces
    assert "data" in result
    assert len(result["data"]) > 0

    trace = result["data"][0]
    assert "x" in trace
    assert "y" in trace
    assert len(trace["x"]) == len(trace["y"])
    assert len(trace["x"]) == 5


def test_monthly_returns_heatmap_12_months():
    """Trades spanning 12 months produce 12 month buckets."""
    builder = ChartBuilder()
    trades = []
    for month in range(1, 13):
        trades.append({
            "exit_time": f"2024-{month:02d}-15",
            "pnl_usd": 50.0 if month % 2 == 0 else -30.0,
        })

    result_json = builder.monthly_returns_heatmap(trades)
    result = json.loads(result_json)

    assert "data" in result
    trace = result["data"][0]
    assert len(trace["x"]) == 12


def test_drawdown_chart_valid():
    """Drawdown chart produces valid Plotly JSON."""
    builder = ChartBuilder()
    equity = [10000, 9500, 9800, 9200, 9600]
    result_json = builder.drawdown_chart("EUR_USD", equity)
    result = json.loads(result_json)

    assert "data" in result
    trace = result["data"][0]
    assert len(trace["y"]) == 5
    # All drawdown values should be <= 0
    assert all(v <= 0 for v in trace["y"])


def test_combined_equity_multiple_pairs():
    """Combined chart has one trace per pair."""
    builder = ChartBuilder()
    pairs_data = {
        "EUR_USD": {"equity_curve": [10000, 10100]},
        "GBP_USD": {"equity_curve": [10000, 9900]},
    }
    result_json = builder.combined_equity(pairs_data)
    result = json.loads(result_json)

    assert len(result["data"]) == 2
