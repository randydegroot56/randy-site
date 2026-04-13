import pytest
from agents.orchestrator.agents.audit_agent import AuditAgent
from agents.orchestrator.agents.fixer_agent import FixerAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


# ----- AuditAgent -----

def test_audit_agent_name():
    assert AuditAgent.name == "code_auditor"


def test_audit_agent_run_returns_dict_with_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"
    assert "status" in result


def test_audit_agent_run_default_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    result = agent.run()
    assert result["target"] == "."


def test_audit_agent_emits_audit_completed(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("AuditCompleted", received.append)

    agent = AuditAgent(bus=bus, state=state)
    agent.run(target="./src")

    assert len(received) == 1
    assert received[0].agent_name == "code_auditor"


def test_audit_agent_stores_result_in_state(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = AuditAgent(bus=bus, state=state)
    agent.run(target="./src")

    stored = state.get("last_AuditCompleted")
    assert stored is not None
    assert stored["target"] == "./src"


# ----- FixerAgent -----

def test_fixer_agent_name():
    assert FixerAgent.name == "code_fixer"


def test_fixer_agent_run_returns_dict_with_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"


def test_fixer_agent_run_default_target(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run()
    assert result["target"] == "."


def test_fixer_agent_detects_audit_result(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run(audit_result={"issues_found": 5})
    assert result["audit_result_received"] is True


def test_fixer_agent_handles_no_audit_result(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = FixerAgent(bus=bus, state=state)
    result = agent.run()
    assert result["audit_result_received"] is False


def test_fixer_agent_emits_fix_completed(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("FixCompleted", received.append)

    agent = FixerAgent(bus=bus, state=state)
    agent.run()

    assert len(received) == 1
    assert received[0].agent_name == "code_fixer"
