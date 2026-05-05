# Memory Agent — Design Spec

**Date:** 2026-04-14  
**Status:** Approved  
**Location:** `agents/memory/`

---

## Overview

The Memory Agent is the persistent memory layer of the multi-agent system. It stores project context, architectural decisions, and agent history, and delivers ranked, relevant context to other agents on demand. It integrates with the existing `EventBus`, `AgentRegistry`, `StateStore`, and `OrchestratorLogger` without modifying any of those components.

---

## Decisions Made During Design

| Question | Decision |
|---|---|
| CLI routing | Option A: `INTENT_MAP["memory"] = ("memory", "args")`, agent dispatches subcommands internally |
| MemoryIndexer extraction | C+A hybrid: always write event summary to `history`; optionally route specific event types to other categories via `EVENT_CATEGORY_MAP` |
| Relevance scoring | Substring matching (query words found as substrings in content + keywords) |
| Recency scoring | Linear decay: `max(0.0, 1 - age_days / horizon_days)`, horizon=365 days (configurable) |
| Structural approach | Flat module: `store.py`, `indexer.py`, `context_builder.py`, composed by `agent.py` |

---

## File Structure

```
agents/memory/
├── __init__.py
├── agent.py            ← MemoryAgent (BaseAgent subclass, subcommand dispatch)
├── store.py            ← MemoryStore (CRUD, pruning, JSON persistence)
├── indexer.py          ← MemoryIndexer (EventBus wildcard subscriber)
├── context_builder.py  ← ContextBuilder (query → ranked MemoryEntry list)
└── tests/
    ├── __init__.py
    ├── test_store.py
    ├── test_indexer.py
    ├── test_context_builder.py
    └── test_agent.py
```

---

## Data Model

Every memory entry is a `dict` with the following fields:

```python
{
    "id":                 "uuid4-hex",                    # unique identifier
    "timestamp":          "2026-04-14T10:23:00+00:00",   # ISO 8601 UTC
    "category":           "decisions",                    # one of 5 categories
    "content":            "We use FastAPI because...",    # human-readable fact
    "source":             "user:cli",                     # or "agent:code_auditor"
    "relevance_keywords": ["fastapi", "api", "choice"],   # lowercased list
    "pinned":             False                           # pinned entries survive pruning
}
```

**Categories:** `decisions`, `patterns`, `preferences`, `history`, `entities`

**Persistence path:** `~/.agent-orchestrator/memory/<category>.json`  
Each file is a JSON array of entries. Full array loaded on read; full array flushed on every write.

---

## Section 1: MemoryStore

**Responsibility:** CRUD operations, pruning, JSON persistence.

**Public API:**

```python
store = MemoryStore(base_dir=Path("~/.agent-orchestrator/memory"), max_size=500)

store.add(category, content, source, keywords=None, pinned=False) -> dict
store.get(entry_id) -> dict | None
store.delete(entry_id) -> bool
store.list(category=None) -> list[dict]
store.export() -> dict[str, list[dict]]
store.stats() -> dict[str, int]   # {category: count}
```

**Pruning:** When `len(entries) >= max_size`, the oldest unpinned entry is removed before inserting the new one. If all existing entries are pinned, the new entry is still inserted (max_size is a soft limit for unpinned entries).

**Persistence:** Each `add` and `delete` flushes the affected category file immediately. No lazy writes.

---

## Section 2: ContextBuilder

**Responsibility:** Score all entries against a query; return top N ranked results.

**Scoring formula:**

```
final_score(entry) = relevance(entry, query) × recency(entry)
```

**Relevance** — substring matching across `content` and `relevance_keywords`:
```python
query_words = set(query.lower().split())
search_text = entry["content"].lower() + " " + " ".join(entry["relevance_keywords"])
relevance = sum(1 for word in query_words if word in search_text)
```
Entries with `relevance == 0` are excluded entirely.

**Recency** — linear decay:
```python
age_days = (now_utc - parse_timestamp(entry["timestamp"])).days
recency = max(0.0, 1.0 - age_days / horizon_days)
```
Default `horizon_days=365` (configurable per call).

**Pinned override:** Pinned entries always appear first in results, regardless of score. They do not consume scored slots — the top `max_results` unpinned scored entries fill remaining slots.

**Public API:**

```python
builder = ContextBuilder(store)

builder.query(text, max_results=20, horizon_days=365) -> list[dict]
# Returns: pinned entries first, then scored entries desc, then timestamp desc as tiebreaker
```

---

## Section 3: MemoryIndexer

**Responsibility:** Listen to all bus events; auto-extract and store relevant facts.

**Construction:** `MemoryIndexer(bus, store)` — subscribes to `"*"` immediately on construction.

**Two-layer extraction:**

