"""Build Plotly chart JSON dicts for the HTML report."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio


class ChartBuilder:
    """Create Plotly chart JSON dicts from report data."""

    PLOTLY_CONFIG = {"displayModeBar": True, "responsive": True}

    # ------------------------------------------------------------------
    # Equity curve
    # ------------------------------------------------------------------

    def equity_curve(self, pair: str, equity_data: list[float]) -> str:
        """Build equity curve line chart. Returns Plotly JSON string."""
        x = list(range(len(equity_data)))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=equity_data,
            mode="lines",
            name=pair,
            line=dict(width=2),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.1)",
        ))
        fig.update_layout(
            title=f"{pair} — Equity Curve",
            xaxis_title="Bar Index",
            yaxis_title="Balance ($)",
            template="plotly_dark",
            height=350,
            margin=dict(l=50, r=20, t=50, b=40),
        )
        return pio.to_json(fig)

    # ------------------------------------------------------------------
    # Drawdown chart
    # ------------------------------------------------------------------

    def drawdown_chart(self, pair: str, equity_data: list[float]) -> str:
        """Build drawdown area chart. Returns Plotly JSON string."""
        if not equity_data:
            return pio.to_json(go.Figure())

        peak = equity_data[0]
        dd = []
        for val in equity_data:
            if val > peak:
                peak = val
            dd.append((val - peak) / peak * 100 if peak != 0 else 0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(dd))), y=dd,
            mode="lines",
            name="Drawdown %",
            line=dict(color="#ef4444", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.15)",
        ))
        fig.update_layout(
            title=f"{pair} — Drawdown",
            xaxis_title="Bar Index",
            yaxis_title="Drawdown (%)",
            template="plotly_dark",
            height=250,
            margin=dict(l=50, r=20, t=50, b=40),
        )
        return pio.to_json(fig)

    # ------------------------------------------------------------------
    # Monthly returns heatmap
    # ------------------------------------------------------------------

    def monthly_returns_heatmap(self, trades: list[dict]) -> str:
        """Build monthly PnL heatmap. Returns Plotly JSON string."""
        if not trades:
            return pio.to_json(go.Figure())

        # Bucket trades by Year-Month of exit
        monthly: dict[str, float] = defaultdict(float)
        for t in trades:
            exit_time = t.get("exit_time")
            if not exit_time:
                continue
            try:
                import pandas as pd
                ts = pd.Timestamp(exit_time)
                key = ts.strftime("%Y-%m")
                monthly[key] += t.get("pnl_usd", 0)
            except Exception:
                continue

        if not monthly:
            return pio.to_json(go.Figure())

        # Sort by date
        sorted_keys = sorted(monthly.keys())
        months = sorted_keys
        values = [round(monthly[k], 2) for k in sorted_keys]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=months, y=values,
            marker_color=[
                "#22c55e" if v >= 0 else "#ef4444" for v in values
            ],
        ))
        fig.update_layout(
            title="Monthly P&L ($)",
            xaxis_title="Month",
            yaxis_title="P&L ($)",
            template="plotly_dark",
            height=300,
            margin=dict(l=50, r=20, t=50, b=40),
        )
        return pio.to_json(fig)

    # ------------------------------------------------------------------
    # Combined equity multi-pair
    # ------------------------------------------------------------------

    def combined_equity(self, pairs_data: dict[str, dict]) -> str:
        """Overlay equity curves for all pairs."""
        colors = ["#6366f1", "#22c55e", "#f59e0b", "#ec4899"]
        fig = go.Figure()

        for i, (pair, data) in enumerate(pairs_data.items()):
            ec = data.get("equity_curve", [])
            if not ec:
                continue
            fig.add_trace(go.Scatter(
                x=list(range(len(ec))), y=ec,
                mode="lines",
                name=pair,
                line=dict(width=2, color=colors[i % len(colors)]),
            ))

        fig.update_layout(
            title="All Pairs — Equity Curves",
            xaxis_title="Bar Index",
            yaxis_title="Balance ($)",
            template="plotly_dark",
            height=400,
            margin=dict(l=50, r=20, t=50, b=40),
            legend=dict(orientation="h", y=1.12),
        )
        return pio.to_json(fig)
