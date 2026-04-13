from orchestrator.bus import EventBus
from orchestrator.events import AgentEvent, AuditCompleted


def test_subscribe_and_publish():
    bus = EventBus()
    received = []
    bus.subscribe("AuditCompleted", received.append)

    event = AuditCompleted(agent_name="auditor")
    bus.publish(event)

    assert len(received) == 1
    assert received[0] is event


def test_wildcard_receives_all_events():
    bus = EventBus()
    received = []
    bus.subscribe("*", received.append)

    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="b", event_type="TypeB"))

    assert len(received) == 2


def test_wildcard_and_specific_both_fire():
    bus = EventBus()
    wildcard_calls = []
    specific_calls = []
    bus.subscribe("*", wildcard_calls.append)
    bus.subscribe("AuditCompleted", specific_calls.append)

    bus.publish(AuditCompleted(agent_name="auditor"))

    assert len(wildcard_calls) == 1
    assert len(specific_calls) == 1


def test_no_handler_for_event_type_is_silent():
    bus = EventBus()
    # Should not raise even with no subscribers
    bus.publish(AgentEvent(agent_name="x", event_type="Unhandled"))


def test_multiple_handlers_same_event_all_called():
    bus = EventBus()
    calls = []
    bus.subscribe("AuditCompleted", lambda e: calls.append("h1"))
    bus.subscribe("AuditCompleted", lambda e: calls.append("h2"))

    bus.publish(AuditCompleted(agent_name="auditor"))

    assert calls == ["h1", "h2"]


def test_unsubscribed_event_type_does_not_receive():
    bus = EventBus()
    received = []
    bus.subscribe("AuditCompleted", received.append)

    bus.publish(AgentEvent(agent_name="x", event_type="OtherEvent"))

    assert received == []
