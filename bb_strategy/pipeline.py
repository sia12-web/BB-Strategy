"""Data pipeline: fetch candles from Oanda and persist locally."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from bb_strategy.config import Config
from bb_strategy.data.oanda_client import OandaClient
from bb_strategy.data.data_store import DataStore
from bb_strategy.data.historical_fetcher import HistoricalFetcher

logger = logging.getLogger(__name__)


def run_pipeline(
    pairs: Optional[list[str]] = None,
    timeframes: Optional[list[str]] = None,
    target_count: int = 5000,
    config: Optional[Config] = None,
) -> None:
    """Fetch and store candles for every pair × timeframe combination.

    Args:
        pairs: List of instrument names. Defaults to config.PAIRS.
        timeframes: List of granularities. Defaults to config.TIMEFRAMES.
        target_count: Total number of candles to try and fetch (will use multiple requests if > 5000).
        config: Optional Config override.
    """
    cfg = config or Config()
    pairs = pairs or cfg.PAIRS
    timeframes = timeframes or cfg.TIMEFRAMES

    client = OandaClient(cfg)
    store = DataStore(cfg.DATA_DIR)

    for pair in pairs:
        for tf in timeframes:
            logger.info("Fetching %s %s (target: %d candles)...", pair, tf, target_count)
            
            all_candles = []
            to_date = None
            remaining = target_count
            
            while remaining > 0:
                fetch_count = min(remaining, 5000)
                logger.info("  Requesting %d candles (to_date=%s)...", fetch_count, to_date)
                
                try:
                    df = client.get_candles(pair, tf, count=fetch_count, to_date=to_date)
                except Exception as e:
                    logger.error("  Error fetching candles: %s", e)
                    break

                if df.empty:
                    logger.info("  No more candles returned by API.")
                    break
                
                all_candles.append(df)
                remaining -= len(df)
                
                # Update to_date to the oldest candle's time to fetch previous chunk
                to_date = df["time"].min().strftime("%Y-%m-%dT%H:%M:%SZ")

            if not all_candles:
                logger.warning("No candles fetched for %s %s", pair, tf)
                continue

            final_df = pd.concat(all_candles).drop_duplicates(subset=["time"]).sort_values("time")
            path = store.save(pair, tf, final_df)
            logger.info("Saved %d rows → %s", len(final_df), path)


def run_full_pipeline(
    years: int = 3,
    pairs: Optional[list[str]] = None,
    timeframes: Optional[list[str]] = None,
    config: Optional[Config] = None,
) -> None:
    """Fetch multi-year data for all pairs × timeframes using HistoricalFetcher.

    Saves to ``data/{pair}_{timeframe}_{years}y.parquet``.

    Args:
        years: Number of years to fetch (default 3).
        pairs: Instrument list. Defaults to config.PAIRS.
        timeframes: Granularities. Defaults to config.TIMEFRAMES.
        config: Optional Config override.
    """
    cfg = config or Config()
    pairs = pairs or cfg.PAIRS
    timeframes = timeframes or cfg.TIMEFRAMES

    fetcher = HistoricalFetcher(config=cfg)

    for pair in pairs:
        for tf in timeframes:
            logger.info("Fetching %d years of %s %s...", years, pair, tf)
            df = fetcher.fetch_years(pair, tf, years=years)
            logger.info("  %s %s → %d rows", pair, tf, len(df))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_full_pipeline(years=3)

