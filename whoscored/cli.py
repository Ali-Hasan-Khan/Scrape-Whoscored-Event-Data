"""Command-line interface: ``whoscored ...``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .client import WhoscoredClient
from .exceptions import WhoscoredError
from .utils import save_dataframe, save_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whoscored",
        description="Scrape football event data from Whoscored.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--delay", type=float, default=7.0, help="seconds between requests (default 7)"
    )
    parser.add_argument(
        "--jitter", type=float, default=2.0, help="random extra delay (default 2)"
    )
    parser.add_argument(
        "--cache", default=None, help="directory used to cache raw match payloads"
    )
    parser.add_argument(
        "--proxy", default=None, help="single host:port or http://host:port proxy"
    )
    parser.add_argument(
        "--free-proxies", action="store_true",
        help="rotate through validated free HTTP proxies from public lists",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_leagues = sub.add_parser("leagues", help="list leagues as {slug: url}")
    p_leagues.add_argument("--refresh", action="store_true", help="scrape the live site (needs browser)")
    p_leagues.add_argument("--browser", action="store_true", help="use the browser backend")
    p_leagues.add_argument("--out", default=None, help="write JSON to this file")

    p_fixtures = sub.add_parser("fixtures", help="list fixtures for a competition/season")
    p_fixtures.add_argument("league", help="league slug, e.g. spain-laliga")
    p_fixtures.add_argument("season", help="season label, e.g. 2023/2024")
    p_fixtures.add_argument("--out", default=None, help="write JSON to this file")

    p_team = sub.add_parser("team", help="filter a fixtures file to one team")
    p_team.add_argument("team", help="team name, e.g. Liverpool")
    p_team.add_argument("--fixtures", required=True, help="JSON file of fixtures")
    p_team.add_argument("--out", default=None, help="write JSON to this file")

    p_match = sub.add_parser("match", help="fetch a single match")
    p_match.add_argument("id", help="numeric match id or match URL")
    p_match.add_argument("--out", default=None, help="write events CSV / match JSON to this directory")
    p_match.add_argument("--epv", action="store_true", help="append the EPV column")

    p_scrape = sub.add_parser("scrape", help="fetch many matches from a fixtures file")
    p_scrape.add_argument("--fixtures", required=True, help="JSON file of fixtures")
    p_scrape.add_argument("--out", default=None, help="output directory (default: ./scraped)")
    p_scrape.add_argument("--max", type=int, default=None, help="only scrape the first N matches")
    p_scrape.add_argument("--no-progress", action="store_true", help="disable the progress bar")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with WhoscoredClient(
            backend="browser" if getattr(args, "browser", False) else "http",
            request_delay=args.delay,
            jitter=args.jitter,
            cache_dir=args.cache,
            proxy=args.proxy,
            free_proxies=args.free_proxies,
        ) as client:
            if args.command == "leagues":
                leagues = client.list_leagues(refresh=args.refresh)
                _print_and_maybe_save(leagues, args.out)
            elif args.command == "fixtures":
                fixtures = client.list_fixtures(args.league, args.season)
                payload = [fixture.__dict__ for fixture in fixtures]
                _print_and_maybe_save(payload, args.out)
            elif args.command == "team":
                with open(args.fixtures, encoding="utf-8") as handle:
                    raw = json.load(handle)
                fixtures = [_dict_to_fixture(row) for row in raw]
                team_fixtures = client.team_fixtures(args.team, fixtures)
                _print_and_maybe_save([f.__dict__ for f in team_fixtures], args.out)
            elif args.command == "match":
                match = client.get_match(args.id)
                print(f"Match {match.match_id}: {match.home.name} {match.score} {match.away.name} "
                      f"({match.league or '?'} {match.season or '?'})")
                events = match.add_epv() if args.epv else match.events
                if args.out:
                    save_dataframe(events, f"{args.out}/events_{match.match_id}.csv")
                    save_json(match.raw, f"{args.out}/match_{match.match_id}.json")
                    print(f"Saved to {args.out}/")
            elif args.command == "scrape":
                with open(args.fixtures, encoding="utf-8") as handle:
                    raw = json.load(handle)
                urls = [_dict_to_fixture(row).url for row in raw]
                if args.max:
                    urls = urls[: args.max]
                out_dir = args.out or "scraped"
                all_events = []
                for match in client.get_matches(urls, progress=not args.no_progress):
                    events = match.events
                    all_events.append(events)
                    save_dataframe(events, f"{out_dir}/events_{match.match_id}.csv")
                    save_json(match.raw, f"{out_dir}/match_{match.match_id}.json")
                    print(f"  {match.match_id}: {match.home.name} {match.score} {match.away.name}")
                if all_events:
                    import pandas as pd

                    combined = pd.concat(all_events, ignore_index=True)
                    save_dataframe(combined, f"{out_dir}/events_all.csv")
                    print(f"Combined events written to {out_dir}/events_all.csv "
                          f"({combined.shape[0]} rows, {combined.shape[1]} columns)")
        return 0
    except WhoscoredError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dict_to_fixture(row: dict[str, Any]):
    from .models import Fixture

    return Fixture(
        date=row["date"],
        home=row["home"],
        away=row["away"],
        score=row.get("score", ""),
        url=row["url"],
    )


def _print_and_maybe_save(payload: Any, out: str | None) -> None:
    if out:
        save_json(payload, out)
        print(f"Saved to {out}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
