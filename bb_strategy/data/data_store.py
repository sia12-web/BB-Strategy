"""Local parquet-based data store for OHLCV candle data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bb_strategy.config import Config


class DataStore:
    """Read/write parquet files for pair+timeframe combinations."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Config().DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pair: str, timeframe: str, suffix: str = "") -> Path:
        return self.data_dir / f"{pair}_{timeframe}{suffix}.parquet"

    def save(self, pair: str, timeframe: str, df: pd.DataFrame) -> Path:
        """Save DataFrame as parquet. Returns the file path."""
        path = self._path(pair, timeframe)
        df.to_parquet(path, engine="pyarrow", index=False)
        return path

    def load(self, pair: str, timeframe: str, suffix: str = "") -> pd.DataFrame:
        """Load parquet into DataFrame. Raises FileNotFoundError if missing."""
        path = self._path(pair, timeframe, suffix=suffix)
        if not path.exists():
            raise FileNotFoundError(f"No data file at {path}")
        return pd.read_parquet(path, engine="pyarrow")

    def exists(self, pair: str, timeframe: str) -> bool:
        """Check whether a parquet file exists for this pair+timeframe."""
        return self._path(pair, timeframe).exists()
