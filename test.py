"""Run the SDK test suite.

By default this runs the full offline suite (fixture data, no network). Pass
``--live`` to also run a single live smoke test against one Whoscored match
page — useful to confirm the current site still returns parseable data, at the
cost of one polite request.

Usage::

    python test.py            # offline suite only
    python test.py --live     # offline suite + one live match fetch
"""

from __future__ import annotations

import argparse
import sys


def run_live_smoke_test() -> None:
    from whoscored import WhoscoredClient

    print("Fetching a single match (one request, polite delay)...")
    with WhoscoredClient() as client:
        match = client.get_match(1650630)
    events = match.events
    print(f"Match {match.match_id}: {match.home.name} {match.score} {match.away.name}")
    print(f"Events: {len(events)} rows, {events.shape[1]} columns")
    assert match.match_id == 1650630
    assert len(events) == 1465


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="run the live smoke test")
    args = parser.parse_args()

    import pytest

    code = pytest.main(["-q", "tests"])
    if code != 0:
        return int(code)

    if args.live:
        try:
            run_live_smoke_test()
        except Exception as exc:  # noqa: BLE001 - report and exit nonzero
            print(f"Live smoke test failed: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
