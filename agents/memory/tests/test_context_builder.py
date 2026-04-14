"""Tests for agents.memory.context_builder.ContextBuilder."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from agents.memory.context_builder import ContextBuilder
from agents.memory.store import MemoryStore


def make_store_and_builder(tmp_path):
    store = MemoryStore(base_dir=tmp_path / "memory")
    builder = ContextBuilder(store)
    return store, builder


def test_query_returns_matching_entries(tmp_path):
    store, builder = make_store_and_builder(tmp_path)
    store.add("decisions", "We use FastAPI for the REST API", "user:cli", keywords=["fastapi"])
    store.add("decisions", "Database is PostgreSQL", "user:cli", keywords=["postgres"])
    results = builder.query("fastapi")
    assert len(results) == 1
    assert "FastAPI" in results[0]["content"]


def test_query_no_match_returns_empty(tmp_path):
    store, builder = make_store_and_builder(tmp_path)
    store.add("decisions", "We use FastAPI", "user:cli", keywords=["fastapi"])
    results = builder.query("django")
    assert results == []


def test_query_respects_max_results(tmp_path):
    store, builder = make_store_and_builder(tmp_path)
    for i in range(10):
        store.add("decisions", f"FastAPI note {i}", "user:cli", keywords=["fastapi"])
    results = builder.query("fastapi", max_results=3)
    assert len(results) <= 3


def test_pinned_entries_appear_first(tmp_path):
    store, builder = make_store_and_builder(tmp_path)
    store.add("decisions", "unpinned fastapi note", "user:cli", keywords=["fastapi"])
    pinned = store.add(
        "decisions", "pinned fastapi note", "user:cli", keywords=["fastapi"], pinned=True
    )
    results = builder.query("fastapi")
    assert results[0]["id"] == pinned["id"]


def test_recency_decay_older_entry_scores_lower(tmp_path):
    """An entry 300 days old should rank below a fresh entry with equal keyword overlap."""
    store, builder = make_store_and_builder(tmp_path)
    recent = store.add("decisions", "fastapi choice", "user:cli", keywords=["fastapi"])

    # Inject an old entry by patching the JSON file directly
    cat_file = tmp_path / "memory" / "decisions.json"
    data = json.loads(cat_file.read_text())
    old_entry = {
        "id": "old-entry-001",
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=300)).isoformat(),
        "category": "decisions",
        "content": "fastapi choice",
        "source": "user:cli",
        "relevance_keywords": ["fastapi"],
        "pinned": False,
    }
    data.append(old_entry)
    cat_file.write_text(json.dumps(data))

    results = builder.query("fastapi", horizon_days=365)
    assert results[0]["id"] == recent["id"]      # recent ranks higher
    assert results[1]["id"] == "old-entry-001"


def test_zero_relevance_entries_excluded(tmp_path):
    store, builder = make_store_and_builder(tmp_path)
    store.add("decisions", "completely unrelated content", "user:cli", keywords=["postgres"])
    results = builder.query("fastapi")
    assert results == []


def test_pinned_entries_do_not_consume_scored_slots(tmp_path):
    """max_results=2 with 1 pinned should still return 2 scored entries (+ the pinned)."""
    store, builder = make_store_and_builder(tmp_path)
    pinned = store.add("decisions", "pinned fastapi", "user:cli", keywords=["fastapi"], pinned=True)
    scored1 = store.add("decisions", "fastapi one", "user:cli", keywords=["fastapi"])
    scored2 = store.add("decisions", "fastapi two", "user:cli", keywords=["fastapi"])
    results = builder.query("fastapi", max_results=2)
    ids = [r["id"] for r in results]
    assert pinned["id"] in ids
    assert scored1["id"] in ids
    assert scored2["id"] in ids
