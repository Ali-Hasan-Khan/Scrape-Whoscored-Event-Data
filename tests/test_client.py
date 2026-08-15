"""Tests for utility helpers and the client (all offline)."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from whoscored.client import WhoscoredClient
from whoscored.exceptions import BlockedError, TransportError
from whoscored.utils import (
    RateLimiter,
    load_dataframe,
    load_json,
    retry,
    save_dataframe,
    save_json,
)

from .conftest import FixtureTransport


def test_rate_limiter_enforces_minimum_delay():
    limiter = RateLimiter(delay=0.15, jitter=0.0)
    start = time.monotonic()
    limiter.wait()
    limiter.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.15


def test_retry_succeeds_eventually():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("not yet")
        return "ok"

    assert retry(flaky, retries=4, backoff=0.01, exceptions=(ValueError,)) == "ok"
    assert calls["n"] == 3


def test_retry_exhausts():
    def always_fails():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        retry(always_fails, retries=2, backoff=0.01, exceptions=(ValueError,))


def test_save_load_dataframe_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = str(tmp_path / "out.csv")
    save_dataframe(df, path)
    loaded = load_dataframe(path)
    pd.testing.assert_frame_equal(df, loaded)


def test_save_json_roundtrip(tmp_path):
    payload = {"matchId": 1650630, "events": [1, 2, 3]}
    path = str(tmp_path / "nested" / "match.json")
    save_json(payload, path)
    assert load_json(path) == payload


def test_client_get_match_uses_transport(match_html):
    client = WhoscoredClient()
    client.transport = FixtureTransport(match_html)  # no network
    match = client.get_match(1650630)
    assert match.match_id == 1650630
    assert match.home.name == "Barcelona"
    assert match.away.name == "Rayo Vallecano"
    assert len(match.events) == 1465
    client.close()


def test_client_get_match_with_url(match_html):
    client = WhoscoredClient()
    client.transport = FixtureTransport(match_html)
    url = "https://www.whoscored.com/Matches/1650630/Live/Spain-LaLiga-2022-2023-Barcelona-Rayo-Vallecano"
    match = client.get_match(url)
    assert match.match_id == 1650630
    client.close()


def test_client_get_match_caches(match_html, tmp_path):
    client = WhoscoredClient(cache_dir=str(tmp_path))
    client.transport = FixtureTransport(match_html)
    first = client.get_match(1650630)
    assert first.match_id == 1650630
    # second call served from cache: swap transport for a failing one
    class FailingTransport:
        def get(self, url):
            raise AssertionError("should not hit the network")

        def close(self):
            pass

    client.transport = FailingTransport()
    second = client.get_match(1650630)
    assert second.match_id == 1650630
    client.close()


def test_client_list_leagues_bundled_no_network():
    client = WhoscoredClient()
    leagues = client.list_leagues()
    assert len(leagues) > 300
    assert leagues["spain-laliga"].startswith("https://")
    assert leagues["england-premier-league"].startswith("https://")
    client.close()


def test_client_team_fixtures():
    from whoscored.models import Fixture

    fixtures = [
        Fixture("Sunday, Aug 13 2023", "Barcelona", "Rayo Vallecano", "0:0", "/matches/1650630/live/x"),
        Fixture("Sunday, Aug 20 2023", "Barcelona", "Cadiz", "2:0", "/matches/1650631/live/x"),
        Fixture("Sunday, Aug 20 2023", "Real Madrid", "Almeria", "3:1", "/matches/1650632/live/x"),
    ]
    client = WhoscoredClient()
    team = client.team_fixtures("Barcelona", fixtures)
    assert [f.match_id for f in team] == [1650630, 1650631]
    client.close()


def test_client_falls_back_to_browser_on_block(match_html, monkeypatch):
    from whoscored.exceptions import BlockedError

    class BlockingTransport:
        def get(self, url):
            raise BlockedError("HTTP 403 bot challenge")

        def close(self):
            pass

    class CapturingBrowser:
        def __init__(self, calls, html):
            self.calls = calls
            self.html = html

        def get(self, url):
            self.calls.append(url)
            return self.html

    client = WhoscoredClient()
    client.transport = BlockingTransport()
    seen = []
    monkeypatch.setattr(
        client, "_browser_fallback", lambda: CapturingBrowser(seen, match_html)
    )
    match = client.get_match(1650630)
    assert match.match_id == 1650630
    assert len(seen) == 1
    assert "1650630" in seen[0]
    client.close()


def test_client_does_not_fall_back_when_disabled(match_html, monkeypatch):
    from whoscored.exceptions import BlockedError

    class BlockingTransport:
        def get(self, url):
            raise BlockedError("HTTP 403 bot challenge")

        def close(self):
            pass

    client = WhoscoredClient(fallback_to_browser=False)
    client.transport = BlockingTransport()
    monkeypatch.setattr(
        client, "_browser_fallback", lambda: (_ for _ in ()).throw(AssertionError("should not spawn browser"))
    )
    with pytest.raises(BlockedError):
        client.get_match(1650630)
    client.close()


def test_client_http_transport_raises_blocked_on_403():
    import requests

    def fake_response(status_code: int) -> requests.Response:
        response = requests.Response()
        response.status_code = status_code
        response._content = b""
        return response

    from whoscored.transports import HttpTransport

    transport = HttpTransport(request_delay=0.0, jitter=0.0)
    transport.session.get = lambda url, timeout=None, **kwargs: fake_response(403)
    with pytest.raises(BlockedError):
        transport.get("https://www.whoscored.com/Regions/206/Tournaments/4")

    transport.session.get = lambda url, timeout=None, **kwargs: fake_response(500)
    with pytest.raises(TransportError):
        transport.get("https://www.whoscored.com/Matches/1")
    transport.close()
