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
        """Initialise the MemoryAgent and subscribe the MemoryIndexer to the bus.

        Args:
            bus: EventBus for publishing MemoryUpdated and ContextProvided events.
            state: StateStore for persisting last event payloads (via BaseAgent).
            memory_dir: Directory for JSON memory files.
                        Defaults to ~/.agent-orchestrator/memory/.
        """
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
        """list [category] — show stored memories, optionally filtered by category."""
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
