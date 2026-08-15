"""Free-proxy pool support.

:class:`ProxyRotator` holds a list of HTTP proxies and rotates through them so
the scraper presents different IPs to Whoscored. Proxies can be supplied
directly or pulled from public free-proxy lists and validated.

.. warning::

    Free proxies are unreliable, slow, and occasionally operated by malicious
    actors. Do not send anything sensitive through them, expect a large share
    to fail, and keep the SDK's politeness settings (delays + caching) enabled.
"""

from __future__ import annotations

import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, Sequence

import requests

from .exceptions import ProxyError

#: ``host:port`` plain-text endpoints used when ``fetch_sources=True``.
FREE_PROXY_SOURCES: dict[str, str] = {
    "proxyscrape": (
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http"
        "&timeout=10000&country=all&ssl=all&anonymity=all"
    ),
    "proxy-list-download": "https://www.proxy-list.download/api/v1/get?type=http",
}

#: Lightweight, CORS-friendly endpoint used only to sanity-check proxies.
DEFAULT_VALIDATION_URL = "https://www.gstatic.com/generate_204"

Validator = Callable[[str], bool]


def normalize_proxy(proxy: str) -> str:
    """Return ``http://host:port`` for a ``host:port`` or URL-form proxy."""
    proxy = proxy.strip()
    if not proxy:
        raise ValueError("empty proxy string")
    if proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return proxy
    return f"http://{proxy}"


def _validate_proxy(proxy: str, url: str, timeout: float) -> bool:
    """Return True if the proxy can reach ``url`` within ``timeout`` seconds."""
    try:
        response = requests.get(
            url,
            proxies={"http": proxy, "https": proxy},
            timeout=timeout,
            stream=True,
        )
    except requests.RequestException:
        return False
    response.close()
    return response.ok


class ProxyRotator:
    """A rotating pool of HTTP proxies.

    Parameters
    ----------
    proxies : iterable of str, optional
        Proxies in ``host:port`` or URL form. When omitted and
        ``fetch_sources`` is set, the pool is populated from free proxy lists.
    fetch_sources : bool, default False
        Also pull proxies from :data:`FREE_PROXY_SOURCES`.
    sources : mapping of name -> url, optional
        Override the free-list endpoints used when ``fetch_sources`` is set.
    validate : bool, default True
        Test each proxy against ``validation_url`` before adding it to the
        pool. Off by default only for user-supplied lists when explicitly
        disabled; always on for fetched proxies.
    validation_url : str, default None
        Endpoint used to test proxies. Defaults to
        :data:`DEFAULT_VALIDATION_URL` (a tiny Google endpoint that does not
        touch Whoscored).
    validation_timeout : float, default 8
        Per-proxy validation timeout in seconds.
    validation_workers : int, default 16
        How many proxies are validated in parallel (keeps pool warm-up fast).
    max_pool_size : int, default 50
        Cap on the number of validated proxies kept in memory.
    seed : int, optional
        Random seed for shuffling the pool (tests).
    """

    def __init__(
        self,
        proxies: Iterable[str] = (),
        fetch_sources: bool = False,
        sources: dict[str, str] | None = None,
        validate: bool = True,
        validation_url: str | None = None,
        validation_timeout: float = 8.0,
        validation_workers: int = 16,
        max_pool_size: int = 50,
        seed: int | None = None,
    ) -> None:
        self.sources = dict(sources or FREE_PROXY_SOURCES)
        self.validate = validate
        self.validation_url = validation_url or DEFAULT_VALIDATION_URL
        self.validation_timeout = validation_timeout
        self.validation_workers = validation_workers
        self.max_pool_size = max_pool_size
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        self._pool: list[str] = []
        self._index = 0
        if proxies:
            self.add_many(proxies)
        if fetch_sources:
            self.refresh()

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def add_many(self, proxies: Iterable[str]) -> int:
        """Normalise, validate and add proxies; returns how many were kept."""
        normalized = [normalize_proxy(p) for p in proxies]
        if not self.validate:
            with self._lock:
                room = max(0, self.max_pool_size - len(self._pool))
            kept = normalized[:room]
            self._pool.extend(kept)
            self._shuffle()
            return len(kept)
        kept: list[str] = []
        count = 0
        with ThreadPoolExecutor(max_workers=self.validation_workers) as executor:
            futures = {
                executor.submit(
                    _validate_proxy, proxy, self.validation_url, self.validation_timeout
                ): proxy
                for proxy in normalized
            }
            for future in as_completed(futures):
                proxy = futures[future]
                if not future.result():
                    continue
                with self._lock:
                    if count >= self.max_pool_size:
                        continue
                    count += 1
                kept.append(proxy)
        self._pool.extend(kept)
        self._shuffle()
        return len(kept)

    def _shuffle(self) -> None:
        with self._lock:
            self._rng.shuffle(self._pool)

    def refresh(self) -> int:
        """Re-fetch proxies from the free lists and replace the pool."""
        fetched: list[str] = []
        for name, url in self.sources.items():
            try:
                response = requests.get(url, timeout=self.validation_timeout)
                response.raise_for_status()
            except requests.RequestException:
                continue
            for line in response.text.splitlines():
                line = line.strip()
                if line and ":" in line and not line.lower().startswith("http"):
                    fetched.append(normalize_proxy(line))
        with self._lock:
            self._pool = []
            self._index = 0
        return self.add_many(fetched)

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def next(self) -> str:
        """Return the next proxy URL, round-robin with random re-shuffles.

        Raises
        ------
        ProxyError
            If the pool is empty.
        """
        with self._lock:
            if not self._pool:
                raise ProxyError(
                    "No proxies available in the pool. Supply proxies or "
                    "enable fetch_sources=True to pull free proxy lists."
                )
            proxy = self._pool[self._index % len(self._pool)]
            self._index += 1
            if self._index % len(self._pool) == 0 and len(self._pool) > 1:
                self._rng.shuffle(self._pool)
                self._index = 0
            return proxy

    def request_proxies(self) -> dict[str, str]:
        """Return a ``requests``-style ``proxies`` dict for the next proxy."""
        proxy = self.next()
        return {"http": proxy, "https": proxy}

    def __len__(self) -> int:
        with self._lock:
            return len(self._pool)

    def __repr__(self) -> str:
        with self._lock:
            return f"ProxyRotator(pool_size={len(self._pool)})"
