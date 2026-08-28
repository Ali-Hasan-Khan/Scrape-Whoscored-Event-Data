# AGENTS.md

Python SDK (`whoscored/`, v2.0.0) for scraping football event data from Whoscored's chalkboard, plus a legacy notebook project (v1). SDK docs live in `docs/index.html`; README covers usage.

## Commands

- Install for dev: `pip install -e .` (deps in `pyproject.toml`; `selenium` is the `browser` extra, `mplsoccer` the `visuals` extra).
- Run the full test suite: `python test.py` → runs `pytest tests` (47 tests).
- `python test.py --live` adds ONE real match fetch (id `1650630`, Barcelona 0–0 Rayo). Never run live without explicit user approval — the user does not want Whoscored flagging their IP.
- No linter, formatter, typecheck, or CI is configured. `./.venv/bin/python` is the venv interpreter; `.venv/bin/pytest` works.

## Architecture

- `whoscored/`: the SDK. `client.py` = `WhoscoredClient` entrypoint; `parser.py` extracts the match-centre JSON blob; `dataframe.py` builds event/match frames; `epv.py` uses the bundled `data/EPV_grid.csv`; `transports.py` = HTTP + Selenium backends; `discovery.py` = league/fixture listing; `proxies.py` = rotating pool; `cli.py` backs the `whoscored` command (`python -m whoscored` equivalent). `data/leagues.json` is a bundled offline snapshot (430 leagues) — `list_leagues()` must not need network.
- `main.py`: v1 compatibility shim for the legacy notebook functions (`getMatchData`, `createEventsDF`, `translateDate`, etc.); all shims `warnings.warn(..., DeprecationWarning)`. Legacy project files (`utils.py`, `visuals.py`, `linecollection.py`, `EPV_grid.csv`, `data/events.csv`, `tutorial.ipynb`) are v1 — out of scope except for parity tests.
- `tests/`: offline suite. `conftest.py`'s `FixtureTransport` returns the canned gzipped HTML `tests/fixtures/match_1650630.html.gz` for any URL; no network is ever touched unless `--live`.

## Testing quirks

- Default suite is fully offline by design. `--live` fetches exactly one match via `WhoscoredClient()` and asserts 1465 event rows — keep that number meaningfully in sync if the fixture changes.
- Known data shapes (from the Whoscored feed): shot events are `SavedShot`/`MissedShots` — there is no `Shot` type; `isShot` flags shots. EPV is non-NaN only for `Pass` events with `outcomeType == Successful`. `match.events` has 258 columns; the matches dataframe has a non-unique (duplicated) index.

## Web-scraping operational gotchas

- Whoscored 403/challenges match pages **intermittently** — even the same URL can flip between 200 and 403. `WhoscoredClient` auto-retries through a real browser (`fallback_to_browser=True`); expect this, don't treat it as a bug.
- League/fixture listing pages are Cloudflare-protected → need `backend="browser"` (HTTP gets `BlockedError`).
- Whoscored ships generated (hashed) CSS class names, so `discovery.py` selectors are fragile and may need updating when Whoscored reshuffles their front-end. The match-centre data pipeline never touches those pages.
- Free proxy pools currently all fail on Whoscored (datacenter IPs get 403) — proxies are still exposed/validated against `gstatic.com` only; don't change the validation target to Whoscored.

## Browser quirks (Ubuntu/snap)

- `/usr/bin/firefox` is a shell wrapper, not a real binary — geckodriver fails with "binary is not a Firefox executable". `transports.py` auto-resolves the real snap ELF (`/snap/firefox/.../firefox`) or the `FIREFOX_BIN` env override; `binary_location=` also works.
- Selenium's chromedriver/geckodriver teardown spews `PermissionError` tracebacks ("Error terminating service process") and "might not be compatible" warnings — silenced via `_QuietFirefoxService`/log filters. Set `SE_DEBUG` or `WHOSCORED_DEBUG` to restore diagnostics.
- Do not use `executable_path=` kwarg with Selenium ≥ 4.10; use `service=`.

## Docs & versioning

- `docs/index.html` is the single-page SDK docs site, deployed statically via root `vercel.json` (`outputDirectory: "docs"`). Update docs alongside API changes.
- v2.0.0 is pinned in three places — keep them in sync: `pyproject.toml`, `whoscored/__init__.py` (`__version__`), and `docs/index.html` (<span class="ver"> badge + footer). The "v2.0.0 vs v1 notebook" framing is intentional; do not introduce tag/merge/semver planning notes into docs.