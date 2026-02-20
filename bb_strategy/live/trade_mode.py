"""Trade mode resolver: determines live vs paper mode per pair."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_RESULTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "optimization_results.json"


def get_trade_modes(
    results_path: Path | str = DEFAULT_RESULTS_PATH,
    pairs: list[str] | None = None,
) -> dict[str, str]:
    """Load optimization results and return per-pair trade mode.

    Args:
        results_path: Path to optimization_results.json.
        pairs: List of pairs to include. Defaults to the 4 configured pairs.

    Returns:
        Dict mapping pair → "live" | "paper".
        A pair gets "live" only if passed_validation is True in the JSON.
        Falls back to "paper" for all if file is missing or unreadable.
    """
    if pairs is None:
        pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]

    results_path = Path(results_path)

    # Default: everything is paper
    modes: dict[str, str] = {pair: "paper" for pair in pairs}

    if not results_path.exists():
        logger.warning("Optimization results not found at %s — all pairs default to paper", results_path)
        return modes

    try:
        with open(results_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read optimization results: %s — all pairs default to paper", exc)
        return modes

    # data is expected to be a list of result dicts
    if isinstance(data, list):
        for entry in data:
            pair = entry.get("pair", "")
            if pair in modes and entry.get("passed_validation", False):
                modes[pair] = "live"
    elif isinstance(data, dict):
        # Handle dict-keyed format: {"EUR_USD": {...}, ...}
        for pair in pairs:
            entry = data.get(pair, {})
            if entry.get("passed_validation", False):
                modes[pair] = "live"

    logger.info("Trade modes: %s", modes)
    return modes
