"""Typed wrappers around the raw Whoscored payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Team:
    """A team taking part in a match."""

    team_id: int
    name: str
    venue: str = ""  # "h" or "a" within the match

    @classmethod
    def from_match_payload(cls, payload: dict[str, Any], venue: str) -> "Team":
        return cls(
            team_id=payload.get("teamId"),
            name=payload.get("name"),
            venue=venue,
        )


@dataclass(frozen=True)
class League:
    """A competition reachable on Whoscored."""

    slug: str
    url: str

    @property
    def name(self) -> str:
        return self.slug.split("-", 1)[-1].replace("-", " ").title()


@dataclass(frozen=True)
class Fixture:
    """A single fixture listed in a competition/season page."""

    date: str
    home: str
    away: str
    score: str
    url: str

    @property
    def match_id(self) -> int | None:
        try:
            return int(self.url.split("/")[2])
        except (IndexError, ValueError):
            return None


@dataclass
class Match:
    """A parsed match: raw payload plus convenient accessors.

    Attributes
    ----------
    raw : dict
        The full parsed match payload (see
        :func:`whoscored.parser.parse_match_data`).
    """

    raw: dict[str, Any]
    home: Team = field(init=False)
    away: Team = field(init=False)

    def __post_init__(self) -> None:
        home_payload = self.raw.get("home") or {}
        away_payload = self.raw.get("away") or {}
        object.__setattr__(self, "home", Team.from_match_payload(home_payload, "h"))
        object.__setattr__(self, "away", Team.from_match_payload(away_payload, "a"))

    @property
    def match_id(self) -> int | None:
        return self.raw.get("matchId")

    @property
    def date(self) -> str | None:
        return self.raw.get("startDate")

    @property
    def score(self) -> str | None:
        return self.raw.get("score")

    @property
    def venue(self) -> str | None:
        return self.raw.get("venueName")

    @property
    def league(self) -> str | None:
        return self.raw.get("league") or None

    @property
    def season(self) -> str | None:
        return self.raw.get("season") or None

    @property
    def events(self) -> pd.DataFrame:
        from .dataframe import create_events_dataframe

        return create_events_dataframe(self.raw)

    @property
    def matches_df(self) -> pd.DataFrame:
        from .dataframe import create_matches_dataframe

        return create_matches_dataframe(self.raw)

    def add_epv(self, **kwargs: Any) -> pd.DataFrame:
        """Return the events DataFrame with an EPV column appended."""
        from .epv import add_epv_to_dataframe

        return add_epv_to_dataframe(self.events, **kwargs)
