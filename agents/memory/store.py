"""
agents/memory/store.py
======================
MemoryStore — JSON-backed persistent store for memory entries.

One JSON file per category in base_dir. Full array flushed on every write.
Unpinned entries are pruned oldest-first when max_size is reached.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_CATEGORIES = frozenset({"decisions", "patterns", "preferences", "history", "entities"})
DEFAULT_BASE_DIR = Path.home() / ".agent-orchestrator" / "memory"


class MemoryStore:
    """Persistent JSON-backed store for memory entries, one file per category."""

    def __init__(
        self,
        base_dir: Path = DEFAULT_BASE_DIR,
        max_size: int = 500,
    ) -> None:
        """Initialise the store.

        Args:
            base_dir: Directory where per-category JSON files are written.
                      Created (with parents) if it does not exist.
            max_size: Maximum number of entries per category file.
                      When reached, the oldest unpinned entry is removed
                      before the new one is written. Raises OverflowError
                      if all entries are pinned.
        """
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_size = max_size

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, category: str) -> Path:
        return self._base_dir / f"{category}.json"

    def _load(self, category: str) -> List[Dict[str, Any]]:
        path = self._path(category)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, category: str, entries: List[Dict[str, Any]]) -> None:
        self._path(category).write_text(
            json.dumps(entries, indent=2, default=str),
            encoding="utf-8",
        )

    def _validate_category(self, category: str) -> None:
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Valid: {sorted(VALID_CATEGORIES)}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(
        self,
        category: str,
        content: str,
        source: str,
        keywords: Optional[List[str]] = None,
        pinned: bool = False,
    ) -> Dict[str, Any]:
        """Add a memory entry. Prunes oldest unpinned entry when max_size is reached."""
        self._validate_category(category)
        entries = self._load(category)

        if len(entries) >= self._max_size:
            unpinned = [i for i, e in enumerate(entries) if not e.get("pinned", False)]
            if not unpinned:
                raise OverflowError(
                    f"Category '{category}' is at max_size ({self._max_size}) "
                    "and all entries are pinned; unpin an entry before adding more."
                )
            entries.pop(unpinned[0])

        entry: Dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "content": content,
            "source": source,
            "relevance_keywords": [kw.lower() for kw in (keywords or [])],
            "pinned": pinned,
        }
        entries.append(entry)
        self._save(category, entries)
        return entry

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single entry by id across all categories. Returns None if not found."""
        for category in VALID_CATEGORIES:
            for entry in self._load(category):
                if entry["id"] == entry_id:
                    return entry
        return None

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by id. Returns True if found and deleted, False otherwise."""
        for category in VALID_CATEGORIES:
            entries = self._load(category)
            filtered = [e for e in entries if e["id"] != entry_id]
            if len(filtered) < len(entries):
                self._save(category, filtered)
                return True
        return False

    def list(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all entries, optionally filtered to one category."""
        if category is not None:
            self._validate_category(category)
            return self._load(category)
        result: List[Dict[str, Any]] = []
        for cat in sorted(VALID_CATEGORIES):
            result.extend(self._load(cat))
        return result

    def export(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return all entries grouped by category."""
        return {cat: self._load(cat) for cat in sorted(VALID_CATEGORIES)}

    def stats(self) -> Dict[str, int]:
        """Return entry count per category."""
        return {cat: len(self._load(cat)) for cat in sorted(VALID_CATEGORIES)}
