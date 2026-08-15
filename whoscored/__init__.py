"""Whoscored event-data SDK.

A polite, typed client for scraping football match event data from
Whoscored's chalkboard. The match-centre pages (which hold every event) are
fetched over plain HTTP with built-in rate limiting and caching; league and
fixture listings are Cloudflare-protected and use a Selenium browser instead.

Quick start::

    from whoscored import WhoscoredClient

    with WhoscoredClient() as client:
        match = client.get_match(1650630)
        events = match.events              # pandas.DataFrame
        events = match.add_epv()           # adds an EPV column
        events.to_csv("events.csv", index=False)
"""

from __future__ import annotations

from .client import WhoscoredClient
from .dataframe import create_events_dataframe, create_matches_dataframe
from .epv import (
    add_epv_to_dataframe,
    get_epv_at_location,
    load_epv_grid,
    to_metric_coordinates_from_whoscored,
)
from .exceptions import (
    BackendError,
    BlockedError,
    MatchNotFoundError,
    ParseError,
    ProxyError,
    SeasonNotFoundError,
    TransportError,
    WhoscoredError,
)
from .models import Fixture, League, Match, Team
from .proxies import ProxyRotator, FREE_PROXY_SOURCES, normalize_proxy
from .utils import RateLimiter, load_dataframe, load_json, retry, save_dataframe, save_json

__version__ = "2.0.0"

__all__ = [
    "WhoscoredClient",
    "Match",
    "Fixture",
    "League",
    "Team",
    "create_events_dataframe",
    "create_matches_dataframe",
    "add_epv_to_dataframe",
    "get_epv_at_location",
    "load_epv_grid",
    "to_metric_coordinates_from_whoscored",
    "RateLimiter",
    "retry",
    "save_dataframe",
    "load_dataframe",
    "save_json",
    "load_json",
    "ProxyRotator",
    "FREE_PROXY_SOURCES",
    "normalize_proxy",
    "WhoscoredError",
    "TransportError",
    "BlockedError",
    "MatchNotFoundError",
    "SeasonNotFoundError",
    "ParseError",
    "BackendError",
    "ProxyError",
    "__version__",
]
