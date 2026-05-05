# Orchestrator Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python Agent Orchestrator Framework — a shared foundation that wraps existing agents (code_auditor, code_fixer) and future agents behind a common BaseAgent interface, event bus, state store, and top-level CLI.

**Architecture:** A new `orchestrator/` package provides the core primitives (BaseAgent, EventBus, StateStore, AgentRegistry, OrchestratorLogger, Orchestrator). Existing agents are wrapped as thin adapter classes inside `orchestrator/agents/`. The top-level `main.py` wires everything together and exposes a CLI: `python main.py audit ./src`.

**Tech Stack:** Python 3.10+, stdlib only (dataclasses, json, abc, argparse, asyncio-ready but sync for now), pytest for tests.

---

## File Map

```
orchestrator/
├── __init__.py               # Empty package marker
├── events.py                 # AgentEvent dataclass + concrete subtypes
├── bus.py                    # EventBus: subscribe/publish
├── state.py                  # StateStore: JSON-backed key-value
├── base_agent.py             # BaseAgent: ABC with run(), emit(), get_name()
├── registry.py               # AgentRegistry: register/get/list
├── logger.py                 # OrchestratorLogger: subscribes to *, formats output
├── orchestrator.py           # Orchestrator: intent resolution + dispatch
└── agents/
    ├── __init__.py           # Empty package marker
    ├── audit_agent.py        # AuditAgent wrapping code_auditor (stub for now)
    └── fixer_agent.py        # FixerAgent wrapping code_fixer (stub for now)

orchestrator/tests/
├── __init__.py
├── test_events.py
├── test_bus.py
├── test_state.py
├── test_base_agent.py
├── test_registry.py
├── test_logger.py
├── test_orchestrator.py
└── test_stub_agents.py

main.py                       # CLI entry point
HOW_TO_ADD_AGENT.md           # Developer guide (repo root, required by spec)
```

---

## Task 1: Package Skeletons

**Files:**
- Create: `orchestrator/__init__.py`
- Create: `orchestrator/agents/__init__.py`
- Create: `orchestrator/tests/__init__.py`

- [ ] **Step 1: Create the three `__init__.py` files**

```python
# orchestrator/__init__.py  (empty)
```

```python
# orchestrator/agents/__init__.py  (empty)
```

```python
# orchestrator/tests/__init__.py  (empty)
```

- [ ] **Step 2: Verify pytest is available**

Run: `python -m pytest --version`
Expected: `pytest X.Y.Z`

If missing: `pip install pytest`

- [ ] **Step 3: Commit**

```bash
git add orchestrator/__init__.py orchestrator/agents/__init__.py orchestrator/tests/__init__.py
git commit -m "feat(orchestrator): scaffold package directories"
```

---

## Task 2: Events Module

**Files:**
- Create: `orchestrator/events.py`
- Create: `orchestrator/tests/test_events.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_events.py`:
```python
from orchestrator.events import AgentEvent, AuditCompleted, AuditFailed, FixCompleted, FixFailed


def test_agent_event_defaults():
    event = AgentEvent(agent_name="test_agent")
    assert event.event_type == "AgentEvent"
    assert event.agent_name == "test_agent"
    assert event.status == "success"
    assert event.payload == {}
    assert event.error is None
    assert event.timestamp  # not empty string


def test_audit_completed_has_correct_event_type():
    event = AuditCompleted(agent_name="code_auditor", payload={"issues": 5})
    assert event.event_type == "AuditCompleted"
    assert event.payload == {"issues": 5}


def test_audit_failed_has_failed_status():
    event = AuditFailed(agent_name="code_auditor", error="disk full")
    assert event.event_type == "AuditFailed"
    assert event.status == "failed"
    assert event.error == "disk full"


def test_fix_completed_has_correct_event_type():
    event = FixCompleted(agent_name="code_fixer")
    assert event.event_type == "FixCompleted"


def test_fix_failed_has_failed_status():
    event = FixFailed(agent_name="code_fixer", error="no audit found")
    assert event.status == "failed"
    assert event.error == "no audit found"


def test_event_timestamp_is_iso_format():
    import re
    event = AgentEvent(agent_name="x")
    # ISO 8601: 2026-04-13T12:00:00.000000
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", event.timestamp)
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_events.py -v`
Expected: `ModuleNotFoundError` — `orchestrator.events` does not exist yet.

- [ ] **Step 3: Implement `orchestrator/events.py`**

