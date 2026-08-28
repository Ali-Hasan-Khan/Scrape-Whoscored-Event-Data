# Contributing

Thanks for considering a contribution to **whoscored-event-data**. This guide
covers the setup and the conventions that keep the project healthy — and keeps
contributors' IPs off Whoscored's block list. MIT licensed; by contributing you
agree your changes ship under the same license.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .          # SDK + core deps (pandas, requests, ...)
pip install -e ".[dev]"   # adds pytest (and pyarrow for Parquet I/O)
pip install -e ".[browser]"   # adds selenium (only needed for fixture listings)
```

## Running tests

The entire suite runs **offline** against a captured match page
(`tests/fixtures/match_1650630.html.gz`) — no network, no ban risk:

```bash
python test.py            # 47 tests, offline only
```

`python test.py --live` performs **one** real match fetch (id `1650630`) and
asserts exactly 1465 event rows. Do **not** run it casually: Whoscored
intermittently challenges matching IPs and the catches can linger. Only run it
when you genuinely need to validate against the current live site, and keep it
to a single fetch.

There is no linter, formatter, or typechecker wired up — the test suite is the
gate. Make sure `python test.py` passes before submitting.

## Conventions

- **Offline-first.** New tests must not touch the network. Reuse the
  `FixtureTransport` in `tests/conftest.py` (returns the canned fixture HTML
  for any URL) instead of hitting the site.
- **Keep the fixture meaningful.** The live smoke test asserts 1465 rows; if
  the fixture ever changes, keep that assertion truthful. Commit any new
  fixture inside `tests/fixtures/`.
- **Version pinning in three places.** v2.0.0 lives in `pyproject.toml`,
  `whoscored/__init__.py` (`__version__`), and the `docs/index.html` badge +
  footer. Bump all three together when the version changes.
- **Public API is exported.** New public symbols should be added to
  `whoscored/__init__.py` (`__all__`), documented in `docs/index.html`, and
  mentioned in the CLI help if applicable.
- **Docs ship with code.** `docs/index.html` is the single-page documentation
  site (deployed statically via `vercel.json`). Update it in the same change
  that touches the API.
- **v1 stays v1.** `main.py` is a compatibility shim for the legacy notebook
  API and emits `DeprecationWarning`. Don't hard-wire new SDK features into it;
  the shims exist so old notebooks keep working.
- **No generated-code or lockfiles.** No `poetry.lock`/`pip-tools` — pin purely
  via `pyproject.toml` ranges. Don't commit `*.egg-info/`, `.venv/`,
  `.pytest_cache/`, or `scraped/` (already in `.gitignore`).

## Changing the scraper

Some pitfalls are baked into Whoscored itself — don't "fix" them unless you're
sure you understand the behaviour:

- Match pages **intermittently** return HTTP 403 challenges, even for the same
  URL between requests. The client auto-retries through a real browser
  (`fallback_to_browser=True`); that's expected, not a bug.
- League/fixture **listing** pages are Cloudflare-protected and require
  `backend="browser"`. Whoscored ships generated (hashed) CSS class names, so
  the `discovery.py` selectors may stale-out when the front-end changes — the
  match-centre pipeline never touches those pages.
- Browser automation needs Selenium ≥ 4.10 (use `service=`; `executable_path=`
  was removed). On Ubuntu, `/usr/bin/firefox` is a shell wrapper, not a real
  binary — `transports.py` auto-resolves the real snap ELF and silences benign
  geckodriver teardown noise (set `SE_DEBUG=1` or `WHOSCORED_DEBUG=1` to
  restore diagnostics).
- Proxy pools are validated against `gstatic.com`, **never** Whoscored — don't
  change the validation target, it would burn discovery requests on a page we
  are scraping.

## Submitting changes

1. Branch from `main` with a descriptive name.
2. Make focused changes; one logical change per PR.
3. Run `python test.py` locally (offline) before opening the PR.
4. If the change touches live scraping behaviour, note in the PR description
   how you validated it without hammering the site.
5. Open the PR against `main`. Keep the description short but explicit about
   what changed and why.