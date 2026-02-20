"""Session tagger based on Montreal (America/Montreal) timezone.

Converts UTC candle times to ET and assigns trading sessions.
"""

from __future__ import annotations

import pandas as pd


# Session boundaries in ET (Eastern Time — EST/EDT handled automatically)
_TZ = "America/Montreal"

# (start_hour, end_hour) — half-open intervals [start, end)
# NOTE: London extended to 12:00 ET (was 08:00) to capture overlap +
#       NY morning liquidity.  Overlap and new_york windows adjusted.
_SESSIONS = {
    "asian":    (19, 2),   # 19:00–02:00 ET  (wraps midnight)
    "london":   (3, 12),   # 03:00–12:00 ET  (extended to cover overlap + NY morning)
    "overlap":  (8, 11),   # 08:00–11:00 ET  (London + NY overlap — still labelled but tradeable via london)
    "new_york": (12, 17),  # 12:00–17:00 ET  (post-morning NY)
    # everything else → "off"
}


class SessionFilter:
    """Tag each row with its trading session and tradeability."""

    VALID_SESSIONS = {"asian", "london", "overlap", "new_york", "off"}

    def tag_sessions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ``session`` and ``tradeable_session`` columns.

        Args:
            df: DataFrame with a ``time`` column in UTC.

        Returns:
            Copy of *df* with two new columns.

        Raises:
            ValueError: If ``time`` column is missing.
        """
        if "time" not in df.columns:
            raise ValueError("DataFrame must have a 'time' column")

        df = df.copy()

        # Convert UTC → Montreal local time
        utc_times = df["time"].dt.tz_localize("UTC") if df["time"].dt.tz is None else df["time"]
        local_times = utc_times.dt.tz_convert(_TZ)
        hours = local_times.dt.hour

        # Classify each hour into a session
        df["session"] = self._classify_hours(hours)

        # Tradeable = asian or london (pre-overlap only)
        df["tradeable_session"] = df["session"].isin({"asian", "london"})

        return df

    @staticmethod
    def _classify_hours(hours: pd.Series) -> pd.Series:
        """Map hour-of-day to session name."""
        result = pd.Series("off", index=hours.index)

        # Asian: 19:00–02:00 ET (wraps midnight)
        result[(hours >= 19) | (hours < 2)] = "asian"

        # London (extended): 03:00–12:00 ET — includes overlap + NY morning
        result[(hours >= 3) & (hours < 12)] = "london"

        # New York (post-morning): 12:00–17:00 ET
        result[(hours >= 12) & (hours < 17)] = "new_york"

        # 02:00–03:00 ET and 17:00–19:00 ET remain "off"
        return result
