"""Tests for agents.test_generator.agent.TestGeneratorAgent."""
import pytest
from pathlib import Path
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.test_generator.agent import TestGeneratorAgent


def make_agent(tmp_path, **kwargs):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = TestGeneratorAgent(bus=bus, state=state, tests_dir=tmp_path / "tests", **kwargs)
    return agent, bus, state


def write_source(tmp_path, content="def greet(name):\n    return f'Hello {name}'\n"):
    src = tmp_path / "greet.py"
    src.write_text(content)
    return src


# ── basic contract ───────────────────────────────────────────────────────────

def test_agent_name():
    assert TestGeneratorAgent.name == "testgen"


def test_agent_description_is_set():
    assert TestGeneratorAgent.description


def test_unknown_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown test subcommand"):
        agent.run(args=["bogus"])


def test_none_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown test subcommand"):
        agent.run(args=[])


# ── generate --from-code ─────────────────────────────────────────────────────

def test_generate_from_code_creates_test_file(tmp_path):
    src = write_source(tmp_path)
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["generate", "--from-code", str(src)])
    assert "path" in result
    assert Path(result["path"]).exists()


def test_generate_from_code_publishes_tests_generated(tmp_path):
    src = write_source(tmp_path)
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("TestsGenerated", received.append)
    agent.run(args=["generate", "--from-code", str(src)])
    assert len(received) == 1
    assert received[0].event_type == "TestsGenerated"


def test_generate_returns_scenarios_count(tmp_path):
    src = write_source(tmp_path)
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["generate", "--from-code", str(src)])
    assert result["scenarios"] >= 1


def test_generate_no_flags_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Usage"):
        agent.run(args=["generate"])


# ── validate ─────────────────────────────────────────────────────────────────

def test_validate_returns_syntax_ok(tmp_path):
    f = tmp_path / "test_foo.py"
    f.write_text("def test_ok():\n    pass\n")
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["validate", str(f)])
    assert "syntax_ok" in result
    assert result["syntax_ok"] is True


def test_validate_publishes_tests_passed_on_green(tmp_path):
    f = tmp_path / "test_foo.py"
    f.write_text("def test_ok():\n    assert 1 == 1\n")
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("TestsPassed", received.append)
    agent.run(args=["validate", str(f)])
    assert len(received) == 1


def test_validate_publishes_tests_failed_on_red(tmp_path):
    f = tmp_path / "test_foo.py"
    f.write_text("def test_fail():\n    assert 1 == 2\n")
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("TestsFailed", received.append)
    agent.run(args=["validate", str(f)])
    assert len(received) == 1


# ── coverage ─────────────────────────────────────────────────────────────────

def test_coverage_returns_report(tmp_path):
    write_source(tmp_path)
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["coverage", str(tmp_path)])
    assert "estimated_coverage" in result
    assert "files_analyzed" in result


def test_coverage_publishes_coverage_report_event(tmp_path):
    write_source(tmp_path)
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("CoverageReport", received.append)
    agent.run(args=["coverage", str(tmp_path)])
    assert len(received) == 1


# ── list ─────────────────────────────────────────────────────────────────────

def test_list_returns_test_files(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_x(): pass\n")
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["list"])
    assert "test_files" in result


# ── run ──────────────────────────────────────────────────────────────────────

def test_run_executes_test_file(tmp_path):
    f = tmp_path / "test_run_me.py"
    f.write_text("def test_ok():\n    assert True\n")
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["run", str(f)])
    assert "passed" in result
    assert result["passed"] >= 1


def test_run_missing_file_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(FileNotFoundError):
        agent.run(args=["run", str(tmp_path / "nonexistent.py")])
