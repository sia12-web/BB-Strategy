"""Oanda REST API client for fetching OHLCV candle data."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import oandapyV20
import oandapyV20.endpoints.instruments as instruments

from bb_strategy.config import Config


class OandaClient:
    """Thin wrapper around oandapyV20 for candle retrieval."""

    def __init__(
        self,
        config: Optional[Config] = None,
        environment: Optional[str] = None,
    ) -> None:
        self.config = config or Config()
        self.config.validate()
        env = environment or self.config.OANDA_ENV
        self.api = oandapyV20.API(
            access_token=self.config.OANDA_API_KEY,
            environment=env,
        )

    def get_candles(
        self,
        pair: str,
        timeframe: str,
        count: int = 500,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles from Oanda.

        Args:
            pair: Instrument name, e.g. "EUR_USD".
            timeframe: Granularity, e.g. "M15" or "H1".
            count: Number of candles (max 5000).
            from_date: ISO-8601 start time (optional).
            to_date: ISO-8601 end time (optional).

        Returns:
            DataFrame with columns [time, open, high, low, close, volume].
        """
        params: dict = {
            "granularity": timeframe,
            "price": "M",  # midpoint
        }

        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        if not from_date and not to_date:
            params["count"] = str(count)
        elif not from_date or not to_date:
            # If only one is provided, Oanda respects count as well
            params["count"] = str(count)

        endpoint = instruments.InstrumentsCandles(instrument=pair, params=params)
        response = self.api.request(endpoint)

        candles = response.get("candles", [])
        if not candles:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

        records = []
        for c in candles:
            if not c.get("complete", False):
                continue
            mid = c["mid"]
            records.append(
                {
                    "time": c["time"],
                    "open": float(mid["o"]),
                    "high": float(mid["h"]),
                    "low": float(mid["l"]),
                    "close": float(mid["c"]),
                    "volume": float(c["volume"]),
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
            
        df["time"] = pd.to_datetime(df["time"])
        return df
