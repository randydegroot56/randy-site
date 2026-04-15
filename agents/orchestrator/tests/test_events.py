from agents.orchestrator.events import AgentEvent, AuditCompleted, AuditFailed, ContextProvided, FixCompleted, FixFailed, MemoryUpdated


def test_agent_event_defaults():
    event = AgentEvent(agent_name="test_agent")
    assert event.event_type == "AgentEvent"
    assert event.agent_name == "test_agent"
    assert event.status == "success"
    assert event.payload == {}
    assert event.error is None
    assert event.timestamp  # not empty string


def test_audit_completed_has_correct_event_type():
    event = AuditCompleted(agent_name="code_auditor", payload={"issues": 5})
    assert event.event_type == "AuditCompleted"
    assert event.payload == {"issues": 5}


def test_audit_failed_has_failed_status():
    event = AuditFailed(agent_name="code_auditor", error="disk full")
    assert event.event_type == "AuditFailed"
    assert event.status == "failed"
    assert event.error == "disk full"


def test_fix_completed_has_correct_event_type():
    event = FixCompleted(agent_name="code_fixer")
    assert event.event_type == "FixCompleted"


def test_fix_failed_has_failed_status():
    event = FixFailed(agent_name="code_fixer", error="no audit found")
    assert event.status == "failed"
    assert event.error == "no audit found"


def test_event_timestamp_is_iso_format():
    import re
    event = AgentEvent(agent_name="x")
    # ISO 8601: 2026-04-13T12:00:00.000000
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*\+00:00$", event.timestamp)


def test_payload_not_shared_between_instances():
    e1 = AgentEvent(agent_name="a")
    e2 = AgentEvent(agent_name="b")
    e1.payload["x"] = 1
    assert "x" not in e2.payload


def test_memory_updated_event():
    e = MemoryUpdated(agent_name="memory", payload={"entry_id": "abc"})
    assert e.event_type == "MemoryUpdated"
    assert e.status == "success"
    assert e.payload == {"entry_id": "abc"}


def test_context_provided_event():
    e = ContextProvided(agent_name="memory", payload={"query": "fastapi"})
    assert e.event_type == "ContextProvided"
    assert e.status == "success"
    assert e.payload == {"query": "fastapi"}


# ── Spec events ────────────────────────────────────────────────────────────────

def test_spec_created_event():
    from agents.orchestrator.events import SpecCreated
    e = SpecCreated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecCreated"
    assert e.status == "success"


def test_spec_validated_event():
    from agents.orchestrator.events import SpecValidated
    e = SpecValidated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecValidated"


def test_spec_updated_event():
    from agents.orchestrator.events import SpecUpdated
    e = SpecUpdated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecUpdated"


def test_spec_failed_event():
    from agents.orchestrator.events import SpecFailed
    e = SpecFailed(agent_name="spec", error="something went wrong")
    assert e.event_type == "SpecFailed"
    assert e.status == "failed"
