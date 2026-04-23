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


@dataclass
class MemoryUpdated(AgentEvent):
    event_type: str = "MemoryUpdated"


@dataclass
class ContextProvided(AgentEvent):
    event_type: str = "ContextProvided"


@dataclass
class SpecCreated(AgentEvent):
    event_type: str = "SpecCreated"


@dataclass
class SpecValidated(AgentEvent):
    event_type: str = "SpecValidated"


@dataclass
class SpecUpdated(AgentEvent):
    event_type: str = "SpecUpdated"


@dataclass
class SpecFailed(AgentEvent):
    event_type: str = "SpecFailed"
    status: str = "failed"


@dataclass
class TestsGenerated(AgentEvent):
    event_type: str = "TestsGenerated"


@dataclass
class TestsPassed(AgentEvent):
    event_type: str = "TestsPassed"


@dataclass
class TestsFailed(AgentEvent):
    event_type: str = "TestsFailed"
    status: str = "failed"


@dataclass
class CoverageReport(AgentEvent):
    event_type: str = "CoverageReport"


@dataclass
class ScaffoldCompleted(AgentEvent):
    event_type: str = "ScaffoldCompleted"


@dataclass
class ScaffoldFailed(AgentEvent):
    event_type: str = "ScaffoldFailed"
    status: str = "failed"


@dataclass
class ScaffoldCleaned(AgentEvent):
    event_type: str = "ScaffoldCleaned"
