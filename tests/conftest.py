"""Offline test suite for the Whoscored SDK.

No network requests are made: every test runs against the bundled fixture
``tests/fixtures/match_1650630.html.gz`` (a real match-centre page captured
from Whoscored). Live scraping is deliberately left out so we never risk
getting the site to flag anyone's IP.
"""

from __future__ import annotations

import gzip
import os

import pytest

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "match_1650630.html.gz")


@pytest.fixture(scope="session")
def match_html() -> str:
    with gzip.open(FIXTURE_PATH, "rt", encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture(scope="session")
def match_data(match_html: str):
    from whoscored.parser import parse_match_data

    return parse_match_data(match_html)


@pytest.fixture(scope="session")
def events_df(match_data):
    from whoscored.dataframe import create_events_dataframe

    return create_events_dataframe(match_data)


class FixtureTransport:
    """Returns the canned fixture HTML for any URL (no network)."""

    def __init__(self, html: str) -> None:
        self.html = html

    def get(self, url: str) -> str:
        return self.html

    def close(self) -> None:
        pass
