"""Startup checks for the live trading engine."""

import logging
import json
from pathlib import Path
from typing import Optional

from bb_strategy.config import Config
from bb_strategy.data.oanda_client import OandaClient

logger = logging.getLogger(__name__)

def run_startup_check() -> bool:
    """Verify optimization results, validated pairs, regional data, and API access.
    
    Returns:
        True if all critical checks pass, False otherwise.
    """
    config = Config()
    passed = True
    
    logger.info("--- Launching Startup Checks ---")

    # 1. Check for optimization_results.json
    results_path = config.DATA_DIR / "optimization_results.json"
    if not results_path.exists():
        logger.error("FAILED [Files]: optimization_results.json missing at %s", results_path)
        passed = False
    else:
        logger.info("PASS [Files]: Found optimization results.")

    # 2. Check for EUR_USD validation
    if passed:
        try:
            with open(results_path) as f:
                data = json.load(f)
            
            eur_usd = data.get("EUR_USD", {})
            if not eur_usd.get("passed_validation", False):
                logger.error("FAILED [Validation]: EUR_USD did not pass validation. Check optimization logs.")
                passed = False
            else:
                logger.info("PASS [Validation]: EUR_USD is validated for trading.")
                
        except Exception as e:
            logger.error("FAILED [Validation]: Could not parse optimization results: %s", e)
            passed = False

    # 3. Check for 3y historical data (parity check)
    if passed:
        missing_data = []
        # Check at least M15 and H1 for the validated pair
        for pair in ["EUR_USD"]:
            for tf in ["M15", "H1"]:
                p = config.DATA_DIR / f"{pair}_{tf}_3y.parquet"
                if not p.exists():
                    missing_data.append(str(p.name))
        
        if missing_data:
            logger.error("FAILED [Data]: Missing required 3y historical files: %s", missing_data)
            passed = False
        else:
            logger.info("PASS [Data]: Historical 3y parquet files found.")

    # 4. Check Oanda connectivity
    if passed:
        try:
            # security: always use 'practice' for the startup ping
            client = OandaClient(environment="practice")
            # Fetch 2 candles to ensure we include at least one complete historical candle
            client.get_candles(pair="EUR_USD", timeframe="M15", count=2)
            logger.info("PASS [API]: Pinged Oanda Practice API successfully.")
        except Exception as e:
            logger.error("FAILED [API]: Oanda Practice API unreachable or credentials invalid: %s", e)
            passed = False

    if passed:
        logger.info("--- ALL CHECKS PASSED: Systems Go ---")
    else:
        logger.error("--- STARTUP FAILED: See errors above ---")

    return passed
