"""Generate the HTML backtest report."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from bb_strategy.config import Config
from bb_strategy.reporting.report_data import ReportData
from bb_strategy.reporting.html_renderer import HTMLRenderer

logger = logging.getLogger(__name__)


def generate_report(
    output_path: Optional[str] = None,
    config: Optional[Config] = None,
    pairs: Optional[list[str]] = None,
    initial_balance: float = 10_000.0,
    data_suffix: str = "_3y",
) -> Path:
    """Collect data, build charts, render HTML report.

    Args:
        output_path: Where to save. Defaults to data/report.html.
        config: Optional Config override.
        pairs: Pair list override.
        initial_balance: Starting balance.

    Returns:
        Path to the generated report.
    """
    cfg = config or Config()
    out = Path(output_path) if output_path else cfg.DATA_DIR / "report.html"

    logger.info("Collecting report data (suffix='%s')...", data_suffix)
    collector = ReportData(
        config=cfg,
        initial_balance=initial_balance,
        data_suffix=data_suffix,
    )
    data = collector.collect(pairs=pairs)

    logger.info("Rendering HTML report...")
    renderer = HTMLRenderer()
    html = renderer.render(data)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    logger.info("Report saved to %s", out)

    return out


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    generate_report()
