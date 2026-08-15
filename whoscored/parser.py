"""Parsing of Whoscored match-centre pages.

The match centre page embeds the full event feed inside a ``<script>`` tag as
an assignment to ``require.config.params["args"]``. The payload is a sequence
of comma-separated ``key: value`` pairs where the values are strict JSON
objects (the keys themselves are unquoted). ``matchCentreData`` is the big
one containing every event plus team/player metadata.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .exceptions import ParseError

# Matches the block that holds all match centre variables.
_ARGS_MARKER = 'require.config.params["args"]'
_DATA_MARKER = "matchCentreData:"
_EVENT_TYPES_MARKER = "matchCentreEventTypeJson:"
_MATCH_ID_RE = re.compile(r"matchId:\s*(\d+)")


def _decode_json_after(marker: str, text: str) -> dict[str, Any]:
    """Decode the first JSON object that follows ``marker`` in ``text``."""
    idx = text.find(marker)
    if idx < 0:
        raise ParseError(f"Could not locate '{marker}' in page source.")
    start = idx + len(marker)
    # JSONDecoder.raw_decode does not skip leading whitespace in all versions.
    while start < len(text) and text[start].isspace():
        start += 1
    if text[start : start + 1] != "{":
        raise ParseError(f"Expected a JSON object after '{marker}'.")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Failed to decode JSON after '{marker}': {exc}") from exc
    if not isinstance(obj, dict):
        raise ParseError(f"Expected a JSON object after '{marker}', got {type(obj).__name__}.")
    return obj


def find_args_script(html: str) -> str:
    """Return the ``require.config.params["args"]`` script content (if any)."""
    idx = html.find(_ARGS_MARKER)
    if idx < 0:
        raise ParseError("Match centre script not found in page source.")
    return html[idx:]


def extract_match_id(html: str) -> int:
    """Extract the numeric match id from the page source."""
    match = _MATCH_ID_RE.search(html)
    if match is None:
        raise ParseError("Could not locate matchId in page source.")
    return int(match.group(1))


def parse_match_data(html: str) -> dict[str, Any]:
    """Parse a match-centre page into a flat dictionary.

    The returned dict mirrors the structure the original project produced with
    Selenium: every key of ``matchCentreData`` plus ``matchId`` and
    ``matchCentreEventTypeJson`` at the top level, together with competition
    metadata (``region``, ``league``, ``season``, ``competitionType``,
    ``competitionStage``) where it can be derived from the breadcrumb.

    Parameters
    ----------
    html : str
        Raw HTML of a Whoscored ``/Matches/<id>/Live/...`` page.

    Returns
    -------
    dict
        Keys sorted alphabetically for stable diffs across runs.
    """
    args = find_args_script(html)
    match_data = _decode_json_after(_DATA_MARKER, args)
    match_data["matchId"] = extract_match_id(args)
    match_data["matchCentreEventTypeJson"] = _decode_json_after(_EVENT_TYPES_MARKER, args)

    match_data.update(_breadcrumb_metadata(html))
    return dict(sorted(match_data.items()))


def _breadcrumb_metadata(html: str) -> dict[str, str]:
    """Best-effort region/league/season/competition info from the breadcrumb."""
    metadata: dict[str, str] = {
        "region": "",
        "league": "",
        "season": "",
        "competitionType": "League",
        "competitionStage": "",
    }
    nav = _extract_breadcrumb_nav(html)
    if nav is None:
        return metadata

    link = _find_first_link_text(nav)
    if link:
        parts = [p.strip() for p in link.split("-")]
        if len(parts) >= 2:
            metadata["league"] = parts[0]
            metadata["season"] = parts[1]
        if len(parts) > 2:
            metadata["competitionType"] = "Knock Out"
            metadata["competitionStage"] = " - ".join(parts[2:])

    region = _extract_region(nav)
    if region:
        metadata["region"] = region

    return metadata


def _extract_breadcrumb_nav(html: str) -> str | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ParseError("BeautifulSoup is required for breadcrumb parsing.") from exc
    try:
        start = html.index('id="breadcrumb-nav"')
    except ValueError:
        return None
    end = html.find("</div>", start)
    if end < 0:
        return None
    return html[start:end]


def _find_first_link_text(fragment: str) -> str | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return None
    soup = BeautifulSoup(fragment, "lxml")
    a = soup.find("a")
    return a.get_text(strip=True) if a else None


def _extract_region(fragment: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return ""
    soup = BeautifulSoup(fragment, "lxml")
    span = soup.find("span", class_=re.compile(r"iconize"))
    if span:
        return span.get_text(strip=True)
    return ""
