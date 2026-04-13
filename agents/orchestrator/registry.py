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

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore


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
