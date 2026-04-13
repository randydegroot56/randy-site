import io
import json
from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import AgentEvent, AuditCompleted
from agents.orchestrator.logger import OrchestratorLogger


def test_logger_prints_event_type_on_event():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="test_agent", event_type="TestEvent"))

    output = out.getvalue()
    assert "TestEvent" in output
    assert "test_agent" in output


def test_logger_prints_checkmark_for_success():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="E", status="success"))

    assert "✓" in out.getvalue()


def test_logger_prints_cross_for_failed():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="E", status="failed", error="oops"))

    output = out.getvalue()
    assert "✗" in output
    assert "oops" in output


def test_logger_writes_json_log_file(tmp_path):
    bus = EventBus()
    log_file = tmp_path / "log.json"
    out = io.StringIO()
    OrchestratorLogger(bus, log_file=log_file, stream=out)

    bus.publish(AuditCompleted(agent_name="auditor", payload={"issues": 3}))

    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["event_type"] == "AuditCompleted"
    assert entries[0]["payload"]["issues"] == 3


def test_logger_appends_to_existing_json_log(tmp_path):
    bus = EventBus()
    log_file = tmp_path / "log.json"
    out = io.StringIO()
    OrchestratorLogger(bus, log_file=log_file, stream=out)

    bus.publish(AgentEvent(agent_name="a", event_type="First"))
    bus.publish(AgentEvent(agent_name="b", event_type="Second"))

    entries = json.loads(log_file.read_text())
    assert len(entries) == 2


def test_logger_summary_no_events():
    bus = EventBus()
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)
    assert logger.summary() == "No events recorded."


def test_logger_summary_counts_event_types():
    bus = EventBus()
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)

    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="a", event_type="TypeA"))
    bus.publish(AgentEvent(agent_name="b", event_type="TypeB"))

    summary = logger.summary()
    assert "TypeA: 2" in summary
    assert "TypeB: 1" in summary


def test_logger_verbose_prints_payload_keys():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, verbose=True, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="Ev", payload={"mykey": "myval"}))

    output = out.getvalue()
    assert "mykey" in output
    assert "myval" in output


def test_logger_non_verbose_does_not_print_payload():
    bus = EventBus()
    out = io.StringIO()
    OrchestratorLogger(bus, verbose=False, stream=out)

    bus.publish(AgentEvent(agent_name="x", event_type="Ev", payload={"secret": "hidden"}))

    assert "secret" not in out.getvalue()


def test_logger_survives_corrupted_log_file(tmp_path):
    """Logger should not crash when log_file exists but contains invalid JSON."""
    bus = EventBus()
    log_file = tmp_path / "log.json"
    log_file.write_text("NOT VALID JSON", encoding="utf-8")
    out = io.StringIO()
    logger = OrchestratorLogger(bus, log_file=log_file, stream=out)

    # Publishing after corruption must not raise
    bus.publish(AgentEvent(agent_name="x", event_type="E"))

    # After recovery, the file should be valid JSON with one entry
    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
