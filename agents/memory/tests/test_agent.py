"""Tests for agents.memory.agent.MemoryAgent."""
import pytest

from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.memory.agent import MemoryAgent


def make_agent(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = MemoryAgent(bus=bus, state=state, memory_dir=tmp_path / "memory")
    return agent, bus, state


# --- dispatch ---

def test_unknown_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown memory subcommand 'bogus'"):
        agent.run(args=["bogus"])


def test_none_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown memory subcommand 'None'"):
        agent.run(args=[])


# --- add ---

def test_add_stores_entry(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["add", "decisions", "We use FastAPI"])
    assert "added" in result
    assert result["added"]["content"] == "We use FastAPI"
    assert result["added"]["category"] == "decisions"


def test_add_joins_multi_word_text(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["add", "decisions", "We", "use", "FastAPI"])
    assert result["added"]["content"] == "We use FastAPI"


def test_add_missing_text_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Usage: memory add"):
        agent.run(args=["add", "decisions"])   # category given, text missing


def test_add_missing_all_args_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Usage: memory add"):
        agent.run(args=["add"])


def test_add_publishes_memory_updated(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("MemoryUpdated", received.append)
    agent.run(args=["add", "decisions", "We use FastAPI"])
    # Filter out any MemoryUpdated events from other sources
    agent_events = [e for e in received if e.agent_name == "memory"]
    assert len(agent_events) >= 1
    assert agent_events[0].event_type == "MemoryUpdated"


# --- query ---

def test_query_returns_results(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["add", "decisions", "We use FastAPI for REST"])
    result = agent.run(args=["query", "fastapi"])
    assert "results" in result


def test_query_publishes_context_provided(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    agent.run(args=["add", "decisions", "We use FastAPI for REST"])
    received = []
    bus.subscribe("ContextProvided", received.append)
    agent.run(args=["query", "fastapi"])
    assert len(received) == 1
    assert received[0].event_type == "ContextProvided"


def test_query_missing_text_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Usage: memory query"):
        agent.run(args=["query"])


# --- list ---

def test_list_returns_entries(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["add", "decisions", "content A"])
    result = agent.run(args=["list"])
    assert "entries" in result
    assert len(result["entries"]) == 1


def test_list_filters_by_category(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["add", "decisions", "decision A"])
    agent.run(args=["add", "patterns", "pattern B"])
    result = agent.run(args=["list", "decisions"])
    assert len(result["entries"]) == 1
    assert result["entries"][0]["category"] == "decisions"


# --- forget ---

def test_forget_unknown_id_returns_false(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["forget", "no-such-id"])
    assert result == {"deleted": False}


def test_forget_known_id_returns_true(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    add_result = agent.run(args=["add", "decisions", "to be deleted"])
    entry_id = add_result["added"]["id"]
    result = agent.run(args=["forget", entry_id])
    assert result == {"deleted": True}


def test_forget_missing_id_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Usage: memory forget"):
        agent.run(args=["forget"])


# --- stats ---

def test_stats_returns_counts(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["add", "decisions", "A"])
    agent.run(args=["add", "decisions", "B"])
    result = agent.run(args=["stats"])
    assert result["stats"]["decisions"] == 2


# --- export ---

def test_export_returns_all_categories(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["export"])
    assert set(result.keys()) == {"decisions", "patterns", "preferences", "history", "entities"}