```python
"""
orchestrator/events.py
======================
Event dataclasses for the agent event bus.

Field ordering rule: agent_name (required) comes first, then
event_type (has a default), then all other defaulted fields.
This allows subclasses to override event_type without breaking
Python dataclass ordering constraints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AgentEvent:
    """Base event emitted by any agent."""

    agent_name: str
    event_type: str = "AgentEvent"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"   # "success" | "failed" | "warning"
    error: Optional[str] = None


@dataclass
class AuditCompleted(AgentEvent):
    event_type: str = "AuditCompleted"


@dataclass
class AuditFailed(AgentEvent):
    event_type: str = "AuditFailed"
    status: str = "failed"


@dataclass
class FixCompleted(AgentEvent):
    event_type: str = "FixCompleted"


@dataclass
class FixFailed(AgentEvent):
    event_type: str = "FixFailed"
    status: str = "failed"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_events.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/events.py orchestrator/tests/test_events.py
git commit -m "feat(orchestrator): add AgentEvent dataclasses with concrete subtypes"
```

---

## Task 3: EventBus

**Files:**
- Create: `orchestrator/bus.py`
- Create: `orchestrator/tests/test_bus.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_bus.py`:
```python
from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent, AuditCompleted


def test_subscribe_and_publish():
    bus = EventBus()
    received = []
    bus.subscribe("AuditCompleted", received.append)

    event = AuditCompleted(agent_name="auditor")
    bus.publish(event)

    assert len(received) == 1
    assert received[0] is event


def test_wildcard_receives_all_events():
    bus = EventBus()
    received = []
    bus.subscribe("*", received.append)

    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="b", event_type="TypeB"))

    assert len(received) == 2


def test_wildcard_and_specific_both_fire():
    bus = EventBus()
    wildcard_calls = []
    specific_calls = []
    bus.subscribe("*", wildcard_calls.append)
    bus.subscribe("AuditCompleted", specific_calls.append)

    bus.publish(AuditCompleted(agent_name="auditor"))

    assert len(wildcard_calls) == 1
    assert len(specific_calls) == 1


def test_no_handler_for_event_type_is_silent():
    bus = EventBus()
    # Should not raise even with no subscribers
    bus.publish(AgentEvent(agent_name="x", event_type="Unhandled"))


def test_multiple_handlers_same_event_all_called():
    bus = EventBus()
    calls = []
    bus.subscribe("AuditCompleted", lambda e: calls.append("h1"))
    bus.subscribe("AuditCompleted", lambda e: calls.append("h2"))

    bus.publish(AuditCompleted(agent_name="auditor"))

    assert calls == ["h1", "h2"]


def test_unsubscribed_event_type_does_not_receive():
    bus = EventBus()
    received = []
    bus.subscribe("AuditCompleted", received.append)

    bus.publish(AgentEvent(agent_name="x", event_type="OtherEvent"))

    assert received == []
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_bus.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/bus.py`**

```python
"""
orchestrator/bus.py
===================
Synchronous pub/sub EventBus.

Subscribers register for a specific event_type or '*' (wildcard).
All wildcard subscribers fire BEFORE type-specific subscribers.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from orchestrator.events import AgentEvent

Handler = Callable[[AgentEvent], None]


class EventBus:
    """Synchronous event bus for agent communication."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = {}
        self._wildcard: List[Handler] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler. Use '*' to receive all events."""
        if event_type == "*":
            self._wildcard.append(handler)
        else:
            self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: AgentEvent) -> None:
        """Deliver event to all matching subscribers."""
        for handler in self._wildcard:
            handler(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_bus.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/bus.py orchestrator/tests/test_bus.py
git commit -m "feat(orchestrator): add synchronous EventBus with wildcard support"
```

---

## Task 4: StateStore

**Files:**
- Create: `orchestrator/state.py`
- Create: `orchestrator/tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_state.py`:
```python
import json
from orchestrator.state import StateStore


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
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_state.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/state.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_state.py -v`
Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/state.py orchestrator/tests/test_state.py
git commit -m "feat(orchestrator): add JSON-backed StateStore"
```

---

## Task 5: BaseAgent

**Files:**
- Create: `orchestrator/base_agent.py`
- Create: `orchestrator/tests/test_base_agent.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_base_agent.py`:
```python
import pytest
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent
from orchestrator.state import StateStore


class ConcreteAgent(BaseAgent):
    name = "test_agent"
    description = "A test agent"

    def run(self, **kwargs):
        return {"ran": True}


