import pytest
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent
from orchestrator.state import StateStore


class ConcreteAgent(BaseAgent):
    name = "test_agent"
    description = "A test agent"

    def run(self, **kwargs):
        return {"ran": True}


def make_agent(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = ConcreteAgent(bus=bus, state=state)
    return agent, bus, state


def test_get_name(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    assert agent.get_name() == "test_agent"


def test_run_returns_dict(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run()
    assert isinstance(result, dict)


def test_emit_publishes_to_bus(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("SomeEvent", received.append)

    event = AgentEvent(agent_name="test_agent", event_type="SomeEvent")
    agent.emit(event)

    assert len(received) == 1
    assert received[0] is event


def test_emit_stores_payload_in_state(tmp_path):
    agent, _, state = make_agent(tmp_path)
    event = AgentEvent(
        agent_name="test_agent",
        event_type="SomeEvent",
        payload={"result": "ok"},
    )
    agent.emit(event)

    assert state.get("last_SomeEvent") == {"result": "ok"}


def test_missing_name_raises_on_instantiation(tmp_path):
    class NoNameAgent(BaseAgent):
        name = ""
        description = "broken"

        def run(self, **kwargs):
            return {}

    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    with pytest.raises(ValueError, match="must define a non-empty `name`"):
        NoNameAgent(bus=bus, state=state)


def test_cannot_instantiate_base_agent_directly(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    with pytest.raises(TypeError):
        BaseAgent(bus=bus, state=state)
