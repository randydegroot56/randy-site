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