def make_agent(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = ConcreteAgent(bus=bus, state=state)
    return agent, bus, state


def test_get_name(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    assert agent.get_name() == "test_agent"


def test_run_returns_dict(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run()
    assert isinstance(result, dict)


def test_emit_publishes_to_bus(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("SomeEvent", received.append)

    event = AgentEvent(agent_name="test_agent", event_type="SomeEvent")
    agent.emit(event)

    assert len(received) == 1
    assert received[0] is event


def test_emit_stores_payload_in_state(tmp_path):
    agent, _, state = make_agent(tmp_path)
    event = AgentEvent(
        agent_name="test_agent",
        event_type="SomeEvent",
        payload={"result": "ok"},
    )
    agent.emit(event)

    assert state.get("last_SomeEvent") == {"result": "ok"}


def test_missing_name_raises_on_instantiation(tmp_path):
    class NoNameAgent(BaseAgent):
        name = ""
        description = "broken"

        def run(self, **kwargs):
            return {}

    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    with pytest.raises(ValueError, match="must define a non-empty `name`"):
        NoNameAgent(bus=bus, state=state)


def test_cannot_instantiate_base_agent_directly(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    with pytest.raises(TypeError):
        BaseAgent(bus=bus, state=state)
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_base_agent.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/base_agent.py`**

```python
"""
orchestrator/base_agent.py
==========================
Abstract base class for all Command Center agents.

To create a new agent:
1. Subclass BaseAgent
2. Set class attributes: name (unique str) and description (str)
3. Implement run(**kwargs) -> Dict[str, Any]
4. Call self.emit(event) to publish results to the bus
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent
from orchestrator.state import StateStore


class BaseAgent(ABC):
    """Abstract base for all agents. Subclasses must set `name` and implement `run`."""

    name: str = ""
    description: str = ""

    def __init__(self, bus: EventBus, state: StateStore) -> None:
        if not self.name:
            raise ValueError(
                f"{type(self).__name__} must define a non-empty `name` class attribute"
            )
        self._bus = bus
        self._state = state

    @abstractmethod
    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's primary task. Returns a result dict."""
        ...

    def emit(self, event: AgentEvent) -> None:
        """Publish an event to the bus and cache its payload in state."""
        self._bus.publish(event)
        self._state.set(f"last_{event.event_type}", event.payload)

    def get_name(self) -> str:
        return self.name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_base_agent.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/base_agent.py orchestrator/tests/test_base_agent.py
git commit -m "feat(orchestrator): add BaseAgent ABC with emit() and state integration"
```

---

## Task 6: AgentRegistry

**Files:**
- Create: `orchestrator/registry.py`
- Create: `orchestrator/tests/test_registry.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_registry.py`:
```python
import pytest
from orchestrator.registry import AgentRegistry
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.state import StateStore


class AlphaAgent(BaseAgent):
    name = "alpha"
    description = "Alpha agent"
    def run(self, **kwargs): return {}


class BetaAgent(BaseAgent):
    name = "beta"
    description = "Beta agent"
    def run(self, **kwargs): return {}


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


def test_register_and_list(tmp_path):
    registry = AgentRegistry()
    registry.register(AlphaAgent)
    assert "alpha" in registry.list_agents()
    assert registry.list_agents()["alpha"] == "Alpha agent"


def test_get_returns_correct_instance(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    agent = registry.get("alpha", bus, state)
    assert isinstance(agent, AlphaAgent)


def test_get_agent_has_bus_and_state(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    agent = registry.get("alpha", bus, state)
    assert agent._bus is bus
    assert agent._state is state


def test_get_unknown_agent_raises_key_error(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    with pytest.raises(KeyError, match="No agent 'missing'"):
        registry.get("missing", bus, state)


def test_get_error_message_lists_available_agents(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)
    registry.register(BetaAgent)

    with pytest.raises(KeyError, match="alpha"):
        registry.get("missing", bus, state)


def test_register_agent_without_name_raises(tmp_path):
    class UnnamedAgent(BaseAgent):
        name = ""
        description = "bad"
        def run(self, **kwargs): return {}

    registry = AgentRegistry()
    with pytest.raises(ValueError, match="has no name"):
        registry.register(UnnamedAgent)


def test_list_agents_returns_alphabetical_order(tmp_path):
    registry = AgentRegistry()
    registry.register(BetaAgent)
    registry.register(AlphaAgent)
    names = list(registry.list_agents())
    assert names == sorted(names)


def test_empty_registry_list_agents_returns_empty_dict():
    registry = AgentRegistry()
    assert registry.list_agents() == {}
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_registry.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/registry.py`**

```python
"""
orchestrator/registry.py
========================
AgentRegistry — discovers and instantiates agents by name.

Usage:
    registry = AgentRegistry()
    registry.register(MyAgent)           # register once at startup
    agent = registry.get("my_agent", bus, state)  # instantiate on demand
"""
from __future__ import annotations

from typing import Dict, Type

from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.state import StateStore


class AgentRegistry:
    """Maps agent names to agent classes. Instantiates on demand."""

    def __init__(self) -> None:
        self._classes: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class. The class must have a non-empty `name`."""
        if not agent_class.name:
            raise ValueError(
                f"Agent class {agent_class.__name__} has no name. "
                "Set a non-empty `name` class attribute."
            )
        self._classes[agent_class.name] = agent_class

    def get(self, name: str, bus: EventBus, state: StateStore) -> BaseAgent:
        """Instantiate and return a registered agent by name."""
        if name not in self._classes:
            available = ", ".join(sorted(self._classes))
            raise KeyError(f"No agent '{name}'. Available: {available or '(none)'}")
        return self._classes[name](bus=bus, state=state)

    def list_agents(self) -> Dict[str, str]:
        """Return {name: description} for all registered agents, sorted."""
        return {
            name: cls.description
            for name, cls in sorted(self._classes.items())
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_registry.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/registry.py orchestrator/tests/test_registry.py
git commit -m "feat(orchestrator): add AgentRegistry for agent discovery and instantiation"
```

---

## Task 7: OrchestratorLogger

**Files:**
- Create: `orchestrator/logger.py`
- Create: `orchestrator/tests/test_logger.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_logger.py`:
```python
import io
import json
from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent, AuditCompleted
from orchestrator.logger import OrchestratorLogger


def test_logger_prints_event_type_on_event():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="test_agent", event_type="TestEvent"))

    output = out.getvalue()
    assert "TestEvent" in output
    assert "test_agent" in output


def test_logger_prints_checkmark_for_success():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="E", status="success"))

    assert "✓" in out.getvalue()


def test_logger_prints_cross_for_failed():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="E", status="failed", error="oops"))

    output = out.getvalue()
    assert "✗" in output
    assert "oops" in output


def test_logger_writes_json_log_file(tmp_path):
    bus = EventBus()
    log_file = tmp_path / "log.json"
    out = io.StringIO()
    OrchestratorLogger(bus, log_file=log_file, stream=out)

    bus.publish(AuditCompleted(agent_name="auditor", payload={"issues": 3}))

    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["event_type"] == "AuditCompleted"
    assert entries[0]["payload"]["issues"] == 3


def test_logger_appends_to_existing_json_log(tmp_path):
    bus = EventBus()
    log_file = tmp_path / "log.json"
    out = io.StringIO()
    logger = OrchestratorLogger(bus, log_file=log_file, stream=out)

    bus.publish(AgentEvent(agent_name="a", event_type="First"))
    bus.publish(AgentEvent(agent_name="b", event_type="Second"))

    entries = json.loads(log_file.read_text())
    assert len(entries) == 2


def test_logger_summary_no_events():
    bus = EventBus()
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)
    assert logger.summary() == "No events recorded."


def test_logger_summary_counts_event_types():
    bus = EventBus()
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="b", event_type="TypeB"))

    summary = logger.summary()
    assert "TypeA: 2" in summary
    assert "TypeB: 1" in summary


def test_logger_verbose_prints_payload_keys():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, verbose=True, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="Ev", payload={"mykey": "myval"}))

    output = out.getvalue()
    assert "mykey" in output
    assert "myval" in output


def test_logger_non_verbose_does_not_print_payload():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, verbose=False, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="Ev", payload={"secret": "hidden"}))

    assert "secret" not in out.getvalue()
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_logger.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/logger.py`**

```python
"""
orchestrator/logger.py
======================
OrchestratorLogger — subscribes to all bus events and logs them.

Terminal output: timestamped line with ✓/✗ icon.
JSON log file: append-only, one entry per event.
summary(): human-readable count of events by type.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional, TextIO

from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent


class OrchestratorLogger:
    """Subscribes to all events; logs to terminal and optionally to a JSON file."""

    def __init__(
        self,
        bus: EventBus,
        log_file: Optional[Path] = None,
        verbose: bool = False,
        stream: TextIO = sys.stdout,
    ) -> None:
        self._log_file = Path(log_file) if log_file else None
        self._verbose = verbose
        self._stream = stream
        self._events: List[AgentEvent] = []
        bus.subscribe("*", self._handle)

    def _handle(self, event: AgentEvent) -> None:
        self._events.append(event)
        self._print_terminal(event)
        if self._log_file:
            self._append_json(event)

    def _print_terminal(self, event: AgentEvent) -> None:
        icon = "✓" if event.status == "success" else "✗"
        line = f"[{event.timestamp}] {icon} [{event.agent_name}] {event.event_type}"
        if event.error:
            line += f" — ERROR: {event.error}"
        print(line, file=self._stream)
        if self._verbose and event.payload:
            for k, v in event.payload.items():
                print(f"    {k}: {v}", file=self._stream)

    def _append_json(self, event: AgentEvent) -> None:
        try:
            existing = (
                json.loads(self._log_file.read_text(encoding="utf-8"))
                if self._log_file.exists()
                else []
            )
        except (json.JSONDecodeError, OSError):
            existing = []
        entry = {
            "timestamp": event.timestamp,
            "agent": event.agent_name,
            "event_type": event.event_type,
            "status": event.status,
            "payload": event.payload,
            "error": event.error,
        }
        existing.append(entry)
        self._log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def summary(self) -> str:
        """Return a human-readable count of all events by type."""
        if not self._events:
            return "No events recorded."
        counts: dict[str, int] = {}
        errors: list[str] = []
        for e in self._events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
            if e.error:
                errors.append(f"  {e.agent_name}: {e.error}")
        lines = ["=== Session Summary ==="]
        for event_type, count in sorted(counts.items()):
            lines.append(f"  {event_type}: {count}")
        if errors:
            lines.append("Errors:")
            lines.extend(errors)
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_logger.py -v`
Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/logger.py orchestrator/tests/test_logger.py
git commit -m "feat(orchestrator): add OrchestratorLogger with terminal and JSON output"
```

---

## Task 8: Orchestrator (Intent Resolution + Dispatch)

**Files:**
- Create: `orchestrator/orchestrator.py`
- Create: `orchestrator/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_orchestrator.py`:
```python
import io
import pytest
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.events import AuditCompleted
from orchestrator.logger import OrchestratorLogger
from orchestrator.orchestrator import Orchestrator
from orchestrator.registry import AgentRegistry
from orchestrator.state import StateStore


class EchoAuditAgent(BaseAgent):
    """Test double: echoes target back in result."""
    name = "code_auditor"
    description = "Echo audit for testing"

    def run(self, target=".", **kwargs):
        result = {"target": target, "issues_found": 0}
        self.emit(AuditCompleted(agent_name=self.name, payload=result))
        return result


class EchoFixAgent(BaseAgent):
    """Test double: records whether audit_result was received."""
    name = "code_fixer"
    description = "Echo fixer for testing"

    def run(self, target=".", audit_result=None, **kwargs):
        from orchestrator.events import FixCompleted
        result = {"target": target, "audit_result_received": audit_result is not None}
        self.emit(FixCompleted(agent_name=self.name, payload=result))
        return result


def make_orch(tmp_path, agents=None):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)
    registry = AgentRegistry()
    for cls in (agents or [EchoAuditAgent, EchoFixAgent]):
        registry.register(cls)
    orch = Orchestrator(registry, bus, state, logger)
    return orch, state, logger


def test_run_audit_dispatches_to_code_auditor(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    result = orch.run("audit", ["./src"])
    assert result["target"] == "./src"


def test_run_audit_stores_result_in_state(tmp_path):
    orch, state, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    stored = state.get("last_AuditCompleted")
    assert stored is not None
    assert stored["target"] == "./src"


def test_run_fix_after_audit_passes_audit_result(tmp_path):
    orch, state, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    result = orch.run("fix", [])
    assert result["audit_result_received"] is True


def test_run_fix_with_explicit_target(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    result = orch.run("fix", ["./src"])
    assert result["target"] == "./src"


def test_run_unknown_command_raises_value_error(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    with pytest.raises(ValueError, match="Unknown command 'unknown'"):
        orch.run("unknown", [])


def test_run_unknown_command_error_lists_available(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    with pytest.raises(ValueError, match="audit"):
        orch.run("unknown", [])


def test_print_summary_calls_logger_summary(tmp_path, capsys):
    orch, _, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    orch.print_summary()
    captured = capsys.readouterr()
    assert "AuditCompleted" in captured.out
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_orchestrator.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/orchestrator.py`**

```python
"""
orchestrator/orchestrator.py
=============================
Orchestrator — parses user commands and dispatches to the correct agent.

INTENT_MAP ties CLI verbs to agent names. To add a new command:
    INTENT_MAP["scrape"] = ("web_scraper", "url")

The fix command automatically pulls the last audit result from state
so the user can run "audit ./src" then "fix" without repeating the path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from orchestrator.bus import EventBus
from orchestrator.logger import OrchestratorLogger
from orchestrator.registry import AgentRegistry
from orchestrator.state import StateStore

# Maps CLI verb -> (agent_name, kwarg_key_for_first_positional_arg)
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit": ("code_auditor", "target"),
    "fix":   ("code_fixer",   "target"),
}


class Orchestrator:
    """Routes CLI commands to registered agents."""

    def __init__(
        self,
        registry: AgentRegistry,
        bus: EventBus,
        state: StateStore,
        logger: OrchestratorLogger,
    ) -> None:
        self._registry = registry
        self._bus = bus
        self._state = state
        self._logger = logger

    def run(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Resolve intent and run the matching agent."""
        if command not in INTENT_MAP:
            available = ", ".join(sorted(INTENT_MAP))
            raise ValueError(
                f"Unknown command '{command}'. Available: {available}"
            )

        agent_name, kwarg_key = INTENT_MAP[command]
        kwargs: Dict[str, Any] = {}

        # Map first positional arg to the agent's expected kwarg
        if kwarg_key and args:
            kwargs[kwarg_key] = args[0]

        # For "fix": if no target given and a previous audit exists, inject it
        if command == "fix":
            audit_result = self._state.get("last_AuditCompleted")
            if audit_result:
                kwargs.setdefault("audit_result", audit_result)

        agent = self._registry.get(agent_name, self._bus, self._state)
        return agent.run(**kwargs)

    def print_summary(self) -> None:
        print(self._logger.summary())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_orchestrator.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add orchestrator/orchestrator.py orchestrator/tests/test_orchestrator.py
git commit -m "feat(orchestrator): add Orchestrator with intent resolution and audit→fix context passing"
```

---

## Task 9: Stub Agents (AuditAgent + FixerAgent)

**Files:**
- Create: `orchestrator/agents/audit_agent.py`
- Create: `orchestrator/agents/fixer_agent.py`
- Create: `orchestrator/tests/test_stub_agents.py`

- [ ] **Step 1: Write the failing tests**

`orchestrator/tests/test_stub_agents.py`:
```python
import pytest
from orchestrator.agents.audit_agent import AuditAgent
from orchestrator.agents.fixer_agent import FixerAgent
from orchestrator.bus import EventBus
from orchestrator.state import StateStore


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


# ----- AuditAgent -----

def test_audit_agent_name():
    assert AuditAgent.name == "code_auditor"


def test_audit_agent_run_returns_dict_with_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"
    assert "status" in result


def test_audit_agent_run_default_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    result = agent.run()
    assert result["target"] == "."


def test_audit_agent_emits_audit_completed(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("AuditCompleted", received.append)

    agent = AuditAgent(bus=bus, state=state)
    agent.run(target="./src")

    assert len(received) == 1
    assert received[0].agent_name == "code_auditor"


def test_audit_agent_stores_result_in_state(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    agent.run(target="./src")

    stored = state.get("last_AuditCompleted")
    assert stored is not None
    assert stored["target"] == "./src"


# ----- FixerAgent -----

def test_fixer_agent_name():
    assert FixerAgent.name == "code_fixer"


def test_fixer_agent_run_returns_dict_with_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"


def test_fixer_agent_run_default_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run()
    assert result["target"] == "."


def test_fixer_agent_detects_audit_result(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run(audit_result={"issues_found": 5})
    assert result["audit_result_received"] is True


def test_fixer_agent_handles_no_audit_result(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run()
    assert result["audit_result_received"] is False


def test_fixer_agent_emits_fix_completed(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("FixCompleted", received.append)

    agent = FixerAgent(bus=bus, state=state)
    agent.run()

    assert len(received) == 1
    assert received[0].agent_name == "code_fixer"
```

- [ ] **Step 2: Run to verify tests fail**

Run: `python -m pytest orchestrator/tests/test_stub_agents.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `orchestrator/agents/audit_agent.py`**

```python
"""
orchestrator/agents/audit_agent.py
====================================
AuditAgent — adapter for the Code Auditor.

Current implementation: stub that proves the framework plumbing works.
Real implementation: invoke agents.code_auditor.cli subcommands via
subprocess or direct Python import.
"""
from __future__ import annotations

from typing import Any, Dict

from orchestrator.base_agent import BaseAgent
from orchestrator.events import AuditCompleted, AuditFailed


class AuditAgent(BaseAgent):
    name = "code_auditor"
    description = "Audits a target directory for unused code and quality issues"

    def run(self, target: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            # TODO: replace stub with real call:
            # from agents.code_auditor.cli import cmd_discover
            result: Dict[str, Any] = {
                "target": target,
                "issues_found": 0,
                "status": "stub",
            }
            self.emit(AuditCompleted(agent_name=self.name, payload=result))
            return result
        except Exception as exc:
            self.emit(AuditFailed(agent_name=self.name, error=str(exc)))
            raise
```

- [ ] **Step 4: Implement `orchestrator/agents/fixer_agent.py`**

```python
"""
orchestrator/agents/fixer_agent.py
=====================================
FixerAgent — adapter for the Code Fixer.

Current implementation: stub that proves the framework plumbing works.
Real implementation: invoke agents.code_fixer.cli subcommands via
subprocess or direct Python import.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from orchestrator.base_agent import BaseAgent
from orchestrator.events import FixCompleted, FixFailed


class FixerAgent(BaseAgent):
    name = "code_fixer"
    description = "Applies fixes from a previous audit result to the codebase"

    def run(
        self,
        target: str = ".",
        audit_result: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            # TODO: replace stub with real call:
            # from agents.code_fixer.cli import cmd_fix
            result: Dict[str, Any] = {
                "target": target,
                "fixes_applied": 0,
                "audit_result_received": audit_result is not None,
                "status": "stub",
            }
            self.emit(FixCompleted(agent_name=self.name, payload=result))
            return result
        except Exception as exc:
            self.emit(FixFailed(agent_name=self.name, error=str(exc)))
            raise
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest orchestrator/tests/test_stub_agents.py -v`
Expected: 11 PASSED

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest orchestrator/tests/ -v`
Expected: All PASSED (no failures)

- [ ] **Step 7: Commit**

```bash
git add orchestrator/agents/audit_agent.py orchestrator/agents/fixer_agent.py orchestrator/tests/test_stub_agents.py
git commit -m "feat(orchestrator): add AuditAgent and FixerAgent stubs with full event integration"
```

---

## Task 10: main.py CLI Entry Point

**Files:**
- Create: `main.py`

No tests for main.py — it is thin wiring code. Tested manually with the smoke test below.

- [ ] **Step 1: Implement `main.py`**

```python
#!/usr/bin/env python3
"""
main.py — AI Command Center entry point.

Usage::
    python main.py list                  # Show all registered agents
    python main.py audit ./src           # Run Code Auditor on ./src
    python main.py audit ./src -v        # Verbose: show event payloads
    python main.py fix ./src             # Run Code Fixer on ./src
    python main.py fix                   # Fix using last audit result from state
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is importable when run as `python main.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator.agents.audit_agent import AuditAgent
from orchestrator.agents.fixer_agent import FixerAgent
from orchestrator.bus import EventBus
from orchestrator.logger import OrchestratorLogger
from orchestrator.orchestrator import Orchestrator
from orchestrator.registry import AgentRegistry
from orchestrator.state import StateStore


def build_registry() -> AgentRegistry:
    """Register all known agents. Add new agents here."""
    registry = AgentRegistry()
    registry.register(AuditAgent)
    registry.register(FixerAgent)
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="AI Command Center — orchestrate your agents",
    )
    parser.add_argument("command", help="Command to run: audit | fix | list")
    parser.add_argument("args", nargs="*", help="Arguments (e.g. ./src)")
    parser.add_argument(
        "--log-file",
        default=".orchestrator_log.json",
        help="Path for JSON event log (default: .orchestrator_log.json)",
    )
    parser.add_argument(
        "--state-file",
        default=".orchestrator_state.json",
        help="Path for state file (default: .orchestrator_state.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print event payloads")
    parsed = parser.parse_args()

    bus = EventBus()
    state = StateStore(Path(parsed.state_file))
    logger = OrchestratorLogger(
        bus,
        log_file=Path(parsed.log_file),
        verbose=parsed.verbose,
    )
    registry = build_registry()
    orch = Orchestrator(registry, bus, state, logger)

    if parsed.command == "list":
        print("Registered agents:")
        for name, desc in registry.list_agents().items():
            print(f"  {name}: {desc}")
        return 0

    try:
        orch.run(parsed.command, parsed.args)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        orch.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke test — verify the CLI runs end-to-end**

Run: `python main.py list`

Expected output (exact names may vary):
```
Registered agents:
  code_auditor: Audits a target directory for unused code and quality issues
  code_fixer: Applies fixes from a previous audit result to the codebase
```

- [ ] **Step 3: Smoke test — audit command**

Run: `python main.py audit ./src -v`

Expected output contains:
```
[2026-...] ✓ [code_auditor] AuditCompleted
    target: ./src
    issues_found: 0
    status: stub
=== Session Summary ===
  AuditCompleted: 1
```

- [ ] **Step 4: Smoke test — fix after audit (context passing)**

Run:
```bash
python main.py audit ./src
python main.py fix
```

Second command should include `audit_result_received: True` in its output.

- [ ] **Step 5: Verify JSON log was created**

Run: `python -c "import json; print(json.load(open('.orchestrator_log.json'))[-1]['event_type'])"`
Expected: `FixCompleted`

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(orchestrator): add main.py CLI entry point with audit/fix/list commands"
```

---

## Task 11: HOW_TO_ADD_AGENT.md

**Files:**
- Create: `HOW_TO_ADD_AGENT.md`

- [ ] **Step 1: Create the guide**

`HOW_TO_ADD_AGENT.md`:
```markdown
# How to Add a New Agent

Adding an agent to the Command Center takes **4 steps**.
When you're done, `python main.py <your-command> <args>` will work.

---

## Step 1 — Create your agent file

Create `orchestrator/agents/my_agent.py`:

```python
from __future__ import annotations
from typing import Any, Dict
from orchestrator.base_agent import BaseAgent
from orchestrator.events import AgentEvent


# Define your agent's events (optional — use AgentEvent directly if you prefer)
from dataclasses import dataclass

@dataclass
class MyTaskCompleted(AgentEvent):
    event_type: str = "MyTaskCompleted"

@dataclass
class MyTaskFailed(AgentEvent):
    event_type: str = "MyTaskFailed"
    status: str = "failed"


class MyAgent(BaseAgent):
    name = "my_agent"                              # unique, snake_case
    description = "One sentence about what it does"

    def run(self, target: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            # Your logic here
            result = {"target": target, "status": "success"}
            self.emit(MyTaskCompleted(agent_name=self.name, payload=result))
            return result
        except Exception as exc:
            self.emit(MyTaskFailed(agent_name=self.name, error=str(exc)))
            raise
```

Rules:
- `name` must be unique across all agents (the registry key)
- `run()` must return a `Dict[str, Any]`
- Call `self.emit(event)` to publish results — this writes to the bus AND state automatically
- `self._state.get("last_AuditCompleted")` to read a previous agent's output

---

## Step 2 — Register the agent in main.py

Open `main.py`, find `build_registry()`, add one line:

```python
from orchestrator.agents.my_agent import MyAgent   # add import at top

def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(AuditAgent)
    registry.register(FixerAgent)
    registry.register(MyAgent)    # <-- add this
    return registry
```

---

## Step 3 — Add a CLI command (optional)

If your agent should be invocable directly from the CLI, add it to `INTENT_MAP` in `orchestrator/orchestrator.py`:

```python
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":    ("code_auditor", "target"),
    "fix":      ("code_fixer",   "target"),
    "my-task":  ("my_agent",     "target"),   # <-- add this
}
```

Now `python main.py my-task ./src` works.

---

## Step 4 — Write tests

Create `orchestrator/tests/test_my_agent.py`:

```python
from orchestrator.agents.my_agent import MyAgent
from orchestrator.bus import EventBus
from orchestrator.state import StateStore


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


def test_my_agent_name():
    assert MyAgent.name == "my_agent"


def test_my_agent_run_returns_dict(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = MyAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"


def test_my_agent_emits_completed_event(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("MyTaskCompleted", received.append)

    agent = MyAgent(bus=bus, state=state)
    agent.run(target="./src")

    assert len(received) == 1
    assert received[0].agent_name == "my_agent"
```

Run: `python -m pytest orchestrator/tests/test_my_agent.py -v`

---

## That's it

Verify end-to-end:

```bash
python main.py list              # my_agent should appear
python main.py my-task ./src     # runs your agent, logs event
```

The logger automatically captures your events. The state store automatically
saves `last_MyTaskCompleted` so other agents can read it.
```

- [ ] **Step 2: Commit**

```bash
git add HOW_TO_ADD_AGENT.md
git commit -m "docs(orchestrator): add HOW_TO_ADD_AGENT developer guide"
```

---

## Final Verification

- [ ] **Run the full test suite**

Run: `python -m pytest orchestrator/tests/ -v`
Expected: All tests PASSED, 0 failures

- [ ] **Verify CLI smoke test**

Run:
```bash
python main.py list
python main.py audit ./src -v
python main.py fix -v
```

Verify:
1. `list` shows both agents
2. `audit` prints `✓ [code_auditor] AuditCompleted` and summary
3. `fix` prints `audit_result_received: True` (context was passed from state)

- [ ] **Final commit**

```bash
git add .
git commit -m "feat(orchestrator): complete agent orchestrator framework — base, registry, bus, state, logger, orchestrator, stubs, CLI"
```
