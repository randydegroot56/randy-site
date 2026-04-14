"""Tests for agents.memory.store.MemoryStore."""
import json

import pytest

from agents.memory.store import MemoryStore, VALID_CATEGORIES


def make_store(tmp_path, max_size=500):
    return MemoryStore(base_dir=tmp_path / "memory", max_size=max_size)


# --- add ---

def test_add_returns_entry_with_correct_fields(tmp_path):
    store = make_store(tmp_path)
    entry = store.add("decisions", "We use FastAPI", "user:cli", keywords=["FastAPI"])
    assert entry["category"] == "decisions"
    assert entry["content"] == "We use FastAPI"
    assert entry["source"] == "user:cli"
    assert entry["relevance_keywords"] == ["fastapi"]   # lowercased
    assert entry["pinned"] is False
    assert "id" in entry
    assert "timestamp" in entry


def test_add_without_keywords_defaults_to_empty_list(tmp_path):
    store = make_store(tmp_path)
    entry = store.add("decisions", "content", "user:cli")
    assert entry["relevance_keywords"] == []


def test_add_invalid_category_raises(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Invalid category"):
        store.add("nonexistent", "content", "user:cli")


# --- get ---

def test_get_retrieves_by_id(tmp_path):
    store = make_store(tmp_path)
    entry = store.add("decisions", "content", "user:cli")
    found = store.get(entry["id"])
    assert found == entry


def test_get_returns_none_for_unknown_id(tmp_path):
    store = make_store(tmp_path)
    assert store.get("no-such-id") is None


# --- delete ---

def test_delete_removes_entry_and_returns_true(tmp_path):
    store = make_store(tmp_path)
    entry = store.add("decisions", "content", "user:cli")
    assert store.delete(entry["id"]) is True
    assert store.get(entry["id"]) is None


def test_delete_returns_false_for_unknown_id(tmp_path):
    store = make_store(tmp_path)
    assert store.delete("no-such-id") is False


# --- list ---

def test_list_returns_all_entries(tmp_path):
    store = make_store(tmp_path)
    store.add("decisions", "A", "user:cli")
    store.add("patterns", "B", "user:cli")
    assert len(store.list()) == 2


def test_list_filters_by_category(tmp_path):
    store = make_store(tmp_path)
    store.add("decisions", "A", "user:cli")
    store.add("patterns", "B", "user:cli")
    result = store.list(category="decisions")
    assert len(result) == 1
    assert result[0]["content"] == "A"


def test_list_invalid_category_raises(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="Invalid category"):
        store.list(category="bogus")


# --- stats ---

def test_stats_returns_correct_counts(tmp_path):
    store = make_store(tmp_path)
    store.add("decisions", "A", "user:cli")
    store.add("decisions", "B", "user:cli")
    store.add("patterns", "C", "user:cli")
    stats = store.stats()
    assert stats["decisions"] == 2
    assert stats["patterns"] == 1
    assert stats["history"] == 0


# --- export ---

def test_export_returns_all_categories(tmp_path):
    store = make_store(tmp_path)
    store.add("decisions", "content", "user:cli")
    data = store.export()
    assert set(data.keys()) == {"decisions", "patterns", "preferences", "history", "entities"}
    assert len(data["decisions"]) == 1
    assert data["patterns"] == []


# --- pruning ---

def test_pruning_removes_oldest_unpinned_at_max_size(tmp_path):
    store = make_store(tmp_path, max_size=2)
    e1 = store.add("decisions", "first", "user:cli")
    e2 = store.add("decisions", "second", "user:cli")
    e3 = store.add("decisions", "third", "user:cli")   # triggers prune of e1
    ids = [e["id"] for e in store.list(category="decisions")]
    assert e1["id"] not in ids
    assert e2["id"] in ids
    assert e3["id"] in ids


def test_pruning_preserves_pinned_entries(tmp_path):
    store = make_store(tmp_path, max_size=2)
    pinned = store.add("decisions", "pinned", "user:cli", pinned=True)
    unpinned = store.add("decisions", "unpinned", "user:cli")
    new_entry = store.add("decisions", "new", "user:cli")   # triggers prune of unpinned
    ids = [e["id"] for e in store.list(category="decisions")]
    assert pinned["id"] in ids        # pinned survives
    assert unpinned["id"] not in ids  # oldest unpinned removed
    assert new_entry["id"] in ids


# --- persistence ---

def test_data_survives_reconstruction(tmp_path):
    base_dir = tmp_path / "memory"
    store = MemoryStore(base_dir=base_dir)
    entry = store.add("decisions", "persistent content", "user:cli")

    store2 = MemoryStore(base_dir=base_dir)
    assert store2.get(entry["id"]) == entry
