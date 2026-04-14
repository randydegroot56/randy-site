"""Tests for agents.memory.indexer.MemoryIndexer."""
import pytest

from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import AgentEvent, AuditCompleted
from agents.memory.indexer import MemoryIndexer
from agents.memory.store import MemoryStore


def make_indexer(tmp_path):
    bus = EventBus()
    store = MemoryStore(base_dir=tmp_path / "memory")
    indexer = MemoryIndexer(bus, store)
    return bus, store, indexer


def test_successful_event_stored_in_history(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AgentEvent(agent_name="code_auditor", event_type="SomeEvent"))
    history = store.list(category="history")
    assert len(history) == 1
    assert "SomeEvent" in history[0]["content"]
    assert "code_auditor" in history[0]["content"]


def test_failed_event_includes_error_in_history(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AgentEvent(
        agent_name="code_auditor",
        event_type="AuditFailed",
        status="failed",
        error="Permission denied",
    ))
    history = store.list(category="history")
    assert len(history) == 1
    assert "ERROR: Permission denied" in history[0]["content"]


def test_audit_completed_also_stored_in_patterns(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AuditCompleted(
        agent_name="code_auditor",
        payload={"target": "./src", "issues_found": 5},
    ))
    history = store.list(category="history")
    patterns = store.list(category="patterns")
    assert len(history) == 1
    assert len(patterns) == 1
    assert "./src" in patterns[0]["content"]
    assert "5" in patterns[0]["content"]


def test_memory_updated_not_reprocessed(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AgentEvent(agent_name="memory", event_type="MemoryUpdated"))
    assert store.list(category="history") == []


def test_context_provided_not_reprocessed(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AgentEvent(agent_name="memory", event_type="ContextProvided"))
    assert store.list(category="history") == []


def test_indexer_publishes_memory_updated_after_storing(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    received = []
    bus.subscribe("MemoryUpdated", received.append)
    bus.publish(AgentEvent(agent_name="test_agent", event_type="SomeEvent"))
    assert len(received) >= 1
    assert received[0].event_type == "MemoryUpdated"


def test_source_is_agent_name(tmp_path):
    bus, store, _ = make_indexer(tmp_path)
    bus.publish(AgentEvent(agent_name="code_auditor", event_type="SomeEvent"))
    history = store.list(category="history")
    assert history[0]["source"] == "agent:code_auditor"
