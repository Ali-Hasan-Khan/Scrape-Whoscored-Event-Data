"""Browser-based discovery of leagues and fixtures.

The homepage and tournament pages are protected by a Cloudflare challenge, so
listing competitions and fixtures requires a real browser (Selenium). These
routines are best-effort: Whoscored ships a heavily componentised front-end
with generated class names, so the selectors may need updating whenever
Whoscored changes its markup.

Most users never need these: match-centre pages (the actual event data) are
fetched over plain HTTP. Provide match URLs directly to
:meth:`whoscored.client.WhoscoredClient.get_match` and skip discovery entirely.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .exceptions import SeasonNotFoundError
from .models import Fixture

MAIN_URL = "https://www.whoscored.com/"

_WAIT = 10


def list_leagues(driver: Any) -> dict[str, str]:
    """Open the tournament browser and return ``{slug: url}`` for every league.

    Parameters
    ----------
    driver : selenium WebDriver
        A browser driver (Firefox/Chrome) already set up by the caller.

    Returns
    -------
    dict[str, str]
    """
    driver.get(MAIN_URL)
    wait = WebDriverWait(driver, _WAIT)
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@class=" css-gweyaj"]'))).click()
    except (NoSuchElementException, TimeoutException):
        pass
    wait.until(EC.element_to_be_clickable((By.ID, "All-Tournaments-btn"))).click()

    from bs4 import BeautifulSoup

    panel = driver.find_element(
        By.XPATH, '//*[@id="header-wrapper"]/div/div/div/div[4]/div[2]/div/div/div'
    )
    button_html = panel.find_element(By.XPATH, "./div[1]/div").get_attribute("innerHTML")
    tournaments: list[Any] = []
    for button in BeautifulSoup(button_html, "lxml").find_all("button"):
        btn_id = button.get("id")
        driver.find_element(By.ID, btn_id).click()
        country_blocks = driver.find_elements(
            By.CSS_SELECTOR, '[class*="countryDropdownContainer"]'
        )
        for block in country_blocks:
            country_el = block.find_element(By.CSS_SELECTOR, '[class*="countryDropdown"]')
            country_id = country_el.get_attribute("id")
            country_el.click()
            html = driver.find_element(
                By.XPATH,
                '//*[@id="header-wrapper"]/div/div/div/div[4]/div[2]/div/div/div/div[2]',
            ).get_attribute("innerHTML")
            tournaments.extend(BeautifulSoup(html, "lxml").find_all("a"))
            driver.execute_script("arguments[0].click();", country_el)
        # deselect the current button group
        driver.execute_script("arguments[0].click();", button)

    leagues: dict[str, str] = {}
    for anchor in tournaments:
        href = anchor.get("href")
        if not href or href == "#":
            continue
        slug = href.split("/")[-1]
        leagues[slug] = MAIN_URL[:-1] + href
    return leagues


def list_fixtures(driver: Any, competition_url: str, season: str) -> list[Fixture]:
    """Return every fixture for a competition/season from its tournament page.

    Parameters
    ----------
    driver : selenium WebDriver
        A browser driver set up by the caller.
    competition_url : str
        The tournament URL (see :func:`list_leagues`).
    season : str
        Display label of the season, e.g. ``"2023/2024"``.

    Returns
    -------
    list[Fixture]
        Fixtures sorted by date, de-duplicated.

    Raises
    ------
    SeasonNotFoundError
        When the requested season is not available for this competition.
    """
    driver.get(competition_url)
    wait = WebDriverWait(driver, _WAIT)
    seasons = wait.until(EC.presence_of_element_located((By.ID, "seasons")))
    season_options = seasons.find_elements(By.TAG_NAME, "option")
    available = [opt.text.strip() for opt in season_options]

    target = next((opt for opt in season_options if opt.text.strip() == season), None)
    if target is None:
        raise SeasonNotFoundError(
            f"Season '{season}' not found. Available: {available or 'unknown'}"
        )

    target.click()
    time.sleep(3)
    try:
        stage_options = driver.find_elements(By.CSS_SELECTOR, "#stages option")
    except NoSuchElementException:
        stage_options = [None]

    fixtures: list[Fixture] = []
    for stage in stage_options:
        if stage is not None:
            label = stage.text
            if competition_url.rstrip("/").endswith(("europe-champions-league", "europe-europa-league", "europe-conference-league")):
                if "Grp" not in label and "Final Stage" not in label:
                    continue
            stage.click()
            time.sleep(3)
        fixtures.extend(_collect_fixture_rows(driver))

    # de-duplicate while preserving order
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[Fixture] = []
    for fixture in fixtures:
        key = (fixture.date, fixture.home, fixture.away, fixture.score)
        if key not in seen:
            seen.add(key)
            unique.append(fixture)
    return sorted(unique, key=lambda f: _fixture_sort_key(f.date))


def _collect_fixture_rows(driver: Any) -> list[Fixture]:
    from bs4 import BeautifulSoup

    fixtures: list[Fixture] = []
    while True:
        initial = driver.page_source
        accordions = driver.find_elements(By.CSS_SELECTOR, '[class*="accordion"]')
        for dates in accordions:
            try:
                date_row = dates.find_element(By.CSS_SELECTOR, '[class*="header"]')
            except NoSuchElementException:
                continue
            for row in dates.find_elements(By.CSS_SELECTOR, '[class*="row"]'):
                try:
                    link = row.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href")
                except NoSuchElementException:
                    continue
                if not href or "/live/" not in href.lower():
                    continue
                element = BeautifulSoup(row.get_attribute("innerHTML"), "lxml")
                teams = element.find("div", attrs={"class": re.compile("teams")})
                if teams is None:
                    continue
                anchors = teams.find_all("a")
                if len(anchors) < 2:
                    continue
                home = anchors[0].get_text(strip=True)
                away = anchors[1].get_text(strip=True)
                score = ":".join(s.get_text(strip=True) for s in link.find_all("span")) if link.find_all("span") else ""
                fixtures.append(
                    Fixture(date=date_row.text.strip(), home=home, away=away, score=score, url=href)
                )
        try:
            prev = driver.find_element(By.ID, "dayChangeBtn-prev")
        except NoSuchElementException:
            break
        prev.click()
        time.sleep(1)
        if driver.page_source == initial:
            break
    return fixtures


def _fixture_sort_key(date: str) -> str:
    """Best-effort ISO sort key for fixture dates like 'Sunday, Aug 13 2023'."""
    try:
        from datetime import datetime

        return datetime.strptime(date.split("\n")[0].strip(), "%A, %b %d %Y").isoformat()
    except (ValueError, IndexError):
        return date


def load_league_index(path: str) -> dict[str, str]:
    """Load a league URL index from the bundled JSON snapshot."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
