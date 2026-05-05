# Memory Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent Memory Agent that stores project context, auto-indexes agent events, delivers ranked context on demand, and integrates with the existing EventBus/AgentRegistry/StateStore/OrchestratorLogger stack.

**Architecture:** Flat-module design mirroring `agents/code_auditor/core/` — `store.py`, `context_builder.py`, and `indexer.py` are independent classes composed by `MemoryAgent` in `agent.py`. The agent registers under the name `"memory"` and receives CLI args as a list it dispatches internally.

**Tech Stack:** Python 3.12, stdlib only (`json`, `uuid`, `pathlib`, `datetime`), pytest for tests.

---

## Reference: Existing Interfaces

Before starting, understand these existing types (do not modify their signatures):

```python
# agents/orchestrator/base_agent.py
class BaseAgent(ABC):
    name: str = ""
    description: str = ""
    def __init__(self, bus: EventBus, state: StateStore) -> None: ...
    def emit(self, event: AgentEvent) -> None: ...   # publishes + caches in state

# agents/orchestrator/bus.py
class EventBus:
    def subscribe(self, event_type: str, handler: Callable[[AgentEvent], None]) -> None: ...
    def publish(self, event: AgentEvent) -> None: ...

# agents/orchestrator/events.py
@dataclass
class AgentEvent:
    agent_name: str
    event_type: str = "AgentEvent"
    timestamp: str = field(default_factory=...)
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    error: Optional[str] = None
```

---

## Task 1: Add MemoryUpdated and ContextProvided events

**Files:**
- Modify: `agents/orchestrator/events.py`
- Test: `agents/orchestrator/tests/test_events.py` (extend existing)

- [ ] **Step 1: Write the failing test**

  Open `agents/orchestrator/tests/test_events.py` and add at the bottom:

  ```python
  def test_memory_updated_event():
      from agents.orchestrator.events import MemoryUpdated
      e = MemoryUpdated(agent_name="memory", payload={"entry_id": "abc"})
      assert e.event_type == "MemoryUpdated"
      assert e.status == "success"
      assert e.payload == {"entry_id": "abc"}


  def test_context_provided_event():
      from agents.orchestrator.events import ContextProvided
      e = ContextProvided(agent_name="memory", payload={"query": "fastapi"})
      assert e.event_type == "ContextProvided"
      assert e.status == "success"
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/orchestrator/tests/test_events.py -v
  ```
  Expected: `ImportError: cannot import name 'MemoryUpdated'`

- [ ] **Step 3: Add the new event classes to events.py**

  Open `agents/orchestrator/events.py`. After the `FixFailed` dataclass, append:

  ```python
  @dataclass
  class MemoryUpdated(AgentEvent):
      event_type: str = "MemoryUpdated"


  @dataclass
  class ContextProvided(AgentEvent):
      event_type: str = "ContextProvided"
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/orchestrator/tests/test_events.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Commit**

  ```bash
  git add agents/orchestrator/events.py agents/orchestrator/tests/test_events.py
  git commit -m "feat(events): add MemoryUpdated and ContextProvided event types"
  ```

---

## Task 2: Package scaffolding

**Files:**
- Create: `agents/memory/__init__.py`
- Create: `agents/memory/tests/__init__.py`

- [ ] **Step 1: Create both files**

  Create `agents/memory/__init__.py` with content:
  ```python
  """agents/memory — persistent memory layer for the multi-agent system."""
  ```

  Create `agents/memory/tests/__init__.py` with content:
  ```python
  ```
  (empty)

- [ ] **Step 2: Verify Python can find the package**

  ```
  python -c "import agents.memory; print('ok')"
  ```
  Expected: `ok`

- [ ] **Step 3: Commit**

  ```bash
  git add agents/memory/__init__.py agents/memory/tests/__init__.py
  git commit -m "feat(memory): scaffold agents/memory package"
  ```

---

## Task 3: MemoryStore

**Files:**
- Create: `agents/memory/store.py`
- Create: `agents/memory/tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/memory/tests/test_store.py`:

  ```python
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
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/memory/tests/test_store.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.memory.store'`

