"""Render report data + charts into a self-contained HTML file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from bb_strategy.reporting.chart_builder import ChartBuilder

TEMPLATE_DIR = Path(__file__).parent / "templates"


class HTMLRenderer:
    """Render report data into a single HTML file."""

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self.chart_builder = ChartBuilder()

    def render(self, report_data: dict[str, Any]) -> str:
        """Produce the full HTML string.

        Args:
            report_data: Output from ReportData.collect().

        Returns:
            Complete HTML string.
        """
        pairs = report_data.get("pairs", {})

        # Build chart JSON
        equity_charts: dict[str, Markup] = {}
        dd_charts: dict[str, Markup] = {}
        all_trades: list[dict] = []

        for pair_name, data in pairs.items():
            if data.get("has_data") and data.get("total_trades", 0) > 0:
                ec = data.get("equity_curve", [])
                equity_charts[pair_name] = Markup(
                    self.chart_builder.equity_curve(pair_name, ec)
                )
                dd_charts[pair_name] = Markup(
                    self.chart_builder.drawdown_chart(pair_name, ec)
                )
                all_trades.extend(data.get("trades", []))

        combined_json = Markup(self.chart_builder.combined_equity(pairs))
        monthly_json = Markup(self.chart_builder.monthly_returns_heatmap(all_trades))

        # Aggregate KPIs
        total_trades = sum(d.get("total_trades", 0) for d in pairs.values())
        winners = sum(
            d.get("total_trades", 0) * d.get("win_rate", 0)
            for d in pairs.values()
        )
        overall_win_rate = (winners / total_trades * 100) if total_trades > 0 else 0

        best_pair = max(
            pairs.keys(),
            key=lambda p: pairs[p].get("total_return_pct", -999),
        ) if pairs else "N/A"

        template = self.env.get_template("report.html")
        return template.render(
            pairs=pairs,
            generated_at=report_data.get("generated_at", ""),
            optimization=report_data.get("optimization"),
            pair_count=len(pairs),
            total_trades=total_trades,
            overall_win_rate=overall_win_rate,
            best_pair=best_pair,
            equity_charts=equity_charts,
            dd_charts=dd_charts,
            combined_equity_json=combined_json,
            monthly_chart_json=monthly_json,
        )

