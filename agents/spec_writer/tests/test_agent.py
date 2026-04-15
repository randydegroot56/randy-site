"""Tests for agents.spec_writer.agent.SpecWriterAgent."""
import pytest
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.spec_writer.agent import SpecWriterAgent


def make_agent(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = SpecWriterAgent(bus=bus, state=state, specs_dir=tmp_path / "specs")
    return agent, bus, state


def test_agent_name():
    assert SpecWriterAgent.name == "spec"


def test_unknown_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown spec subcommand"):
        agent.run(args=["bogus"])


def test_none_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError):
        agent.run(args=[])


def test_create_returns_spec_id(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "Build a Python REST API with FastAPI"])
    assert "spec_id" in result
    assert result["spec_id"].startswith("spec_")


def test_create_saves_file(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "Build a Python REST API"])
    spec_id = result["spec_id"]
    assert (tmp_path / "specs" / f"{spec_id}.json").exists()


def test_create_publishes_spec_created(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("SpecCreated", received.append)
    agent.run(args=["create", "Build a Python CLI tool"])
    assert len(received) == 1
    assert received[0].event_type == "SpecCreated"


def test_list_returns_entries(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["create", "First project"])
    agent.run(args=["create", "Second project"])
    result = agent.run(args=["list"])
    assert len(result["specs"]) == 2


def test_show_returns_spec(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "A Python API"])
    spec_id = created["spec_id"]
    result = agent.run(args=["show", spec_id])
    assert result["spec"]["spec_id"] == spec_id


def test_show_unknown_id_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(FileNotFoundError):
        agent.run(args=["show", "spec_no_such"])


def test_validate_publishes_spec_validated(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build a thing"])
    spec_id = created["spec_id"]
    received = []
    bus.subscribe("SpecValidated", received.append)
    agent.run(args=["validate", spec_id])
    assert len(received) == 1
    assert received[0].event_type == "SpecValidated"


def test_export_json(tmp_path):
    import json
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    result = agent.run(args=["export", spec_id, "--format", "json"])
    assert "output" in result
    data = json.loads(result["output"])
    assert data["spec_id"] == spec_id


def test_export_markdown(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    result = agent.run(args=["export", spec_id, "--format", "md"])
    assert "output" in result
    assert "# Spec:" in result["output"]


def test_create_from_file(tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("Build a Python CLI tool that converts CSV to JSON", encoding="utf-8")
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "--file", str(input_file)])
    assert "spec_id" in result


def test_update_adds_new_feature(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build a Python CLI tool"])
    spec_id = created["spec_id"]
    agent.run(args=["update", spec_id, "- Add export to CSV feature"])
    result = agent.run(args=["show", spec_id])
    feature_names = [f["name"] for f in result["spec"]["features"]]
    assert any("CSV" in name or "export" in name.lower() for name in feature_names)


def test_update_publishes_spec_updated(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    received = []
    bus.subscribe("SpecUpdated", received.append)
    agent.run(args=["update", spec_id, "- Add new feature"])
    assert len(received) == 1
    assert received[0].event_type == "SpecUpdated"
