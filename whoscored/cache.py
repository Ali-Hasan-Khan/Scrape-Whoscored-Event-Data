"""Minimal on-disk cache for raw match payloads.

Caching raw payloads means re-running analysis doesn't hammer Whoscored, which
is both faster and far less likely to get your IP flagged.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .exceptions import ParseError


class DiskCache:
    """Store match payloads as JSON files under ``root``.

    Parameters
    ----------
    root : str | None
        Cache directory. ``None`` disables caching.
    """

    def __init__(self, root: str | None) -> None:
        self.root = root

    def _path_for(self, match_id: int) -> str:
        return os.path.join(self.root, "matches", f"{match_id}.json")

    def enabled(self) -> bool:
        return self.root is not None

    def get(self, match_id: int) -> dict[str, Any] | None:
        """Return the cached payload for ``match_id`` or ``None``."""
        if not self.enabled():
            return None
        path = self._path_for(match_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, match_id: int, payload: dict[str, Any]) -> None:
        if not self.enabled():
            return
        path = self._path_for(match_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def clear(self) -> None:
        if not self.enabled():
            return
        import shutil

        shutil.rmtree(os.path.join(self.root, "matches"), ignore_errors=True)
