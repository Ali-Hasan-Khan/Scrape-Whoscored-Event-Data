"""Exception hierarchy for the Whoscored event-data SDK."""

from __future__ import annotations


class WhoscoredError(Exception):
    """Base class for all errors raised by this SDK."""


class TransportError(WhoscoredError):
    """Raised when a network request or browser navigation fails."""


class BlockedError(TransportError):
    """Raised when the site returns an anti-bot / Cloudflare challenge.

    Whoscored protects several pages (homepage, tournament fixtures) behind a
    Cloudflare "Just a moment..." challenge. Plain HTTP requests will usually
    receive an HTTP 403. Use a real (non-headless) browser backend for those
    pages.
    """


class MatchNotFoundError(WhoscoredError):
    """Raised when a match centre page cannot be found for the given id/url."""


class SeasonNotFoundError(WhoscoredError):
    """Raised when the requested competition/season has no fixtures."""


class ParseError(WhoscoredError):
    """Raised when the match centre JSON cannot be located or decoded."""


class BackendError(WhoscoredError):
    """Raised when a requested backend is not available or misconfigured."""


class ProxyError(WhoscoredError):
    """Raised when a proxy pool is exhausted or a proxy fails fatally."""
