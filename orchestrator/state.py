"""
orchestrator/state.py
=====================
JSON-backed key-value StateStore.

Persists every set/delete immediately. Handles missing or
corrupted files gracefully by starting with an empty state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_STATE_FILE = Path(".orchestrator_state.json")


class StateStore:
    """Persistent key-value store backed by a JSON file."""

    def __init__(self, path: Path = DEFAULT_STATE_FILE) -> None:
        self._path = Path(path)
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._save()

    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, default=str),
            encoding="utf-8",
        )
