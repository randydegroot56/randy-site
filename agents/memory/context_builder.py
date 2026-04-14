"""
agents/memory/context_builder.py
==================================
ContextBuilder — scores memory entries against a query and returns top N.

Scoring: relevance (substring matching) × recency (linear decay).
Pinned entries are always included first, regardless of score, and do
not consume scored slots.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Set

from agents.memory.store import MemoryStore


class ContextBuilder:
    """Builds a ranked list of relevant memory entries for a given query."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def _relevance(self, entry: Dict, query_words: Set[str]) -> int:
        """Count query words that appear as substrings in content + keywords."""
        search_text = (
            entry["content"].lower()
            + " "
            + " ".join(entry.get("relevance_keywords", []))
        )
        return sum(1 for word in query_words if word in search_text)

    def _recency(self, entry: Dict, horizon_days: int) -> float:
        """Linear decay from 1.0 (brand-new) to 0.0 at horizon_days old."""
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
        except (ValueError, KeyError):
            return 0.0
        age_days = (datetime.now(timezone.utc) - ts).days
        return max(0.0, 1.0 - age_days / horizon_days)

    def query(
        self,
        text: str,
        max_results: int = 20,
        horizon_days: int = 365,
    ) -> List[Dict]:
        """Return relevant entries scored by relevance × recency.

        Pinned entries appear first (sorted by timestamp desc) and do not
        consume scored slots. Up to max_results unpinned entries follow.
        """
        query_words = set(text.lower().split())
        all_entries = self._store.list()

        pinned = sorted(
            [e for e in all_entries if e.get("pinned")],
            key=lambda e: e["timestamp"],
            reverse=True,
        )
        unpinned = [e for e in all_entries if not e.get("pinned")]

        scored: List[tuple] = []
        for entry in unpinned:
            rel = self._relevance(entry, query_words)
            if rel == 0:
                continue
            rec = self._recency(entry, horizon_days)
            scored.append((rel * rec, entry["timestamp"], entry))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top_unpinned = [entry for _, _, entry in scored[:max_results]]

        return pinned + top_unpinned
