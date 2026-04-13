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

from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import AgentEvent


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
