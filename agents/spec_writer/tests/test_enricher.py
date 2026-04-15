"""Tests for agents.spec_writer.enricher.SpecEnricher."""
import pytest
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.spec_writer.enricher import SpecEnricher
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc


class FakeMemoryAgent:
    name = "memory"

    def run(self, args=None, **kwargs):
        return {
            "results": [
                {"category": "patterns",   "content": "Use repository pattern"},
                {"category": "decisions",  "content": "We use FastAPI for REST"},
            ]
        }


class FakeRegistry:
    def __init__(self, has_memory=True):
        self._has_memory = has_memory

    def get(self, name, bus, state, **kwargs):
        if name == "memory" and self._has_memory:
            return FakeMemoryAgent()
        raise KeyError(f"No agent '{name}'")


def make_spec() -> SpecDoc:
    return SpecDoc(
        spec_id="spec_20260415_001",
        project=ProjectSection(name="TestApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in")],
    )


def test_enrich_fills_patterns_used(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(make_spec())
    assert "Use repository pattern" in spec.context_applied.patterns_used


def test_enrich_fills_decisions_referenced(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(make_spec())
    assert "We use FastAPI for REST" in spec.context_applied.decisions_referenced


def test_enrich_without_memory_agent_adds_warning(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(has_memory=False), bus, state).enrich(make_spec())
    assert any("MemoryAgent" in w or "memory" in w.lower() for w in spec.warnings)


def test_enrich_without_registry_adds_warning(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(None, bus, state).enrich(make_spec())
    assert any("registry" in w.lower() for w in spec.warnings)


def test_enrich_does_not_raise_on_empty_spec(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(SpecDoc())
    assert spec is not None
