"""Run signal-pipeline diagnostics for all pairs and print a summary."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from bb_strategy.config import Config
from bb_strategy.diagnostics.filter_counter import FilterCounter

logger = logging.getLogger(__name__)


def run_diagnostics(config: Config | None = None) -> dict:
    """Run FilterCounter for each pair and return combined results.

    Prints a formatted table to stdout and saves counts to
    ``data/diagnostics.json`` (counts only — no candle data).
    """
    cfg = config or Config()
    counter = FilterCounter(config=cfg)

    results: dict[str, dict] = {}
    headers = ["Pair", "Total", "Tradeable", "Ranging", "Near Band", "Re-entry", "Signals"]
    rows: list[list] = []

    for pair in cfg.PAIRS:
        try:
            counts = counter.run(pair)
            results[pair] = counts
            rows.append([
                pair,
                counts["total"],
                counts["tradeable"],
                counts["ranging"],
                counts["near_band"],
                counts["reentry"],
                counts["signals"],
            ])
        except FileNotFoundError as exc:
            logger.warning("Skipping %s: %s", pair, exc)
            results[pair] = {"error": str(exc)}

    # Print table
    try:
        from tabulate import tabulate
        print("\n" + tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    except ImportError:
        # Fallback if tabulate not installed
        print("\n" + "\t".join(headers))
        for row in rows:
            print("\t".join(str(v) for v in row))

    # Save to JSON (counts only — no candle data)
    out_path = cfg.DATA_DIR / "diagnostics.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved diagnostics → %s", out_path)

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_diagnostics()
