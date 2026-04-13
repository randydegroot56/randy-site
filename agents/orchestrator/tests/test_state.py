import json
from agents.orchestrator.state import StateStore


def test_get_returns_default_when_key_missing(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.get("missing", "default") == "default"


def test_get_returns_none_by_default_when_key_missing(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.get("missing") is None


def test_set_and_get(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set("key", {"value": 42})
    assert store.get("key") == {"value": 42}


def test_persists_to_disk(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set("persistent_key", "hello")

    store2 = StateStore(path)
    assert store2.get("persistent_key") == "hello"


def test_persisted_file_is_valid_json(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set("x", [1, 2, 3])

    content = path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["x"] == [1, 2, 3]


def test_delete_removes_key(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set("to_delete", 1)
    store.delete("to_delete")
    assert store.get("to_delete") is None


def test_delete_nonexistent_key_is_silent(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.delete("never_existed")  # Must not raise


def test_all_returns_full_snapshot(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set("a", 1)
    store.set("b", 2)
    assert store.all() == {"a": 1, "b": 2}


def test_corrupted_state_file_starts_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("NOT JSON", encoding="utf-8")
    store = StateStore(path)
    assert store.all() == {}