**Layer 1 — Always (every event):**
- Success: `content = f"{event.event_type} by {event.agent_name}"`
- Failure: `content = f"{event.event_type} by {event.agent_name} — ERROR: {event.error}"`
- Category: `history`
- Source: `f"agent:{event.agent_name}"`
- Keywords: `[event.event_type.lower(), event.agent_name.lower(), event.status]`

**Layer 2 — EVENT_CATEGORY_MAP (additive):**
```python
EVENT_CATEGORY_MAP: dict[str, tuple[str, Callable[[AgentEvent], str]]] = {
    "AuditCompleted": (
        "patterns",
        lambda e: f"Audit of {e.payload.get('target', '?')} found {e.payload.get('issues_found', '?')} issues"
    ),
    "FixCompleted": (
        "history",
        lambda e: f"Fix applied to {e.payload.get('target', '?')}"
    ),
}
```
If the event type matches, an additional entry is stored in the mapped category. The Layer 1 `history` entry is still written regardless.

**Feedback loop prevention:** Events of type `MemoryUpdated` and `ContextProvided` are ignored by the indexer.

**Publishes:** `MemoryUpdated` event after each successful store operation.

---

## Section 4: MemoryAgent

**Responsibility:** Subcommand dispatch; exposes memory operations to the CLI via the Orchestrator.

**Registration:**
```python
# In main.py build_registry():
from agents.memory.agent import MemoryAgent
registry.register(MemoryAgent)

# In orchestrator.py INTENT_MAP:
INTENT_MAP["memory"] = ("memory", "args")
```

**Class definition:**
```python
class MemoryAgent(BaseAgent):
    name = "memory"
    description = "Persistent memory and context store for the agent system"
```

**Construction:** `__init__` builds `MemoryStore`, `ContextBuilder`, `MemoryIndexer` internally after calling `super().__init__(bus, state)`.

**Subcommand dispatch:**

| Subcommand | Args | Behaviour |
|---|---|---|
| `add` | `[category, text]` | Store entry; publish `MemoryUpdated` |
| `query` | `[text]` | Return ranked entries; publish `ContextProvided` |
| `list` | `[category?]` | Return all entries, optionally filtered |
| `forget` | `[id]` | Delete by id; publish `MemoryUpdated` |
| `export` | `[]` | Return full export dict |
| `stats` | `[]` | Return `{category: count}` dict |

**Error handling:** Unknown subcommand raises `ValueError`. Missing required args raise `ValueError`. These propagate to `main.py`'s existing `except Exception` handler.

**New events** (added to `events.py`):
```python
@dataclass
class MemoryUpdated(AgentEvent):
    event_type: str = "MemoryUpdated"

@dataclass
class ContextProvided(AgentEvent):
    event_type: str = "ContextProvided"
```

---

## Section 5: Tests

All tests use `tmp_path` for file isolation — no writes to `~/.agent-orchestrator/`.

### `test_store.py`
- `add()` returns entry with correct fields (id, timestamp, category, source, pinned=False)
- `get()` retrieves by id; returns `None` for unknown id
- `delete()` removes entry and returns `True`; returns `False` for unknown id
- `list()` returns all entries; filtered correctly when category given
- `stats()` returns correct counts per category
- `export()` returns all five categories
- Pruning at `max_size=2`: adding 3rd unpinned entry removes oldest unpinned
- Pinned entries survive pruning when unpinned entries exist
- Persistence: data survives `MemoryStore` reconstruction from same path

### `test_context_builder.py`
- Query with matching keywords returns relevant entries
- Query with no matches returns empty list
- Results capped at `max_results`
- Pinned entries appear first regardless of score
- Recency decay: older entry scores lower than newer entry with equal keyword overlap
- Entries with relevance score 0 excluded from results

### `test_indexer.py`
- Successful event → summary stored in `history`
- Failed event → error message appended in `history` entry
- `AuditCompleted` → additional entry stored in `patterns` via `EVENT_CATEGORY_MAP`
- `MemoryUpdated` events not re-processed (no feedback loop)
- `ContextProvided` events not re-processed (no feedback loop)
- Indexer publishes `MemoryUpdated` event after storing

### `test_agent.py`
- Each valid subcommand routes to the correct internal method
- Unknown subcommand raises `ValueError`
- `add` with missing category or text raises `ValueError`
- `query` returns results and publishes `ContextProvided` event
- `forget` with unknown id returns `{"deleted": False}`

---

## Integration Checklist

- [ ] Add `MemoryUpdated` and `ContextProvided` to `agents/orchestrator/events.py`
- [ ] Register `MemoryAgent` in `main.py` `build_registry()`
- [ ] Add `"memory": ("memory", "args")` to `INTENT_MAP` in `orchestrator.py`
- [ ] Verify `python main.py memory add decisions "..."` works end-to-end
- [ ] Verify `python main.py memory query "..."` works end-to-end
