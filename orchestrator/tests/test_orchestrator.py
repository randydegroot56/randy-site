import io
import pytest
from orchestrator.base_agent import BaseAgent
from orchestrator.bus import EventBus
from orchestrator.events import AuditCompleted
from orchestrator.logger import OrchestratorLogger
from orchestrator.orchestrator import Orchestrator
from orchestrator.registry import AgentRegistry
from orchestrator.state import StateStore


class EchoAuditAgent(BaseAgent):
    """Test double: echoes target back in result."""
    name = "code_auditor"
    description = "Echo audit for testing"

    def run(self, target=".", **kwargs):
        result = {"target": target, "issues_found": 0}
        self.emit(AuditCompleted(agent_name=self.name, payload=result))
        return result


class EchoFixAgent(BaseAgent):
    """Test double: records whether audit_result was received."""
    name = "code_fixer"
    description = "Echo fixer for testing"

    def run(self, target=".", audit_result=None, **kwargs):
        from orchestrator.events import FixCompleted
        result = {"target": target, "audit_result_received": audit_result is not None}
        self.emit(FixCompleted(agent_name=self.name, payload=result))
        return result


def make_orch(tmp_path, agents=None):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    out = io.StringIO()
    logger = OrchestratorLogger(bus, stream=out)
    registry = AgentRegistry()
    for cls in (agents or [EchoAuditAgent, EchoFixAgent]):
        registry.register(cls)
    orch = Orchestrator(registry, bus, state, logger)
    return orch, state, logger


def test_run_audit_dispatches_to_code_auditor(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    result = orch.run("audit", ["./src"])
    assert result["target"] == "./src"


def test_run_audit_stores_result_in_state(tmp_path):
    orch, state, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    stored = state.get("last_AuditCompleted")
    assert stored is not None
    assert stored["target"] == "./src"


def test_run_fix_after_audit_passes_audit_result(tmp_path):
    orch, state, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    result = orch.run("fix", [])
    assert result["audit_result_received"] is True


def test_run_fix_with_explicit_target(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    result = orch.run("fix", ["./src"])
    assert result["target"] == "./src"


def test_run_unknown_command_raises_value_error(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    with pytest.raises(ValueError, match="Unknown command 'unknown'"):
        orch.run("unknown", [])


def test_run_unknown_command_error_lists_available(tmp_path):
    orch, _, _ = make_orch(tmp_path)
    with pytest.raises(ValueError, match="audit"):
        orch.run("unknown", [])


def test_print_summary_calls_logger_summary(tmp_path, capsys):
    orch, _, _ = make_orch(tmp_path)
    orch.run("audit", ["./src"])
    orch.print_summary()
    captured = capsys.readouterr()
    assert "AuditCompleted" in captured.out
