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

from agents.orchestrator.bus import EventBus
from agents.orchestrator.logger import OrchestratorLogger
from agents.orchestrator.registry import AgentRegistry
from agents.orchestrator.state import StateStore

# Maps CLI verb -> (agent_name, kwarg_key_for_first_positional_arg)
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":  ("code_auditor", "target"),
    "fix":    ("code_fixer",   "target"),
    "memory": ("memory",       "args"),    # memory agent receives full arg list
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
        if kwarg_key:
            # "args" means pass the full list; other keys take only the first element
            kwargs[kwarg_key] = args if kwarg_key == "args" else (args[0] if args else None)

        # For "fix": inject last audit result only when no explicit target was given
        if command == "fix" and not args:
            audit_result = self._state.get("last_AuditCompleted")
            if audit_result:
                kwargs.setdefault("audit_result", audit_result)

        agent = self._registry.get(agent_name, self._bus, self._state)
        return agent.run(**kwargs)

    def print_summary(self) -> None:
        print(self._logger.summary())
