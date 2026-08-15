"""High-level client for the Whoscored event-data SDK.

Typical usage::

    from whoscored import WhoscoredClient

    with WhoscoredClient() as client:
        match = client.get_match(1650630)     # by id or full URL
        events = match.events                   # pandas DataFrame
        events_with_epv = match.add_epv()
        events.to_csv("events.csv", index=False)

League and fixture listings are Cloudflare-protected and need a browser; the
match-centre data itself is fetched over plain HTTP with polite rate limiting.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable

from . import discovery
from .cache import DiskCache
from .exceptions import BlockedError, MatchNotFoundError
from .models import Fixture, League, Match
from .parser import parse_match_data
from .transports import BrowserTransport, HttpTransport, Transport
from .utils import RateLimiter

log = logging.getLogger(__name__)

_BUNDLED_LEAGUES = os.path.join(os.path.dirname(__file__), "data", "leagues.json")
_MATCH_URL_TEMPLATE = "https://www.whoscored.com/Matches/{match_id}/Live"


class WhoscoredClient:
    """A polite, reusable client for Whoscored event data.

    Parameters
    ----------
    backend : str, default "http"
        ``"http"`` for plain requests (fast, works for match-centre pages) or
        ``"browser"`` for a Selenium-driven browser (required for league and
        fixture listings behind Cloudflare).
    driver : optional
        An existing Selenium WebDriver to reuse (browser backend only).
    headless : bool, default False
        Run the browser headless. Not recommended: headless browsers are
        easily flagged.
    browser : str, default "firefox"
        ``"firefox"`` or ``"chrome"`` for the browser backend.
    binary_location : str, optional
        Path to the browser executable (Firefox). Auto-detected by default,
        which works around distro wrapper scripts like the Ubuntu snap
        launcher. Can also be set via the ``FIREFOX_BIN`` environment variable.
    request_delay : float, default 7.0
        Seconds between HTTP requests (keeps scraping polite).
    jitter : float, default 2.0
        Randomised extra delay on top of ``request_delay``.
    timeout : float, default 30
        HTTP timeout per request.
    retries : int, default 3
        Retries per page on transient failures.
    cache_dir : str, optional
        Directory used to cache raw match payloads. ``None`` (default) keeps
        everything in memory only.
    user_agent : str, optional
        Override the HTTP user agent.
    session : optional
        Reuse an existing ``requests.Session``.
    fallback_to_browser : bool, default True
        If the HTTP backend hits a bot challenge (HTTP 403), silently re-fetch
        the page through a real browser instead of failing. Only relevant for
        the ``"http"`` backend; the browser is spawned lazily and never used
        while HTTP requests succeed.
    proxy : str, optional
        A single ``host:port`` or ``http://host:port`` proxy for all requests.
    free_proxies : bool, default False
        Pull free HTTP proxies from public lists and rotate through them
        (see :class:`whoscored.proxies.ProxyRotator`). Proxies are validated
        before use. Ignored if ``proxy_pool`` is given.
    proxy_pool : ProxyRotator, optional
        A custom rotating proxy pool, taking precedence over ``proxy`` and
        ``free_proxies``.
    """

    def __init__(
        self,
        backend: str = "http",
        driver: Any = None,
        headless: bool = False,
        browser: str = "firefox",
        binary_location: str | None = None,
        request_delay: float = 7.0,
        jitter: float = 2.0,
        timeout: float = 30.0,
        retries: int = 3,
        cache_dir: str | None = None,
        user_agent: str | None = None,
        session: Any = None,
        fallback_to_browser: bool = True,
        proxy: str | None = None,
        free_proxies: bool = False,
        proxy_pool: Any = None,
    ) -> None:
        if backend not in {"http", "browser"}:
            raise ValueError("backend must be 'http' or 'browser'")
        self.backend = backend
        self.headless = headless
        self.browser = browser
        self.binary_location = binary_location
        self.fallback_to_browser = fallback_to_browser
        self.limiter = RateLimiter(request_delay, jitter)
        self._fallback_transport: BrowserTransport | None = None
        if backend == "http":
            self.transport: Transport = HttpTransport(
                request_delay=0.0,  # client.limiter governs pacing
                jitter=0.0,
                timeout=timeout,
                retries=retries,
                user_agent=user_agent,
                session=session,
                proxy=proxy,
                proxy_pool=proxy_pool or self._default_pool(free_proxies),
            )
        else:
            self.transport = BrowserTransport(
                driver=driver,
                headless=headless,
                browser=browser,
                binary_location=binary_location,
            )
        self.cache = DiskCache(cache_dir)

    @staticmethod
    def _default_pool(free_proxies: bool) -> Any:
        if not free_proxies:
            return None
        from .proxies import ProxyRotator

        return ProxyRotator(fetch_sources=True)

    # ------------------------------------------------------------------
    # Context manager & teardown
    # ------------------------------------------------------------------

    def __enter__(self) -> "WhoscoredClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        """Release any held resources (browser, session)."""
        self.transport.close()
        if self._fallback_transport is not None:
            self._fallback_transport.close()
            self._fallback_transport = None

    # ------------------------------------------------------------------
    # Match-centre data (plain HTTP, low risk)
    # ------------------------------------------------------------------

    def get_match(self, match_id_or_url: int | str) -> Match:
        """Fetch and parse a single match.

        Parameters
        ----------
        match_id_or_url : int | str
            A numeric match id (e.g. ``1650630``) or a full match-centre URL
            such as ``https://www.whoscored.com/Matches/1650630/Live/...``.

        Returns
        -------
        Match
        """
        url = self._match_url(match_id_or_url)
        match_id = self._match_id(match_id_or_url)
        if match_id is not None:
            cached = self.cache.get(match_id)
            if cached is not None:
                return Match(cached)
        html = self._fetch_html(url)
        payload = parse_match_data(html)
        if match_id is not None:
            self.cache.put(match_id, payload)
        return Match(payload)

    def _fetch_html(self, url: str) -> str:
        """Fetch a page, transparently falling back to a real browser on 403."""
        try:
            self.limiter.wait()
            return self.transport.get(url)
        except BlockedError:
            if self.backend != "http" or not self.fallback_to_browser:
                raise
        log.warning(
            "HTTP backend was blocked by a bot challenge; falling back to a "
            "real browser for %s",
            url,
        )
        return self._browser_fallback().get(url)

    def _browser_fallback(self) -> BrowserTransport:
        if self._fallback_transport is None:
            self._fallback_transport = BrowserTransport(
                headless=self.headless,
                browser=self.browser,
                binary_location=self.binary_location,
            )
        return self._fallback_transport

    def get_matches(
        self,
        match_ids_or_urls: Iterable[int | str],
        progress: bool = True,
    ) -> list[Match]:
        """Fetch several matches, preserving order.

        Parameters
        ----------
        match_ids_or_urls : iterable of int | str
            Match ids or URLs.
        progress : bool, default True
            Show a ``tqdm`` progress bar when available.

        Returns
        -------
        list[Match]
        """
        items = list(match_ids_or_urls)
        results: list[Match] = []
        iterator: Iterable = items
        if progress:
            try:
                from tqdm.auto import tqdm

                iterator = tqdm(items, desc="Fetching matches")
            except ImportError:
                pass
        for item in iterator:
            results.append(self.get_match(item))
        return results

    # ------------------------------------------------------------------
    # Discovery (Cloudflare-protected; requires the browser backend)
    # ------------------------------------------------------------------

    def list_leagues(self, refresh: bool = False) -> dict[str, str]:
        """Return every league as ``{slug: url}``.

        By default a bundled snapshot is returned (no network traffic). Pass
        ``refresh=True`` to re-scrape the live tournament browser, which
        requires the ``"browser"`` backend.

        Parameters
        ----------
        refresh : bool, default False
            When True, scrape the live site instead of using the snapshot.

        Returns
        -------
        dict[str, str]
        """
        if not refresh:
            return discovery.load_league_index(_BUNDLED_LEAGUES)
        if not isinstance(self.transport, BrowserTransport):
            raise RuntimeError(
                "Live league discovery requires backend='browser' (Cloudflare-protected page)."
            )
        return discovery.list_leagues(self.transport.driver)

    def list_fixtures(self, league: str, season: str) -> list[Fixture]:
        """List fixtures for a competition and season.

        Requires the ``"browser"`` backend because tournament pages are behind
        a Cloudflare challenge. ``league`` should be a slug from
        :meth:`list_leagues` (e.g. ``"england-premier-league"``).

        Parameters
        ----------
        league : str
            League slug, e.g. ``"spain-laliga"``.
        season : str
            Season label, e.g. ``"2023/2024"``.

        Returns
        -------
        list[Fixture]
        """
        if not isinstance(self.transport, BrowserTransport):
            raise RuntimeError(
                "Fixture discovery requires backend='browser' (Cloudflare-protected page)."
            )
        leagues = self.list_leagues()
        try:
            competition_url = leagues[league]
        except KeyError:
            available = ", ".join(sorted(leagues)[:10]) + ", ..."
            raise KeyError(f"Unknown league '{league}'. Examples: {available}") from None
        return discovery.list_fixtures(self.transport.driver, competition_url, season)

    def team_fixtures(self, team: str, fixtures: Iterable[Fixture]) -> list[Fixture]:
        """Filter fixtures to those involving ``team``.

        Parameters
        ----------
        team : str
            Team name as it appears on Whoscored (e.g. ``"Liverpool"``).
        fixtures : iterable of Fixture
            The full season's fixture list.

        Returns
        -------
        list[Fixture]
            The team's fixtures, de-duplicated and in order.
        """
        seen: set[int] = set()
        result: list[Fixture] = []
        for fixture in fixtures:
            if fixture.home == team or fixture.away == team:
                mid = fixture.match_id
                if mid is not None and mid in seen:
                    continue
                if mid is not None:
                    seen.add(mid)
                result.append(fixture)
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _match_url(self, match_id_or_url: int | str) -> str:
        value = str(match_id_or_url)
        if value.isdigit():
            return _MATCH_URL_TEMPLATE.format(match_id=value)
        if "whoscored.com" not in value:
            raise ValueError(
                f"Expected a numeric match id or a whoscored.com URL, got '{value}'"
            )
        return value

    @staticmethod
    def _match_id(match_id_or_url: int | str) -> int | None:
        value = str(match_id_or_url)
        if value.isdigit():
            return int(value)
        match = match_id_or_url
        try:
            path = match.split("whoscored.com", 1)[1]
            return int(path.split("/")[2])
        except (IndexError, ValueError):
            return None
