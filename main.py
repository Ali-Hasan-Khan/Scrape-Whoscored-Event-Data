"""Backward-compatible shim for the original ``main.py``.

This module keeps the exact function names/signatures of the 2020 original so
existing notebooks and scripts keep working, but re-implements them on top of
the refactored SDK in :mod:`whoscored`. New projects should use
:class:`whoscored.WhoscoredClient` directly.
"""

from __future__ import annotations

import warnings
from datetime import datetime as dt
from typing import Any

import pandas as pd

from whoscored import (
    add_epv_to_dataframe,
    create_events_dataframe,
    create_matches_dataframe,
    get_epv_at_location,
    load_epv_grid,
    to_metric_coordinates_from_whoscored,
)
from whoscored.client import WhoscoredClient
from whoscored.parser import parse_match_data

warnings.warn(
    "main.py is a compatibility shim for the old notebook-based workflow. "
    "New code should use `from whoscored import WhoscoredClient`.",
    DeprecationWarning,
    stacklevel=2,
)

main_url = "https://www.whoscored.com/"

TRANSLATE_DICT = {
    "Jan": "Jan", "Feb": "Feb", "Mac": "Mar", "Apr": "Apr", "Mei": "May",
    "Jun": "Jun", "Jul": "Jul", "Ago": "Aug", "Sep": "Sep", "Okt": "Oct",
    "Nov": "Nov", "Des": "Dec", "Mar": "Mar", "May": "May", "Aug": "Aug",
    "Oct": "Oct", "Dec": "Dec",
}


def _client_for(backend: str = "http", driver: Any = None) -> WhoscoredClient:
    if backend == "browser" and driver is None:
        driver = _new_driver()
    return WhoscoredClient(backend=backend, driver=driver)


def _new_driver() -> Any:
    from selenium import webdriver

    return webdriver.Firefox()


def getLeagueUrls(minimize_window: bool = True) -> dict[str, str]:
    """Return every league as ``{slug: url}`` (bundled snapshot by default)."""
    with WhoscoredClient() as client:
        return client.list_leagues()


def getMatchUrls(comp_urls: dict[str, str], competition: str, season: str) -> list[dict[str, str]]:
    """Return the fixture list for a competition/season (needs a browser)."""
    league = _resolve_league_key(comp_urls, competition)
    with WhoscoredClient(backend="browser") as client:
        fixtures = client.list_fixtures(league, season)
    return [_fixture_to_old_dict(f) for f in fixtures]


def getTeamUrls(team: str, match_urls: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter fixture dicts to those involving ``team``."""
    from whoscored.models import Fixture

    fixtures = [_old_dict_to_fixture(f) for f in match_urls]
    with WhoscoredClient() as client:
        return [_fixture_to_old_dict(f) for f in client.team_fixtures(team, fixtures)]


def getMatchesData(match_urls: list[dict[str, str]], minimize_window: bool = True) -> list[dict[str, Any]]:
    """Scrape the given fixtures (7s politeness delay per match)."""
    urls = [u["url"] if u["url"].startswith("http") else main_url[:-1] + u["url"] for u in match_urls]
    with WhoscoredClient() as client:
        return [match.raw for match in client.get_matches(urls)]


def getMatchData(driver: Any, url: str, display: bool = True, close_window: bool = True) -> dict[str, Any]:
    """Fetch and parse a single match-centre page."""
    if driver is not None:
        driver.get(url)
        html = driver.page_source
        if close_window:
            try:
                driver.close()
            except Exception:
                pass
    else:
        with WhoscoredClient() as client:
            html = client.transport.get(url)
    payload = parse_match_data(html)
    if display:
        print("Region: {}, League: {}, Season: {}, Match Id: {}".format(
            payload.get("region"), payload.get("league"),
            payload.get("season"), payload.get("matchId")))
    return payload


def getFixtureData(driver: Any) -> list[dict[str, str]]:
    """Collect fixtures from the currently-loaded fixtures page."""
    from whoscored.discovery import _collect_fixture_rows

    return [_fixture_to_old_dict(f) for f in _collect_fixture_rows(driver)]


def createEventsDF(data: dict[str, Any]) -> pd.DataFrame:
    return create_events_dataframe(data)


def createMatchesDF(data: dict[str, Any] | list[dict[str, Any]]) -> pd.DataFrame:
    return create_matches_dataframe(data)


def translateDate(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise translated month names in fixture dates and drop postponed rows."""
    unwanted: list[int] = []
    for i, match in enumerate(data):
        if "?" in match["date"]:
            unwanted.append(i)
            continue
        parts = match["date"].split()
        month = parts[1] if len(parts) > 1 else ""
        if month in TRANSLATE_DICT:
            parts[1] = TRANSLATE_DICT[month]
            match["date"] = " ".join(parts)
        else:
            print(parts)
    for i in sorted(unwanted, reverse=True):
        del data[i]
    return data


def getSortedData(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(data, key=lambda item: dt.strptime(item["date"], "%A, %b %d %Y"))


def load_EPV_grid(fname: str = "EPV_grid.csv"):
    return load_epv_grid(fname)


def get_EPV_at_location(position, EPV, attack_direction, field_dimen=(106.0, 68.0)):
    return get_epv_at_location(position, EPV, attack_direction, field_dimen)


def to_metric_coordinates_from_whoscored(data, field_dimen=(106.0, 68.0)):
    return to_metric_coordinates_from_whoscored(data, field_dimen)


def addEpvToDataFrame(data: pd.DataFrame) -> pd.DataFrame:
    return add_epv_to_dataframe(data)


def _resolve_league_key(comp_urls: dict[str, str], competition: str) -> str:
    if competition in comp_urls:
        return competition
    slug = competition.lower().replace(" ", "-")
    if slug in comp_urls:
        return slug
    normalized = {k.lower(): k for k in comp_urls}
    if slug in normalized:
        return normalized[slug]
    raise KeyError(f"Competition '{competition}' not found in the league index.")


def _fixture_to_old_dict(fixture) -> dict[str, str]:
    return {"date": fixture.date, "home": fixture.home, "away": fixture.away,
            "score": fixture.score, "url": fixture.url}


def _old_dict_to_fixture(row: dict[str, str]):
    from whoscored.models import Fixture

    return Fixture(date=row["date"], home=row["home"], away=row["away"],
                   score=row.get("score", ""), url=row["url"])
