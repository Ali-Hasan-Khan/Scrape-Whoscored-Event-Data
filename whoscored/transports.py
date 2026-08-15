"""Transport backends for fetching Whoscored pages.

Two backends are provided:

* :class:`HttpTransport` — plain HTTP requests. Works for match-centre pages,
  which are served without a bot challenge. Lightweight and the default.
* :class:`BrowserTransport` — Selenium driving a real browser. Required for
  pages behind Cloudflare's "Just a moment..." challenge (homepage and
  tournament fixture listings). A headed browser is used by default because
  headless browsers are detected far more easily.
"""

from __future__ import annotations

import glob
import logging
import os
import shutil
import subprocess
from typing import Any, Protocol

import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.service import Service as FirefoxService

from .exceptions import BackendError, BlockedError, TransportError
from .proxies import normalize_proxy
from .utils import RateLimiter, retry

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class _CosmeticWarningFilter(logging.Filter):
    """Drops Selenium Manager's cosmetic driver/browser version warnings."""

    _NOISE = ("might not be compatible",)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(n in message for n in self._NOISE)


# Applies for the life of the process; harmless and targeted.
logging.getLogger("selenium.webdriver.common.selenium_manager").addFilter(
    _CosmeticWarningFilter()
)


def _is_elf(path: str) -> bool:
    """Return True if the file at ``path`` is a real ELF executable."""
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def _resolve_firefox_binary(binary_location: str | None) -> str | None:
    """Locate the actual Firefox binary, working around distro wrappers.

    On Ubuntu/Debian ``/usr/bin/firefox`` (and snap launchers) are shell
    wrapper scripts that geckodriver rejects with "binary is not a Firefox
    executable". This returns the real ELF binary instead.
    """
    if binary_location:
        return binary_location
    env_path = os.environ.get("FIREFOX_BIN")
    if env_path and os.path.isfile(env_path) and _is_elf(env_path):
        return env_path
    candidates: list[str] = []
    candidates.extend(
        sorted(
            glob.glob("/snap/firefox/*/usr/lib/firefox/firefox"),
            reverse=True,
        )
    )
    candidates += [
        "/usr/lib/firefox/firefox",
        "/opt/firefox/firefox",
        shutil.which("firefox") or "",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and _is_elf(candidate):
            return candidate
    return binary_location


class _QuietFirefoxService(FirefoxService):
    """Firefox service that silences benign driver-shutdown noise.

    Snap-packaged geckodriver processes refuse the final SIGTERM with a
    ``PermissionError``, which Selenium logs as ``Error terminating service
    process`` plus a full traceback on every close. The error is harmless, so
    we swallow it and keep the standard teardown behaviour otherwise.

    geckodriver's own stderr is sent to ``DEVNULL`` unless ``SE_DEBUG`` or
    ``WHOSCORED_DEBUG`` is set, hiding cosmetic version-mismatch warnings.
    Real driver errors still reach Selenium through the response body.
    """

    def __init__(self, log_output: Any = None, **kwargs: Any) -> None:
        debug = os.environ.get("SE_DEBUG") or os.environ.get("WHOSCORED_DEBUG")
        if log_output is None and not debug:
            log_output = subprocess.DEVNULL
        super().__init__(log_output=log_output, **kwargs)

    def _terminate_process(self) -> None:
        process = self.process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    process.terminate()
                except PermissionError:
                    pass  # snap-run driver cannot be signalled; it exits on its own
                else:
                    try:
                        process.wait(60)
                    except subprocess.TimeoutExpired:
                        try:
                            process.kill()
                        except PermissionError:
                            pass
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except (AttributeError, OSError):
                    pass
        except PermissionError:
            pass


class Transport(Protocol):
    def get(self, url: str) -> str: ...

    def close(self) -> None: ...


class HttpTransport:
    """Fetch pages over plain HTTP(S) with polite rate limiting.

    Parameters
    ----------
    request_delay : float, default 7.0
        Minimum gap between requests (see :class:`RateLimiter`).
    jitter : float, default 2.0
        Randomised extra delay added to keep requests irregular.
    timeout : float, default 30
        Per-request timeout in seconds.
    retries : int, default 3
        Retries per page on transient failures.
    user_agent : str, optional
        Override the default browser user agent.
    session : requests.Session, optional
        Reuse an existing session (e.g. one that already holds cookies).
    proxy : str, optional
        A single ``host:port`` or ``http://host:port`` proxy used for every
        request.
    proxy_pool : ProxyRotator, optional
        Rotate through a pool of proxies, one per request. Takes precedence
        over ``proxy``.
    """

    def __init__(
        self,
        request_delay: float = 7.0,
        jitter: float = 2.0,
        timeout: float = 30.0,
        retries: int = 3,
        user_agent: str | None = None,
        session: requests.Session | None = None,
        proxy: str | None = None,
        proxy_pool: Any = None,
    ) -> None:
        self.limiter = RateLimiter(request_delay, jitter)
        self.timeout = timeout
        self.retries = retries
        self.proxy = normalize_proxy(proxy) if proxy else None
        self.proxy_pool = proxy_pool
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent or DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.whoscored.com/",
            }
        )

    def get(self, url: str) -> str:
        """Fetch ``url``, retrying through (rotating) proxies as needed.

        Blocked/challenged responses are retried with the next proxy when a
        pool is configured, so a single bad or blocked proxy does not fail the
        request. Without a pool, a block is surfaced immediately as
        :class:`BlockedError`.
        """
        last_exc: Exception | None = None
        for _attempt in range(self.retries + 1):
            try:
                return self._fetch_once(url)
            except BlockedError:
                if self.proxy_pool is None:
                    raise
                last_exc = BlockedError(
                    f"All proxies were blocked for {url}. The site returned "
                    "bot challenges through every proxy tried."
                )
            except TransportError as exc:
                last_exc = exc
        assert last_exc is not None
        raise last_exc

    def _fetch_once(self, url: str) -> str:
        self.limiter.wait()
        try:
            response = self.session.get(
                url, timeout=self.timeout, proxies=self._request_proxies()
            )
        except (BlockedError, TransportError):
            raise
        except Exception as exc:  # noqa: BLE001 - proxy pools return garbage
            raise TransportError(f"Request failed for {url}: {exc}") from exc
        if response.status_code == 403:
            raise BlockedError(
                f"HTTP 403 for {url}. The site returned a bot challenge. "
                "Use the browser backend (backend='browser') for this page."
            )
        if response.status_code == 404:
            raise BlockedError(f"HTTP 404 for {url}.")
        if response.status_code != 200:
            raise TransportError(f"Unexpected HTTP {response.status_code} for {url}.")
        return response.text

    def _request_proxies(self) -> dict[str, str] | None:
        if self.proxy_pool is not None:
            return self.proxy_pool.request_proxies()
        if self.proxy is not None:
            return {"http": self.proxy, "https": self.proxy}
        return None

    def close(self) -> None:
        self.session.close()


