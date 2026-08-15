"""Conversion of parsed match data into tidy pandas DataFrames."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

_MATCH_META_COLUMNS = [
    "matchId",
    "startDate",
    "startTime",
    "score",
    "ftScore",
    "htScore",
    "etScore",
    "venueName",
    "maxMinute",
]

_EVENT_TYPES = ("shot", "goal", "pass", "foul", "card", "challenge", "dribble",
                "offside", "turnover", "dispossessed", "save", "clearance",
                "touches", "assist", "ballRecovery", "interception", "keeper",
                "penalty", "corner", "sub", "tackle", "throwIn", "aerial",
                "bigChance", "duel", "error", "tackle", "outfielder")


def create_events_dataframe(match_data: dict[str, Any]) -> pd.DataFrame:
    """Build the event-level DataFrame for a single match.

    Mirrors the output of the original ``createEventsDF``: one row per event,
    nested dictionaries (``period``, ``type``, ``outcomeType``, ``cardType``)
    flattened to their ``displayName``, ``playerName`` resolved from the player
    dictionary, a ``h_a`` home/away flag, derived ``shotBodyType``/``situation``
    columns, boolean one-hot columns for every event type, and the match-level
    metadata repeated on every row.

    Parameters
    ----------
    match_data : dict
        Dictionary produced by :func:`whoscored.parser.parse_match_data`.

    Returns
    -------
    pandas.DataFrame
    """
    events = match_data["events"]
    event_type_json = match_data.get("matchCentreEventTypeJson") or {}

    meta = {k: match_data.get(k) for k in _MATCH_META_COLUMNS if k in match_data}
    for event in events:
        event.update(meta)

    df = pd.DataFrame(events)

    for col in ("period", "type", "outcomeType"):
        if col in df.columns:
            df[col] = df[col].map(_display_name)

    if "cardType" in df.columns:
        df["cardType"] = df["cardType"].map(_display_name)
    else:
        df["cardType"] = False

    _resolve_satisfied_event_types(df, event_type_json)

    if "qualifiers" in df.columns:
        df["qualifiers"] = df["qualifiers"].map(_clean_qualifiers)

    # boolean shot / goal flags (older feeds omit the columns entirely)
    for col in ("isShot", "isGoal"):
        if col not in df.columns:
            df[col] = False
        else:
            df[col] = df[col].map(lambda v: bool(v) if not pd.isna(v) else False)

    # player name
    player_names = match_data.get("playerIdNameDictionary") or {}
    if "playerId" in df.columns:
        df.insert(
            loc=df.columns.get_loc("playerId") + 1,
            column="playerName",
            value=df["playerId"].map(lambda pid: player_names.get(_player_key(pid))),
        )

    # home / away
    if "teamId" in df.columns and "home" in match_data and "away" in match_data:
        team_map = {
            match_data["home"]["teamId"]: "h",
            match_data["away"]["teamId"]: "a",
        }
        df.insert(
            loc=df.columns.get_loc("teamId") + 1,
            column="h_a",
            value=df["teamId"].map(team_map),
        )

    df["shotBodyType"] = np.nan
    df["situation"] = np.nan
    if "qualifiers" in df.columns:
        _add_shot_derived_columns(df)

    df = _add_event_type_columns(df, event_type_json)

    return df


def create_matches_dataframe(data: dict[str, Any] | list[dict[str, Any]]) -> pd.DataFrame:
    """Build the match-level DataFrame.

    Accepts either a single match dict or a list of them. The ``home`` and
    ``away`` columns hold the full team dictionaries from the match data (the
    same shape the original ``createMatchesDF`` produced); use ``Match.home`` /
    ``Match.away`` for a structured view.

    Parameters
    ----------
    data : dict | list[dict]
        One match dict or an iterable of match dicts.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``matchId``.
    """
    columns = ["matchId", "attendance", "venueName", "startTime", "startDate",
               "score", "home", "away", "referee"]
    rows = data if isinstance(data, list) else [data]
    records = [{k: m.get(k) for k in columns if k in m} for m in rows]
    df = pd.DataFrame(records, columns=columns)
    if df.empty:
        return df.set_index("matchId")
    return df.set_index("matchId")


def _display_name(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("displayName", value)
    if value is None:
        return np.nan
    return value


def _player_key(player_id: Any) -> str | None:
    """Normalise a float/int player id to the string key used in the dict."""
    if player_id is None or (isinstance(player_id, float) and np.isnan(player_id)):
        return None
    return str(int(player_id))


def _clean_qualifiers(qualifiers: Any) -> Any:
    if not isinstance(qualifiers, list):
        return qualifiers
    for qualifier in qualifiers:
        if isinstance(qualifier, dict) and isinstance(qualifier.get("type"), dict):
            qualifier["type"] = qualifier["type"].get("displayName")
    return qualifiers


def _resolve_satisfied_event_types(df: pd.DataFrame, event_type_json: dict) -> None:
    if "satisfiedEventsTypes" not in df.columns:
        return
    reverse = {int(v): k for k, v in event_type_json.items()}

    def resolve(values: Any) -> Any:
        if not isinstance(values, list):
            return values
        resolved = []
        for value in values:
            try:
                resolved.append(reverse[int(value)])
            except (KeyError, TypeError, ValueError):
                resolved.append(value)
        return resolved

    df["satisfiedEventsTypes"] = df["satisfiedEventsTypes"].map(resolve)


def _add_shot_derived_columns(df: pd.DataFrame) -> None:
    shot_mask = df["isShot"].fillna(False)
    body_parts = {"RightFoot", "LeftFoot", "Head", "OtherBodyPart"}
    situations = {"FromCorner", "SetPiece", "DirectFreekick"}

    body_types = []
    situations_out = []
    for is_shot, qualifiers in zip(shot_mask, df["qualifiers"]):
        body, situation = np.nan, np.nan
        if is_shot and isinstance(qualifiers, list):
            for q in qualifiers:
                qtype = q.get("type") if isinstance(q, dict) else None
                if qtype in body_parts:
                    body = qtype
                elif qtype in situations:
                    situation = qtype
                elif qtype == "RegularPlay":
                    situation = "OpenPlay"
        body_types.append(body)
        situations_out.append(situation)
    df["shotBodyType"] = body_types
    df["situation"] = situations_out


def _add_event_type_columns(df: pd.DataFrame, event_type_json: dict) -> None:
    event_types = list(event_type_json.keys())
    if not event_types:
        return
    decoded = df["satisfiedEventsTypes"] if "satisfiedEventsTypes" in df.columns else pd.Series([[]] * len(df), index=df.index)
    columns = {
        event_type: decoded.map(lambda row: event_type in row if isinstance(row, list) else False)
        for event_type in event_types
    }
    if columns:
        df = pd.concat([df, pd.DataFrame(columns, index=df.index)], axis=1)
    return df
