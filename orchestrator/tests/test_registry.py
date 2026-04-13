import pytest
from orchestrator.registry import AgentRegistry
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.state import StateStore


class AlphaAgent(BaseAgent):
    name = "alpha"
    description = "Alpha agent"
    def run(self, **kwargs): return {}


class BetaAgent(BaseAgent):
    name = "beta"
    description = "Beta agent"
    def run(self, **kwargs): return {}


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


def test_register_and_list(tmp_path):
    registry = AgentRegistry()
    registry.register(AlphaAgent)
    assert "alpha" in registry.list_agents()
    assert registry.list_agents()["alpha"] == "Alpha agent"


def test_get_returns_correct_instance(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    agent = registry.get("alpha", bus, state)
    assert isinstance(agent, AlphaAgent)


def test_get_agent_has_bus_and_state(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    agent = registry.get("alpha", bus, state)
    assert agent._bus is bus
    assert agent._state is state


def test_get_unknown_agent_raises_key_error(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)

    with pytest.raises(KeyError, match="No agent 'missing'"):
        registry.get("missing", bus, state)


def test_get_error_message_lists_available_agents(tmp_path):
    bus, state = make_deps(tmp_path)
    registry = AgentRegistry()
    registry.register(AlphaAgent)
    registry.register(BetaAgent)

    with pytest.raises(KeyError, match="alpha"):
        registry.get("missing", bus, state)


def test_register_agent_without_name_raises(tmp_path):
    class UnnamedAgent(BaseAgent):
        name = ""
        description = "bad"
        def run(self, **kwargs): return {}

    registry = AgentRegistry()
    with pytest.raises(ValueError, match="has no name"):
        registry.register(UnnamedAgent)


def test_list_agents_returns_alphabetical_order(tmp_path):
    registry = AgentRegistry()
    registry.register(BetaAgent)
    registry.register(AlphaAgent)
    names = list(registry.list_agents())
    assert names == sorted(names)


def test_empty_registry_list_agents_returns_empty_dict():
    registry = AgentRegistry()
    assert registry.list_agents() == {}
