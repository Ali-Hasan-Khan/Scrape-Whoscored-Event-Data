# Scraping Whoscored Event Data
![alt text](https://github.com/Ali-Hasan-Khan/Scrape-Whoscored-Event-Data/blob/main/logo.jpg "Whoscored")

📖 **Documentation (HTML, Vercel-ready): [`docs/index.html`](docs/index.html)** —
a self-contained docs site covering the full SDK API, CLI, examples and
troubleshooting. Deploy it with `vercel` from the repo root (see
[`vercel.json`](vercel.json)).

## Versioning

This project is **v2.0.0** — a complete rewrite of the original
Selenium + notebook project, which was **v1.0.0**. The version is mirrored in
`whoscored.__version__`, `pyproject.toml`, `whoscored --version`, and the docs
site.

A **professional Python SDK** for scraping match event data from
[Whoscored](http://whoscored.com/ "Whoscored")'s chalkboard.

This is a full rewrite of the original Selenium-and-notebook project:

- **Typed, documented API** — no more copy-pasting notebook cells.
- **Fast & polite** — match-centre pages are fetched over plain HTTP with
  built-in rate limiting (default 7s + random jitter) and caching, instead of
  driving a full browser per match.
- **Auto browser fallback** — Whoscored intermittently challenges even match
  pages with a bot wall. When the HTTP backend hits one (HTTP 403), the client
  transparently re-fetches the page through a real browser and carries on.
- **No browser needed for the actual data** — only the league/fixture *listing*
  pages sit behind Cloudflare and require a browser (see below).
- **Robust parsing** — the event feed is decoded as real JSON instead of
  brittle string-splitting, and it has been verified against a captured live
  page.
- **Backwards compatible** — the old `main.py` function names still exist as
  shims, so old notebooks keep working.

---

## Installation

```bash
pip install -r requirements.txt        # or: pip install -e .
```

Core dependencies: `pandas`, `numpy`, `requests`, `beautifulsoup4`, `lxml`,
`tqdm`. `selenium` is only needed for the Cloudflare-protected listing pages.

## Quick start

```python
from whoscored import WhoscoredClient

with WhoscoredClient() as client:                # polite by default
    match = client.get_match(1650630)            # id or full match URL

print(f"{match.home.name} {match.score} {match.away.name}")
# -> Barcelona 0:0 Rayo Vallecano

events = match.events                            # pandas.DataFrame, one row per event
events_with_epv = match.add_epv()                # append the EPV column
match.matches_df                                 # match-level summary

events.to_csv("events.csv", index=False)
```

### Fetching several matches

```python
urls = [
    "https://www.whoscored.com/Matches/1650630/Live/Spain-LaLiga-2022-2023-Barcelona-Rayo-Vallecano",
    "https://www.whoscored.com/Matches/1650634/Live/Spain-LaLiga-2022-2023-Osasuna-Sevilla",
]
with WhoscoredClient() as client:
    matches = client.get_matches(urls)           # progress bar + delays included
```

### Discovering leagues and fixtures

League and fixture listing pages are Cloudflare-protected and therefore need a
real browser (Selenium). A snapshot of every league is bundled with the
package, so listing leagues works with no network at all:

```python
client.list_leagues()               # -> {"spain-laliga": "https://www.whoscored.com/...", ...}
```

To re-scrape the live list or list a season's fixtures:

```python
with WhoscoredClient(backend="browser") as client:     # Firefox, headed
    fixtures = client.list_fixtures("spain-laliga", "2023/2024")
    lfc = client.team_fixtures("Real Madrid", fixtures)
```

> Note: Whoscored ships generated CSS class names, so the discovery selectors
> may occasionally need updating when Whoscored changes its front-end. The
> match-centre pipeline (the part that actually gives you data) is unaffected
> because it never touches those pages.

### Browser troubleshooting

- **Ubuntu/Debian snap Firefox:** `/usr/bin/firefox` is a *shell wrapper*, not
  a real binary, so geckodriver fails with `binary is not a Firefox
  executable`. The SDK auto-detects the real binary at
  `/snap/firefox/current/usr/lib/firefox/firefox` (override via
  `WhoscoredClient(binary_location="...")` or the `FIREFOX_BIN` env var).
- Driver shutdown noise is handled automatically: the benign
  `Error terminating service process`/`PermissionError` tracebacks from
  snap-packaged geckodriver and Selenium Manager's cosmetic
  `geckodriver ... might not be compatible` warning are both silenced. Set
  `SE_DEBUG=1` (or `WHOSCORED_DEBUG=1`) to bring back the diagnostics.

## Command line

```bash
whoscored --version
whoscored leagues --out leagues.json
whoscored match 1650630 --out data/ --epv
whoscored fixtures spain-laliga 2023/2024 --out fixtures.json     # browser
whoscored team "Real Madrid" --fixtures fixtures.json
whoscored scrape --fixtures fixtures.json --out scraped/ --delay 8
```

## Politeness & avoiding bans

This SDK is designed to keep your IP safe:

- **Rate limiting** — by default at least 7 seconds (plus random jitter)
  between requests. Tune with `request_delay=`/`jitter=` or the `--delay` CLI
  flag.
- **Caching** — pass `cache_dir=".whoscored_cache"` to cache raw payloads so
  re-runs never touch the site.
- **One request per match** — match-centre pages embed the entire event feed
  in a single page; no multi-page crawl per match.
- **Realistic headers** — a browser user-agent and referer are sent by default.
- **Auto fallback** — if a match page does return a challenge anyway, the
  client retries it through a real (headed) browser instead of hammering the
  HTTP endpoint.
- **Headless browsers are avoided** for Cloudflare pages (headed Firefox is
  far less likely to be flagged).

> Note: Whoscored's bot protection is intermittent and can be triggered after a
> burst of requests. The SDK surfaces these as `BlockedError` (subclass of
> `WhoscoredError`) with a clear message. Stop scraping for a while if you keep
> seeing them — continuing will only prolong the block.

Please also respect Whoscored's terms of service and robots policy, keep delays
generous, and never hammer the site.

## Proxies

To spread requests over multiple IPs, the HTTP backend supports a single
static proxy or a rotating pool:

```python
from whoscored import WhoscoredClient, ProxyRotator

# One static proxy
with WhoscoredClient(proxy="host:port") as client:      # or http://host:port
    client.get_match(1650630)

# Rotate through a pool (host:port list, validated against a neutral endpoint)
pool = ProxyRotator(proxies=["p1:8080", "p2:3128"], validate=True)
with WhoscoredClient(proxy_pool=pool) as client:
    client.get_matches([1650630, 1650634, 1650690])

# Or pull free HTTP proxies from public lists (validated in parallel)
with WhoscoredClient(free_proxies=True) as client:
    client.get_matches(urls)
```

CLI equivalents: `--proxy host:port` and `--free-proxies`.

When a pool is configured, a blocked or dead proxy is skipped automatically —
the transport rotates to the next one and only reports failure once *every*
proxy has been tried. Proxies are validated against `gstatic.com` (never
against Whoscored), and the politeness delay still applies per request.

> **Honest warning:** free proxy lists are dominated by datacenter IPs that
> Whoscored's bot protection blocks outright — in testing, all of them returned
> HTTP 403 challenges. A pool is most useful with **residential** proxy
> services (paid) or your own proxy servers, which can pass the challenge.
> Free proxies also don't make you anonymous: treat them as untrusted middlemen.

## Testing

The test suite runs entirely offline against a real captured match page, so it
never risks getting your IP flagged:

```bash
python test.py            # offline
python test.py --live     # also fetches one real match (single polite request)
```

## Project layout

```
whoscored/            the SDK package
  client.py           WhoscoredClient (main entry point)
  parser.py           match-centre JSON extraction
  dataframe.py        event/match DataFrame builders
  epv.py              Expected Possession Value helpers
  transports.py       HTTP + Selenium browser backends
  discovery.py        league/fixture listing (browser-based)
  cache.py            on-disk payload cache
  utils.py            RateLimiter, retry, save/load helpers
  cli.py              the `whoscored` command
main.py               compatibility shim for the old notebook API
tests/                offline test suite + fixture
examples/quickstart.py
```

## Helper functions

- `save_dataframe(df, path)` / `load_dataframe(path)` — CSV / Parquet round
  trip with parent-directory creation.
- `save_json(data, path)` / `load_json(path)`
- `RateLimiter(delay, jitter)` — enforce a minimum gap between requests.
- `retry(func, retries=3, backoff=1.5)` — exponential-backoff wrapper.
- `create_events_dataframe(data)` / `create_matches_dataframe(data)`
- `load_epv_grid()`, `get_epv_at_location(...)`,
  `to_metric_coordinates_from_whoscored(...)`, `add_epv_to_dataframe(...)`

## Credits

- Original project by [Ali Hasan Khan](https://twitter.com/rockingAli5).
- Expected Possession Value model by
  [Laurie Shaw](https://twitter.com/EightyFivePoint) —
  [check out his work](http://eightyfivepoints.blogspot.com/).
- `mplsoccer` visuals by [Andy](https://twitter.com/numberstorm) and
  [Anmol](https://twitter.com/slothfulwave612).
