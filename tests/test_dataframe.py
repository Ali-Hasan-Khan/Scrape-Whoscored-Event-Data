"""Tests for the event/match DataFrame builders."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

LEGACY_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "events.csv")


def test_events_dataframe_shape(events_df):
    assert isinstance(events_df, pd.DataFrame)
    assert events_df.shape[0] == 1465


def test_events_dataframe_metadata_repeated(events_df):
    assert (events_df["matchId"] == 1650630).all()
    assert (events_df["venueName"] == "Spotify Camp Nou").all()


def test_events_dataframe_flattened_columns(events_df):
    # nested dict columns are flattened to displayName strings
    assert events_df["period"].isin(["FirstHalf", "SecondHalf", "PreMatch", "PostGame"]).all()
    assert set(events_df["type"].unique()) > {"Start", "Pass"}
    assert {"SavedShot", "MissedShots"} <= set(events_df["type"].unique())
    assert events_df["outcomeType"].isin(["Successful", "Unsuccessful"]).all()


def test_events_dataframe_player_names(events_df):
    assert events_df["playerName"].notna().any()
    assert (events_df["playerId"].notna() == events_df["playerName"].notna()).all()


def test_events_dataframe_home_away(events_df):
    assert set(events_df["h_a"].dropna()) == {"h", "a"}


def test_events_dataframe_shot_columns(events_df):
    shots = events_df[events_df["isShot"]]
    assert len(shots) == 25
    assert events_df["shotBodyType"].isin(["RightFoot", "LeftFoot", "Head", "OtherBodyPart", np.nan]).all()
    assert shots["shotBodyType"].notna().all()


def test_events_dataframe_event_type_columns(events_df):
    # one boolean column per event type from the feed's dictionary
    for col in ("passAccurate", "shotOnTarget", "keyPassLong", "goalNormal"):
        assert col in events_df.columns
        assert events_df[col].dtype == bool


def test_events_dataframe_matches_legacy_csv(events_df):
    if not os.path.exists(LEGACY_CSV):
        pytest.skip("legacy events.csv not available")
    legacy = pd.read_csv(LEGACY_CSV, index_col=0)
    legacy = legacy[legacy["matchId"] == 1650630].copy()

    legacy["id"] = legacy["id"].astype("Int64")
    events = events_df.copy()
    events["id"] = events["id"].astype("Int64")

    o = legacy.set_index("id")
    n = events.set_index("id")
    assert set(o.index) == set(n.index)

    for col in ("x", "y", "endX", "endY", "minute", "teamId", "h_a", "type",
                "outcomeType", "period", "situation", "shotBodyType"):
        a = o.loc[n.index, col].astype("string").fillna("")
        b = n.loc[n.index, col].astype("string").fillna("")
        assert (a == b).all(), f"column '{col}' differs from the legacy scrape"


def test_matches_dataframe_single(match_data):
    from whoscored.dataframe import create_matches_dataframe

    df = create_matches_dataframe(match_data)
    assert list(df.columns) == ["attendance", "venueName", "startTime", "startDate",
                                "score", "home", "away", "referee"]
    assert df.index.tolist() == [1650630]
    assert df.loc[1650630, "home"]["name"] == "Barcelona"
    assert df.loc[1650630, "away"]["name"] == "Rayo Vallecano"


def test_matches_dataframe_list(match_data):
    from whoscored.dataframe import create_matches_dataframe

    df = create_matches_dataframe([match_data, match_data])
    assert len(df) == 2
    assert df.index.tolist() == [1650630, 1650630]
