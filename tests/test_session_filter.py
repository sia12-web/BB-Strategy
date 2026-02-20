"""Tests for SessionFilter timezone and session tagging."""

import numpy as np
import pandas as pd
import pytest

from bb_strategy.regime.session_filter import SessionFilter


def _utc_df(hours_utc: list[int], date: str = "2024-01-15") -> pd.DataFrame:
    """Build a DataFrame with UTC timestamps at specific hours."""
    times = [pd.Timestamp(f"{date} {h:02d}:00:00", tz="UTC") for h in hours_utc]
    return pd.DataFrame({"time": pd.to_datetime([t.tz_localize(None) for t in times])})


def _utc_df_from_et(hours_et: list[int], date: str = "2024-01-15") -> pd.DataFrame:
    """Build a DataFrame where the *local ET* hour matches the given list.

    January → EST (UTC-5), so UTC hour = ET hour + 5.
    """
    utc_hours = [(h + 5) % 24 for h in hours_et]
    times = [pd.Timestamp(f"{date} {h:02d}:00:00") for h in utc_hours]
    return pd.DataFrame({"time": pd.to_datetime(times)})


def test_session_column_only_valid_values():
    """session column only contains the defined set of values."""
    df = _utc_df(list(range(24)))
    result = SessionFilter().tag_sessions(df)
    assert result["session"].isin(SessionFilter.VALID_SESSIONS).all()


def test_asian_session_tagged_correctly():
    """21:00 ET → asian session."""
    df = _utc_df_from_et([21, 22, 23, 0, 1])
    result = SessionFilter().tag_sessions(df)
    assert (result["session"] == "asian").all()


def test_london_session_tagged_correctly():
    """03:00–11:00 ET → london session (extended window)."""
    df = _utc_df_from_et([3, 4, 5, 6, 7, 8, 9, 10, 11])
    result = SessionFilter().tag_sessions(df)
    assert (result["session"] == "london").all()


def test_ny_session_starts_at_noon():
    """12:00–16:00 ET → new_york session."""
    df = _utc_df_from_et([12, 13, 14, 15, 16])
    result = SessionFilter().tag_sessions(df)
    assert (result["session"] == "new_york").all()


def test_tradeable_session_true_during_extended_london():
    """09:00 ET is now london (extended) → tradeable_session must be True."""
    df = _utc_df_from_et([9])
    result = SessionFilter().tag_sessions(df)
    assert result["tradeable_session"].iloc[0] is np.bool_(True)


def test_tradeable_session_true_during_london():
    """05:00 ET is london → tradeable_session must be True."""
    df = _utc_df_from_et([5])
    result = SessionFilter().tag_sessions(df)
    assert result["tradeable_session"].iloc[0] is np.bool_(True)


def test_tradeable_session_true_during_asian():
    """21:00 ET is asian → tradeable_session must be True."""
    df = _utc_df_from_et([21])
    result = SessionFilter().tag_sessions(df)
    assert result["tradeable_session"].iloc[0] is np.bool_(True)


def test_off_session():
    """17:00 and 18:00 ET → off session."""
    df = _utc_df_from_et([17, 18])
    result = SessionFilter().tag_sessions(df)
    assert (result["session"] == "off").all()
    assert (result["tradeable_session"] == False).all()