class BrowserTransport:
    """Fetch pages through a Selenium-controlled browser.

    Needed for Cloudflare-protected pages. The driver is created lazily on the
    first request, so constructing the transport costs nothing if it is never
    used.

    Parameters
    ----------
    driver : selenium.webdriver.Remote | WebDriver, optional
        An existing, already-configured driver. When omitted a new Firefox
        driver is launched.
    headless : bool, default False
        Launch the browser headless. Headed is strongly recommended: headless
        browsers are easily flagged by bot protection.
    executable_path : str, optional
        Override the geckodriver/chromedriver path.
    browser : str, default "firefox"
        Either ``"firefox"`` or ``"chrome"``.
    binary_location : str, optional
        Path to the browser executable. For Firefox this is auto-detected
        (with a ``FIREFOX_BIN`` env override) because distro wrappers such as
        the Ubuntu snap launcher are not real executables.
    """

    def __init__(
        self,
        driver: Any = None,
        headless: bool = False,
        executable_path: str | None = None,
        browser: str = "firefox",
        binary_location: str | None = None,
    ) -> None:
        self._driver = driver
        self.headless = headless
        self.executable_path = executable_path
        self.browser = browser
        self.binary_location = _resolve_firefox_binary(binary_location)

    @property
    def driver(self) -> Any:
        if self._driver is None:
            self._driver = self._launch()
        return self._driver

    def _launch(self) -> Any:
        if self.browser == "firefox":
            options = webdriver.FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            if self.binary_location:
                options.binary_location = self.binary_location
            service = _QuietFirefoxService(
                executable_path=self.executable_path
            ) if self.executable_path else _QuietFirefoxService()
            return webdriver.Firefox(options=options, service=service)
        if self.browser == "chrome":
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")
            service = webdriver.ChromeService(
                executable_path=self.executable_path
            ) if self.executable_path else webdriver.ChromeService()
            return webdriver.Chrome(options=options, service=service)
        raise BackendError(f"Unsupported browser '{self.browser}' (use 'firefox' or 'chrome').")

    def get(self, url: str) -> str:
        try:
            self.driver.get(url)
            return self.driver.page_source
        except WebDriverException as exc:
            raise TransportError(f"Browser navigation failed for {url}: {exc}") from exc

    def close(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except WebDriverException:
                pass
            self._driver = None