- [ ] **Step 3: Implement MemoryStore**

  Create `agents/memory/store.py`:

  ```python
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
              return json.loads(path.read_text(encoding="utf-8"))
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
              for i, e in enumerate(entries):
                  if not e.get("pinned", False):
                      entries.pop(i)
                      break

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
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/memory/tests/test_store.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Commit**

  ```bash
  git add agents/memory/store.py agents/memory/tests/test_store.py
  git commit -m "feat(memory): implement MemoryStore with JSON persistence and pruning"
  ```

---

## Task 4: ContextBuilder

**Files:**
- Create: `agents/memory/context_builder.py`
- Create: `agents/memory/tests/test_context_builder.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/memory/tests/test_context_builder.py`:

  ```python
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
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/memory/tests/test_context_builder.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.memory.context_builder'`

- [ ] **Step 3: Implement ContextBuilder**

  Create `agents/memory/context_builder.py`:

  ```python
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
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/memory/tests/test_context_builder.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Commit**

  ```bash
  git add agents/memory/context_builder.py agents/memory/tests/test_context_builder.py
  git commit -m "feat(memory): implement ContextBuilder with substring matching and linear recency decay"
  ```

---

## Task 5: MemoryIndexer

**Files:**
- Create: `agents/memory/indexer.py`
- Create: `agents/memory/tests/test_indexer.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/memory/tests/test_indexer.py`:

  ```python
  """Tests for agents.memory.indexer.MemoryIndexer."""
  import pytest

  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.events import AgentEvent, AuditCompleted
  from agents.memory.indexer import MemoryIndexer
  from agents.memory.store import MemoryStore


  def make_indexer(tmp_path):
      bus = EventBus()
      store = MemoryStore(base_dir=tmp_path / "memory")
      indexer = MemoryIndexer(bus, store)
      return bus, store, indexer


  def test_successful_event_stored_in_history(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AgentEvent(agent_name="code_auditor", event_type="SomeEvent"))
      history = store.list(category="history")
      assert len(history) == 1
      assert "SomeEvent" in history[0]["content"]
      assert "code_auditor" in history[0]["content"]


  def test_failed_event_includes_error_in_history(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AgentEvent(
          agent_name="code_auditor",
          event_type="AuditFailed",
          status="failed",
          error="Permission denied",
      ))
      history = store.list(category="history")
      assert len(history) == 1
      assert "ERROR: Permission denied" in history[0]["content"]


  def test_audit_completed_also_stored_in_patterns(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AuditCompleted(
          agent_name="code_auditor",
          payload={"target": "./src", "issues_found": 5},
      ))
      history = store.list(category="history")
      patterns = store.list(category="patterns")
      assert len(history) == 1
      assert len(patterns) == 1
      assert "./src" in patterns[0]["content"]
      assert "5" in patterns[0]["content"]


  def test_memory_updated_not_reprocessed(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AgentEvent(agent_name="memory", event_type="MemoryUpdated"))
      assert store.list(category="history") == []


  def test_context_provided_not_reprocessed(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AgentEvent(agent_name="memory", event_type="ContextProvided"))
      assert store.list(category="history") == []


  def test_indexer_publishes_memory_updated_after_storing(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      received = []
      bus.subscribe("MemoryUpdated", received.append)
      bus.publish(AgentEvent(agent_name="test_agent", event_type="SomeEvent"))
      assert len(received) >= 1
      assert received[0].event_type == "MemoryUpdated"


  def test_source_is_agent_name(tmp_path):
      bus, store, _ = make_indexer(tmp_path)
      bus.publish(AgentEvent(agent_name="code_auditor", event_type="SomeEvent"))
      history = store.list(category="history")
      assert history[0]["source"] == "agent:code_auditor"
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/memory/tests/test_indexer.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.memory.indexer'`

- [ ] **Step 3: Implement MemoryIndexer**

  Create `agents/memory/indexer.py`:

  ```python
  """
  agents/memory/indexer.py
  =========================
  MemoryIndexer — subscribes to all bus events and auto-extracts memory facts.

  Layer 1: every event generates a human-readable summary stored in 'history'.
  Layer 2: specific event types generate additional entries in other categories
           via EVENT_CATEGORY_MAP.

  MemoryUpdated and ContextProvided events are ignored to prevent feedback loops.
  """
  from __future__ import annotations

  from typing import Callable, Dict, FrozenSet, Tuple

  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.events import AgentEvent, MemoryUpdated
  from agents.memory.store import MemoryStore

  # Maps event_type -> (target_category, content_factory)
  EVENT_CATEGORY_MAP: Dict[str, Tuple[str, Callable[[AgentEvent], str]]] = {
      "AuditCompleted": (
          "patterns",
          lambda e: (
              f"Audit of {e.payload.get('target', '?')} "
              f"found {e.payload.get('issues_found', '?')} issues"
          ),
      ),
      "FixCompleted": (
          "history",
          lambda e: f"Fix applied to {e.payload.get('target', '?')}",
      ),
  }

  # Events emitted by the memory agent itself — skip to avoid feedback loops
  _IGNORE: FrozenSet[str] = frozenset({"MemoryUpdated", "ContextProvided"})


  class MemoryIndexer:
      """Listens to all EventBus events; stores relevant facts in MemoryStore."""

      def __init__(self, bus: EventBus, store: MemoryStore) -> None:
          self._bus = bus
          self._store = store
          bus.subscribe("*", self._handle)

      def _handle(self, event: AgentEvent) -> None:
          """Extract and store facts from an incoming event."""
          if event.event_type in _IGNORE:
              return

          # Layer 1 — always: human-readable summary in history
          if event.status == "failed" and event.error:
              content = f"{event.event_type} by {event.agent_name} — ERROR: {event.error}"
          else:
              content = f"{event.event_type} by {event.agent_name}"

          keywords = [event.event_type.lower(), event.agent_name.lower(), event.status]
          source = f"agent:{event.agent_name}"

          entry = self._store.add("history", content, source, keywords=keywords)
          self._bus.publish(
              MemoryUpdated(
                  agent_name="memory",
                  payload={"entry_id": entry["id"], "category": "history"},
              )
          )

          # Layer 2 — event-type mapping: additional entry in mapped category
          if event.event_type in EVENT_CATEGORY_MAP:
              category, factory = EVENT_CATEGORY_MAP[event.event_type]
              extra = self._store.add(
                  category,
                  factory(event),
                  source,
                  keywords=keywords,
              )
              self._bus.publish(
                  MemoryUpdated(
                      agent_name="memory",
                      payload={"entry_id": extra["id"], "category": category},
                  )
              )
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/memory/tests/test_indexer.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Commit**

  ```bash
  git add agents/memory/indexer.py agents/memory/tests/test_indexer.py
  git commit -m "feat(memory): implement MemoryIndexer with event-driven auto-extraction"
  ```

---

## Task 6: MemoryAgent

**Files:**
- Create: `agents/memory/agent.py`
- Create: `agents/memory/tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/memory/tests/test_agent.py`:

  ```python
  """Tests for agents.memory.agent.MemoryAgent."""
  import pytest

  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.state import StateStore
  from agents.memory.agent import MemoryAgent


  def make_agent(tmp_path):
      bus = EventBus()
      state = StateStore(tmp_path / "state.json")
      agent = MemoryAgent(bus=bus, state=state, memory_dir=tmp_path / "memory")
      return agent, bus, state


  # --- dispatch ---

  def test_unknown_subcommand_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Unknown memory subcommand 'bogus'"):
          agent.run(args=["bogus"])


  def test_none_subcommand_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Unknown memory subcommand 'None'"):
          agent.run(args=[])


  # --- add ---

  def test_add_stores_entry(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["add", "decisions", "We use FastAPI"])
      assert "added" in result
      assert result["added"]["content"] == "We use FastAPI"
      assert result["added"]["category"] == "decisions"


  def test_add_joins_multi_word_text(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["add", "decisions", "We", "use", "FastAPI"])
      assert result["added"]["content"] == "We use FastAPI"


  def test_add_missing_text_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Usage: memory add"):
          agent.run(args=["add", "decisions"])   # category given, text missing


  def test_add_missing_all_args_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Usage: memory add"):
          agent.run(args=["add"])


  # --- query ---

  def test_query_returns_results(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      agent.run(args=["add", "decisions", "We use FastAPI for REST"])
      result = agent.run(args=["query", "fastapi"])
      assert "results" in result


  def test_query_publishes_context_provided(tmp_path):
      agent, bus, _ = make_agent(tmp_path)
      agent.run(args=["add", "decisions", "We use FastAPI for REST"])
      received = []
      bus.subscribe("ContextProvided", received.append)
      agent.run(args=["query", "fastapi"])
      assert len(received) == 1
      assert received[0].event_type == "ContextProvided"


  def test_query_missing_text_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Usage: memory query"):
          agent.run(args=["query"])


  # --- list ---

  def test_list_returns_entries(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      agent.run(args=["add", "decisions", "content A"])
      result = agent.run(args=["list"])
      assert "entries" in result
      assert len(result["entries"]) == 1


  def test_list_filters_by_category(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      agent.run(args=["add", "decisions", "decision A"])
      agent.run(args=["add", "patterns", "pattern B"])
      result = agent.run(args=["list", "decisions"])
      assert len(result["entries"]) == 1
      assert result["entries"][0]["category"] == "decisions"


  # --- forget ---

  def test_forget_unknown_id_returns_false(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["forget", "no-such-id"])
      assert result == {"deleted": False}


  def test_forget_known_id_returns_true(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      add_result = agent.run(args=["add", "decisions", "to be deleted"])
      entry_id = add_result["added"]["id"]
      result = agent.run(args=["forget", entry_id])
      assert result == {"deleted": True}


  def test_forget_missing_id_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Usage: memory forget"):
          agent.run(args=["forget"])


  # --- stats ---

  def test_stats_returns_counts(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      agent.run(args=["add", "decisions", "A"])
      agent.run(args=["add", "decisions", "B"])
      result = agent.run(args=["stats"])
      assert result["stats"]["decisions"] == 2


  # --- export ---

  def test_export_returns_all_categories(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["export"])
      assert set(result.keys()) == {"decisions", "patterns", "preferences", "history", "entities"}
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/memory/tests/test_agent.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.memory.agent'`

- [ ] **Step 3: Implement MemoryAgent**

  Create `agents/memory/agent.py`:

  ```python
  """
  agents/memory/agent.py
  =======================
  MemoryAgent — exposes memory operations to the CLI via the Orchestrator.

  Registered as "memory" in AgentRegistry.
  INTENT_MAP entry: "memory" -> ("memory", "args")

  run(args=[subcommand, ...]) dispatches to internal methods:
      add <category> <text ...>
      query <text ...>
      list [category]
      forget <id>
      export
      stats
  """
  from __future__ import annotations

  import json
  from pathlib import Path
  from typing import Any, Dict, List, Optional

  from agents.orchestrator.base_agent import BaseAgent
  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.events import ContextProvided, MemoryUpdated
  from agents.orchestrator.state import StateStore
  from agents.memory.context_builder import ContextBuilder
  from agents.memory.indexer import MemoryIndexer
  from agents.memory.store import MemoryStore

  DEFAULT_MEMORY_DIR = Path.home() / ".agent-orchestrator" / "memory"


  class MemoryAgent(BaseAgent):
      """Persistent memory and context store for the agent system."""

      name = "memory"
      description = "Persistent memory and context store for the agent system"

      def __init__(
          self,
          bus: EventBus,
          state: StateStore,
          memory_dir: Path = DEFAULT_MEMORY_DIR,
      ) -> None:
          super().__init__(bus=bus, state=state)
          self._store = MemoryStore(base_dir=Path(memory_dir))
          self._context = ContextBuilder(self._store)
          self._indexer = MemoryIndexer(bus, self._store)

      # ------------------------------------------------------------------
      # Dispatch
      # ------------------------------------------------------------------

      def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
          """Dispatch to subcommand. args[0] is subcommand; args[1:] are parameters."""
          args = list(args or [])
          dispatch = {
              "add":    self._cmd_add,
              "query":  self._cmd_query,
              "list":   self._cmd_list,
              "forget": self._cmd_forget,
              "export": self._cmd_export,
              "stats":  self._cmd_stats,
          }
          subcommand = args[0] if args else None
          if subcommand not in dispatch:
              available = ", ".join(sorted(dispatch))
              raise ValueError(
                  f"Unknown memory subcommand '{subcommand}'. Available: {available}"
              )
          return dispatch[subcommand](args[1:])

      # ------------------------------------------------------------------
      # Subcommands
      # ------------------------------------------------------------------

      def _cmd_add(self, args: List[str]) -> Dict[str, Any]:
          """add <category> <text ...> — store a new memory entry."""
          if len(args) < 2:
              raise ValueError("Usage: memory add <category> <text>")
          category = args[0]
          content = " ".join(args[1:])
          entry = self._store.add(category, content, source="user:cli")
          self.emit(MemoryUpdated(
              agent_name=self.name,
              payload={"entry_id": entry["id"], "category": category},
          ))
          print(f"Memory stored [{category}]: {entry['id']}")
          return {"added": entry}

      def _cmd_query(self, args: List[str]) -> Dict[str, Any]:
          """query <text ...> — retrieve ranked context entries."""
          if not args:
              raise ValueError("Usage: memory query <text>")
          text = " ".join(args)
          results = self._context.query(text)
          self.emit(ContextProvided(
              agent_name=self.name,
              payload={"query": text, "results_count": len(results)},
          ))
          for entry in results:
              pin = " [pinned]" if entry.get("pinned") else ""
              print(f"[{entry['category']}]{pin} {entry['content']}  (id: {entry['id']})")
          return {"results": results}

      def _cmd_list(self, args: List[str]) -> Dict[str, Any]:
          """list [category] — show stored memories, optionally filtered."""
          category = args[0] if args else None
          entries = self._store.list(category=category)
          for entry in entries:
              pin = " [pinned]" if entry.get("pinned") else ""
              print(f"[{entry['category']}]{pin} {entry['content']}  (id: {entry['id']})")
          return {"entries": entries}

      def _cmd_forget(self, args: List[str]) -> Dict[str, Any]:
          """forget <id> — delete a memory entry by id."""
          if not args:
              raise ValueError("Usage: memory forget <id>")
          entry_id = args[0]
          deleted = self._store.delete(entry_id)
          if deleted:
              self.emit(MemoryUpdated(
                  agent_name=self.name,
                  payload={"deleted_id": entry_id},
              ))
              print(f"Memory deleted: {entry_id}")
          else:
              print(f"No memory found with id: {entry_id}")
          return {"deleted": deleted}

      def _cmd_export(self, args: List[str]) -> Dict[str, Any]:
          """export — print all memories as JSON."""
          data = self._store.export()
          print(json.dumps(data, indent=2, default=str))
          return data

      def _cmd_stats(self, args: List[str]) -> Dict[str, Any]:
          """stats — show entry count per category."""
          stats = self._store.stats()
          for category, count in stats.items():
              print(f"  {category}: {count}")
          return {"stats": stats}
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/memory/tests/test_agent.py -v
  ```
  Expected: all tests PASS

- [ ] **Step 5: Run the full memory test suite**

  ```
  pytest agents/memory/tests/ -v
  ```
  Expected: all tests PASS

- [ ] **Step 6: Commit**

  ```bash
  git add agents/memory/agent.py agents/memory/tests/test_agent.py
  git commit -m "feat(memory): implement MemoryAgent with subcommand dispatch"
  ```

---

## Task 7: Wire up — INTENT_MAP, registration, smoke test

**Files:**
- Modify: `agents/orchestrator/orchestrator.py` (2 lines)
- Modify: `main.py` (2 lines)

> **Note:** Two minimal changes to `orchestrator.py` are required: add `"memory"` to `INTENT_MAP` and update the dispatch logic to pass a full arg list when `kwarg_key == "args"`. This is necessary because existing agents receive only `args[0]`, but the memory agent needs the full list to dispatch subcommands internally.

- [ ] **Step 1: Update INTENT_MAP in orchestrator.py**

  Open `agents/orchestrator/orchestrator.py`. Find:

  ```python
  INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
      "audit": ("code_auditor", "target"),
      "fix":   ("code_fixer",   "target"),
  }
  ```

  Replace with:

  ```python
  INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
      "audit":  ("code_auditor", "target"),
      "fix":    ("code_fixer",   "target"),
      "memory": ("memory",       "args"),    # memory agent receives full arg list
  }
  ```

- [ ] **Step 2: Update dispatch logic in orchestrator.py**

  In the same file, find:

  ```python
          if kwarg_key and args:
              kwargs[kwarg_key] = args[0]
  ```

  Replace with:

  ```python
          if kwarg_key:
              # "args" means pass the full list; other keys take only the first element
              kwargs[kwarg_key] = args if kwarg_key == "args" else (args[0] if args else None)
  ```

- [ ] **Step 3: Verify existing orchestrator tests still pass**

  ```
  pytest agents/orchestrator/tests/test_orchestrator.py -v
  ```
  Expected: all tests PASS (the change is backwards-compatible — `audit` and `fix` still receive `args[0]`)

- [ ] **Step 4: Register MemoryAgent in main.py**

  Open `main.py`. Find:

  ```python
  from agents.orchestrator.agents.audit_agent import AuditAgent
  from agents.orchestrator.agents.fixer_agent import FixerAgent
  ```

  Add below it:

  ```python
  from agents.memory.agent import MemoryAgent
  ```

  Then find `build_registry()`:

  ```python
  def build_registry() -> AgentRegistry:
      """Register all known agents. Add new agents here."""
      registry = AgentRegistry()
      registry.register(AuditAgent)
      registry.register(FixerAgent)
      return registry
  ```

  Replace with:

  ```python
  def build_registry() -> AgentRegistry:
      """Register all known agents. Add new agents here."""
      registry = AgentRegistry()
      registry.register(AuditAgent)
      registry.register(FixerAgent)
      registry.register(MemoryAgent)
      return registry
  ```

- [ ] **Step 5: Verify memory agent appears in list**

  ```
  python main.py list
  ```

  Expected output includes:
  ```
    memory: Persistent memory and context store for the agent system
  ```

- [ ] **Step 6: Smoke test — add a memory**

  ```
  python main.py memory add decisions "We use FastAPI because it is async-native"
  ```

  Expected output:
  ```
  Memory stored [decisions]: <some-hex-id>
  ```

- [ ] **Step 7: Smoke test — query the memory**

  ```
  python main.py memory query "what framework do we use"
  ```

  Expected output includes:
  ```
  [decisions] We use FastAPI because it is async-native  (id: ...)
  ```

- [ ] **Step 8: Smoke test — list, stats, forget**

  ```
  python main.py memory list
  python main.py memory stats
  python main.py memory list decisions
  ```

  Verify output is sensible, no exceptions.

- [ ] **Step 9: Run the full test suite**

  ```
  pytest agents/ -v
  ```

  Expected: all tests PASS

- [ ] **Step 10: Commit**

  ```bash
  git add agents/orchestrator/orchestrator.py main.py
  git commit -m "feat(memory): wire MemoryAgent into INTENT_MAP and AgentRegistry"
  ```

---

## Quick Reference: CLI Usage After Implementation

```bash
python main.py memory add decisions "We use FastAPI because it is async-native"
python main.py memory add patterns "Services always return a Result type"
python main.py memory add preferences "Use snake_case for all variable names"
python main.py memory query "what web framework do we use"
python main.py memory list
python main.py memory list decisions
python main.py memory stats
python main.py memory forget <id>
python main.py memory export
```
