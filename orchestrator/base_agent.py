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
