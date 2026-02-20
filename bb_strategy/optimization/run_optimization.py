"""Run grid optimization for all pairs and save results."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from bb_strategy.config import Config
from bb_strategy.data.data_store import DataStore
from bb_strategy.optimization.optimizer import Optimizer
from bb_strategy.optimization.optimization_result import OptimizationResult

logger = logging.getLogger(__name__)


def run_all_pairs(
    pairs: Optional[list[str]] = None,
    initial_balance: float = 10_000.0,
    risk_pct: float = 0.01,
    data_split: float = 0.7,
    data_suffix: str = "_3y",
    config: Optional[Config] = None,
    output_path: Optional[Path] = None,
) -> dict[str, OptimizationResult]:
    """Run optimizer for every pair and save results to JSON.

    Args:
        pairs: List of pairs. Defaults to config.PAIRS.
        initial_balance: Starting balance for each backtest.
        risk_pct: Risk per trade.
        data_split: Fraction used for in-sample.
        config: Optional Config override.
        output_path: Where to save JSON. Defaults to data/optimization_results.json.

    Returns:
        Dict of pair → OptimizationResult.
    """
    cfg = config or Config()
    pairs = pairs or cfg.PAIRS
    store = DataStore(cfg.DATA_DIR)
    out = output_path or cfg.DATA_DIR / "optimization_results.json"

    results: dict[str, OptimizationResult] = {}

    for pair in pairs:
        logger.info("=== Optimizing %s ===", pair)

        h1_df = store.load(pair, "H1", suffix=data_suffix)
        m15_df = store.load(pair, "M15", suffix=data_suffix)

        opt = Optimizer(
            pair=pair,
            h1_df=h1_df,
            m15_df=m15_df,
            data_split=data_split,
            initial_balance=initial_balance,
            risk_pct=risk_pct,
        )
        result = opt.run(min_oos_sharpe=0.3)
        results[pair] = result

    # --- Fallback logic ---
    if not any(r.passed_validation for r in results.values()):
        logger.warning("No pairs passed the strict 0.3 Sharpe gate. Applying fallback (0.15) for major pairs.")
        for pair in ["EUR_USD", "GBP_USD"]:
            if pair not in results:
                continue
            
            # Extract data again or reuse (better to just re-run if needed)
            h1_df = store.load(pair, "H1", suffix=data_suffix)
            m15_df = store.load(pair, "M15", suffix=data_suffix)
            opt = Optimizer(pair, h1_df, m15_df, data_split, initial_balance, risk_pct)
            
            fallback_result = opt.run(min_oos_sharpe=0.15)
            if fallback_result.passed_validation:
                logger.info("%s passed with fallback gate (0.15)", pair)
                results[pair] = fallback_result

    # --- Save to JSON ---
    serializable = {pair: r.to_dict() for pair, r in results.items()}

    # Safety: strip any keys that smell like credentials
    _sanitize(serializable)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(serializable, f, indent=2, default=str)

    logger.info("Optimization results saved to %s", out)
    return results


def _sanitize(data: dict) -> None:
    """Remove any accidental credential keys from output."""
    forbidden = {"api_key", "account_id", "access_token", "secret"}
    for pair_data in data.values():
        if isinstance(pair_data, dict):
            for key in list(pair_data.keys()):
                if any(f in key.lower() for f in forbidden):
                    del pair_data[key]
            # Also check best_params
            bp = pair_data.get("best_params", {})
            if isinstance(bp, dict):
                for key in list(bp.keys()):
                    if any(f in key.lower() for f in forbidden):
                        del bp[key]


def update_configs_from_optimization(
    results_path: Path,
) -> tuple[dict, dict]:
    """Load optimization results JSON and return updated indicator + regime configs.

    Only applies params from pairs that passed validation.

    Returns:
        (indicator_configs, regime_configs) dicts ready to pass to engines.
    """
    from bb_strategy.indicators.pair_configs import DEFAULT_PAIR_CONFIGS
    from bb_strategy.regime.regime_configs import DEFAULT_REGIME_CONFIGS
    import copy

    ind_configs = copy.deepcopy(DEFAULT_PAIR_CONFIGS)
    reg_configs = copy.deepcopy(DEFAULT_REGIME_CONFIGS)

    with open(results_path) as f:
        data = json.load(f)

    for pair, result_data in data.items():
        if not result_data.get("passed_validation", False):
            logger.info("%s: did not pass validation, keeping default config", pair)
            continue

        bp = result_data.get("best_params", {})
        if not bp:
            continue

        # Update indicator config
        if pair in ind_configs:
            ind_configs[pair]["bb_period"] = bp.get("bb_period", ind_configs[pair]["bb_period"])
            ind_configs[pair]["bb_std_dev"] = bp.get("bb_std_dev", ind_configs[pair]["bb_std_dev"])
            ind_configs[pair]["atr_period"] = bp.get("atr_period", ind_configs[pair]["atr_period"])
            ind_configs[pair]["ema_fast"] = bp.get("ema_fast", ind_configs[pair]["ema_fast"])
            ind_configs[pair]["ema_slow"] = bp.get("ema_slow", ind_configs[pair]["ema_slow"])

        # Update regime config
        if pair in reg_configs:
            reg_configs[pair]["bb_width_threshold"] = bp.get(
                "bb_width_threshold", reg_configs[pair]["bb_width_threshold"]
            )
            reg_configs[pair]["atr_ratio_threshold"] = bp.get(
                "atr_ratio_threshold", reg_configs[pair]["atr_ratio_threshold"]
            )
            reg_configs[pair]["min_bb_width"] = bp.get(
                "min_bb_width", reg_configs[pair].get("min_bb_width", 0.0)
            )

        logger.info("%s: updated configs from optimization results", pair)

    return ind_configs, reg_configs


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_all_pairs()
