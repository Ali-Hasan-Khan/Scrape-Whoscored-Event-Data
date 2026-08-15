"""Small utilities: polite rate limiting, retries and data I/O helpers."""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Callable, TypeVar

import pandas as pd

T = TypeVar("T")


class RateLimiter:
    """Sleep between requests so scraping stays polite and under the radar.

    Parameters
    ----------
    delay : float, default 7.0
        Minimum number of seconds between successive :meth:`wait` calls.
    jitter : float, default 2.0
        Random extra delay in ``[0, jitter)`` seconds added on top of
        ``delay`` so requests don't arrive on a rigid clock.
    """

    def __init__(self, delay: float = 7.0, jitter: float = 2.0) -> None:
        if delay < 0 or jitter < 0:
            raise ValueError("delay and jitter must be >= 0")
        self.delay = delay
        self.jitter = jitter
        self._last: float | None = None

    def wait(self) -> None:
        """Block until the next request is allowed."""
        now = time.monotonic()
        if self._last is not None:
            elapsed = now - self._last
            required = self.delay + random.random() * self.jitter
            if elapsed < required:
                time.sleep(required - elapsed)
        self._last = time.monotonic()

    def __enter__(self) -> "RateLimiter":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


def retry(
    func: Callable[[], T],
    *,
    retries: int = 3,
    backoff: float = 1.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call ``func`` with exponential backoff retries.

    Parameters
    ----------
    func : callable
        Zero-argument callable returning the desired value.
    retries : int, default 3
        Maximum number of attempts (including the first).
    backoff : float, default 1.5
        Base for the exponential sleep between attempts.
    exceptions : tuple[type[Exception], ...], default (Exception,)
        Which exceptions trigger a retry.

    Returns
    -------
    The return value of ``func``.

    Raises
    ------
    The last exception raised by ``func`` once retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return func()
        except exceptions as exc:  # noqa: PERF203 - intentional retry loop
            last_exc = exc
            if attempt == retries - 1:
                break
            time.sleep(backoff ** attempt + random.random())
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Data I/O helpers
# ---------------------------------------------------------------------------


def save_dataframe(df: pd.DataFrame, path: str) -> str:
    """Persist a DataFrame to CSV or Parquet based on the file extension.

    Supports ``.csv``, ``.csv.gz`` and ``.parquet`` (requires ``pyarrow`` or
    ``fastparquet`` for the latter).

    Parameters
    ----------
    df : pandas.DataFrame
        Frame to save.
    path : str
        Destination path.

    Returns
    -------
    str
        The path written to.
    """
    path = _ensure_dir(path)
    lower = path.lower()
    if lower.endswith(".parquet"):
        df.to_parquet(path, index=False)
    elif lower.endswith(".csv.gz"):
        df.to_csv(path, index=False, compression="gzip")
    elif lower.endswith(".csv"):
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported file extension for '{path}' (use .csv or .parquet)")
    return path


def load_dataframe(path: str) -> pd.DataFrame:
    """Load a DataFrame saved with :func:`save_dataframe`."""
    lower = path.lower()
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def save_json(data: Any, path: str) -> str:
    """Write ``data`` to a JSON file, creating parent directories as needed."""
    path = _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    return path


def load_json(path: str) -> Any:
    """Load a JSON file written with :func:`save_json`."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_dir(path: str) -> str:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    return path
