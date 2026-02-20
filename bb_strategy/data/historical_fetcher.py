"""Historical data fetcher — batched multi-year candle retrieval from Oanda."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from bb_strategy.config import Config
from bb_strategy.data.oanda_client import OandaClient
from bb_strategy.data.data_store import DataStore

logger = logging.getLogger(__name__)

# Oanda caps at 5000 per request
_MAX_BATCH = 5000
# Rate-limit pause between batch requests (seconds)
_BATCH_DELAY = 0.2


class HistoricalFetcher:
    """Fetch multi-year candle data by batching backward from today.

    Usage::

        fetcher = HistoricalFetcher()
        df = fetcher.fetch_years("EUR_USD", "H1", years=3)
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.client = OandaClient(self.config)
        self.store = DataStore(self.config.DATA_DIR)

    def fetch_years(
        self,
        pair: str,
        timeframe: str,
        years: int = 3,
    ) -> pd.DataFrame:
        """Fetch *years* of historical candles for *pair*/*timeframe*.

        Batches requests of up to 5000 candles, walking backward from
        today.  Deduplicates on the ``time`` column and returns a
        DataFrame sorted ascending.  Saves the result to
        ``data/{pair}_{timeframe}_3y.parquet``.

        Args:
            pair: Oanda instrument name.
            timeframe: Granularity (e.g. ``"M15"``, ``"H1"``).
            years: How many years of data to fetch.

        Returns:
            Combined, deduplicated DataFrame.
        """
        all_batches: list[pd.DataFrame] = []
        to_date: Optional[str] = None
        batch_num = 0

        # Estimate total candles as an upper bound for safety
        # M15 ≈ 4*24*252*years, H1 ≈ 24*252*years
        max_batches = 50  # safety cap

        while batch_num < max_batches:
            batch_num += 1
            logger.info(
                "[%s %s] Batch %d — to_date=%s",
                pair, timeframe, batch_num, to_date,
            )

            try:
                df = self.client.get_candles(
                    pair, timeframe, count=_MAX_BATCH, to_date=to_date,
                )
            except Exception as exc:
                logger.error("Batch %d failed: %s", batch_num, exc)
                break

            if df.empty:
                logger.info("No more candles returned. Stopping.")
                break

            all_batches.append(df)

            # Check if we've gone far enough back
            earliest = df["time"].min()
            cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=years)
            if earliest <= cutoff:
                logger.info(
                    "Reached %d-year cutoff (%s <= %s). Stopping.",
                    years, earliest, cutoff,
                )
                break

            # Walk backward: next batch ends at the earliest time we got
            to_date = earliest.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Respect Oanda rate limits
            time.sleep(_BATCH_DELAY)

        if not all_batches:
            logger.warning("No candles fetched for %s %s", pair, timeframe)
            return pd.DataFrame(
                columns=["time", "open", "high", "low", "close", "volume"]
            )

        # Combine, deduplicate, sort
        combined = pd.concat(all_batches, ignore_index=True)
        combined.drop_duplicates(subset=["time"], inplace=True)
        combined.sort_values("time", inplace=True)
        combined.reset_index(drop=True, inplace=True)

        # Trim to exactly `years` of data
        cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=years)
        combined = combined[combined["time"] >= cutoff].reset_index(drop=True)

        # Save with _3y suffix
        path = self._save_path(pair, timeframe, years)
        path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(path, engine="pyarrow", index=False)
        logger.info("Saved %d rows → %s", len(combined), path)

        return combined

    def _save_path(self, pair: str, timeframe: str, years: int) -> Path:
        return self.config.DATA_DIR / f"{pair}_{timeframe}_{years}y.parquet"
