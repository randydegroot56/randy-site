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
    "audit":    ("code_auditor", "target"),
    "fix":      ("code_fixer",   "target"),
    "memory":   ("memory",       "args"),    # memory agent receives full arg list
    "spec":     ("spec",         "args"),    # spec agent receives full arg list
    "test":     ("testgen",      "args"),    # test generator receives full arg list
    "scaffold": ("scaffold",     "args"),    # scaffolder agent receives full arg list
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
            if kwarg_key == "args":
                # Memory agent receives the full argument list
                kwargs[kwarg_key] = args
            elif args:
                # All other agents receive only the first positional argument
                kwargs[kwarg_key] = args[0]
            # When kwarg_key is set but args is empty, leave kwargs empty
            # so the agent can use its own parameter default (e.g. target=".")

        # For "fix": inject last audit result only when no explicit target was given
        if command == "fix" and not args:
            audit_result = self._state.get("last_AuditCompleted")
            if audit_result:
                kwargs.setdefault("audit_result", audit_result)

        extra: Dict[str, Any] = {}
        if command == "spec":
            extra["registry"] = self._registry
        if command == "test":
            extra["registry"] = self._registry
        if command == "scaffold":
            extra["registry"] = self._registry

        agent = self._registry.get(agent_name, self._bus, self._state, **extra)
        return agent.run(**kwargs)

    def print_summary(self) -> None:
        print(self._logger.summary())
