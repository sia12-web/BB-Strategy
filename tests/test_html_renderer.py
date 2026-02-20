"""Tests for HTMLRenderer output validity."""

import pytest

from bb_strategy.reporting.html_renderer import HTMLRenderer


def _sample_report_data() -> dict:
    """Minimal report data for rendering."""
    return {
        "pairs": {
            "EUR_USD": {
                "pair": "EUR_USD",
                "total_trades": 15,
                "win_rate": 0.6,
                "sharpe": 1.2,
                "max_drawdown_pct": 5.5,
                "profit_factor": 1.8,
                "total_return_pct": 3.5,
                "avg_pips_per_trade": 5.2,
                "avg_duration_hours": 4.5,
                "best_trade_usd": 120.50,
                "worst_trade_usd": -45.30,
                "initial_balance": 10000,
                "final_balance": 10350,
                "equity_curve": [10000, 10050, 10100, 10200, 10350],
                "trades": [
                    {
                        "direction": "long", "entry_time": "2024-01-15 05:00",
                        "entry_price": 1.095, "exit_time": "2024-01-15 09:00",
                        "exit_price": 1.097, "exit_reason": "take_profit",
                        "stop_loss": 1.093, "take_profit": 1.097,
                        "units": 1000, "pnl_pips": 20, "pnl_usd": 20.0,
                    }
                ],
                "has_data": True,
            },
            "GBP_USD": {
                "pair": "GBP_USD",
                "total_trades": 10,
                "win_rate": 0.5,
                "sharpe": 0.8,
                "max_drawdown_pct": 8.0,
                "profit_factor": 1.2,
                "total_return_pct": 1.5,
                "avg_pips_per_trade": 3.0,
                "avg_duration_hours": 6.0,
                "best_trade_usd": 80.0,
                "worst_trade_usd": -55.0,
                "initial_balance": 10000,
                "final_balance": 10150,
                "equity_curve": [10000, 10020, 10150],
                "trades": [],
                "has_data": True,
            },
            "USD_JPY": {
                "pair": "USD_JPY",
                "total_trades": 0,
                "win_rate": 0, "sharpe": 0, "max_drawdown_pct": 0,
                "profit_factor": 0, "total_return_pct": 0,
                "avg_pips_per_trade": 0, "avg_duration_hours": 0,
                "best_trade_usd": 0, "worst_trade_usd": 0,
                "initial_balance": 10000, "final_balance": 10000,
                "equity_curve": [], "trades": [],
                "has_data": False,
            },
            "GBP_JPY": {
                "pair": "GBP_JPY",
                "total_trades": 5,
                "win_rate": 0.4,
                "sharpe": 0.3,
                "max_drawdown_pct": 12.0,
                "profit_factor": 0.9,
                "total_return_pct": -2.0,
                "avg_pips_per_trade": -1.5,
                "avg_duration_hours": 3.0,
                "best_trade_usd": 40.0,
                "worst_trade_usd": -80.0,
                "initial_balance": 10000,
                "final_balance": 9800,
                "equity_curve": [10000, 9900, 9800],
                "trades": [],
                "has_data": True,
            },
        },
        "optimization": None,
        "generated_at": "2024-01-20T12:00:00",
    }


def test_render_produces_valid_html():
    """Output starts with <!DOCTYPE html> and contains plotly div."""
    renderer = HTMLRenderer()
    html = renderer.render(_sample_report_data())

    assert html.strip().startswith("<!DOCTYPE html>")
    assert "plotly" in html.lower()
    assert "<table>" in html


def test_render_contains_all_pairs():
    """All 4 pair names appear in the rendered HTML."""
    renderer = HTMLRenderer()
    html = renderer.render(_sample_report_data())

    for pair in ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]:
        assert pair in html
