"""
agents/spec_writer/enricher.py
================================
SpecEnricher — queries the MemoryAgent via AgentRegistry to add project context.

enrich(spec) -> SpecDoc with context_applied populated.
Never raises — missing registry or MemoryAgent produces a warning.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from agents.spec_writer.schema import SpecDoc

if TYPE_CHECKING:
    from agents.orchestrator.bus import EventBus
    from agents.orchestrator.registry import AgentRegistry
    from agents.orchestrator.state import StateStore


class SpecEnricher:
    """Enriches a SpecDoc with context from the MemoryAgent via AgentRegistry."""

    def __init__(
        self,
        registry: Optional["AgentRegistry"],
        bus: "EventBus",
        state: "StateStore",
    ) -> None:
        self._registry = registry
        self._bus = bus
        self._state = state

    def enrich(self, spec: SpecDoc) -> SpecDoc:
        if self._registry is None:
            spec.warnings.append("No registry provided — context enrichment skipped")
            return spec

        try:
            agent = self._registry.get("memory", self._bus, self._state)
        except KeyError:
            spec.warnings.append("MemoryAgent not registered — context enrichment skipped")
            return spec

        query = self._build_query(spec)
        if not query:
            return spec

        try:
            result = agent.run(args=["query", query])
        except Exception as exc:
            spec.warnings.append(f"Memory query failed: {exc}")
            return spec

        for entry in result.get("results", []):
            category = entry.get("category", "")
            content = entry.get("content", "")
            if not content:
                continue
            if category == "patterns":
                spec.context_applied.patterns_used.append(content)
            elif category == "decisions":
                spec.context_applied.decisions_referenced.append(content)

        return spec

    def _build_query(self, spec: SpecDoc) -> str:
        parts = [
            spec.project.language,
            spec.project.framework,
            spec.project.type,
            *(f.description for f in spec.features[:3]),
        ]
        return " ".join(p for p in parts if p and p != "TODO")
