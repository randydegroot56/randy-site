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
