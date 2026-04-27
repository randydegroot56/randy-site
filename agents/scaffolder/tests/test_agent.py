"""Tests for ScaffolderAgent."""
import json
import pytest
from pathlib import Path
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.scaffolder.agent import ScaffolderAgent


def _make_agent(tmp_path: Path, registry=None) -> ScaffolderAgent:
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    return ScaffolderAgent(
        bus=bus,
        state=state,
        registry=registry,
        scaffolds_dir=tmp_path / "scaffolds",
    )


def _write_manifest(tmp_path: Path, spec_id: str) -> Path:
    d = tmp_path / "scaffolds" / spec_id
    d.mkdir(parents=True)
    (d / "main.py").write_text("pass\n", encoding="utf-8")
    manifest = {
        "spec_id": spec_id,
        "blueprint": "python-library",
        "blueprint_version": "1.0.0",
        "scaffold_date": "2026-04-23T00:00:00+00:00",
        "output_dir": str(d),
        "warnings": [],
        "files": [{"relative_path": "main.py", "header": True, "size_bytes": 5}],
    }
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return d


def test_unknown_subcommand_raises_value_error(tmp_path):
    agent = _make_agent(tmp_path)
    with pytest.raises(ValueError):
        agent.run(args=["unknown"])


def test_no_args_raises_value_error(tmp_path):
    agent = _make_agent(tmp_path)
    with pytest.raises(ValueError):
        agent.run(args=[])


def test_clean_removes_scaffold_directory(tmp_path):
    agent = _make_agent(tmp_path)
    scaffold_dir = _write_manifest(tmp_path, "spec_001")
    agent.run(args=["clean", "spec_001"])
    assert not scaffold_dir.exists()


def test_clean_emits_scaffold_cleaned_event(tmp_path):
    agent = _make_agent(tmp_path)
    _write_manifest(tmp_path, "spec_001")
    events = []
    agent._bus.subscribe("ScaffoldCleaned", events.append)
    agent.run(args=["clean", "spec_001"])
    assert len(events) == 1
    assert events[0].payload["spec_id"] == "spec_001"


def test_clean_nonexistent_raises_file_not_found(tmp_path):
    agent = _make_agent(tmp_path)
    with pytest.raises(FileNotFoundError):
        agent.run(args=["clean", "spec_nonexistent"])


def test_validate_returns_ok_for_complete_scaffold(tmp_path):
    agent = _make_agent(tmp_path)
    _write_manifest(tmp_path, "spec_001")
    result = agent.run(args=["validate", "spec_001"])
    assert result["ok"] is True


def test_show_returns_manifest_contents(tmp_path):
    agent = _make_agent(tmp_path)
    _write_manifest(tmp_path, "spec_001")
    result = agent.run(args=["show", "spec_001"])
    assert result["spec_id"] == "spec_001"
    assert result["blueprint"] == "python-library"


def test_spec_created_event_triggers_generate(tmp_path, monkeypatch):
    agent = _make_agent(tmp_path)
    called_with = []
    monkeypatch.setattr(
        agent, "_generate",
        lambda spec_id, force=False: called_with.append(spec_id) or {"spec_id": spec_id},
    )
    from agents.orchestrator.events import SpecCreated
    agent._bus.publish(SpecCreated(agent_name="spec", payload={"spec_id": "spec_001"}))
    assert "spec_001" in called_with


def test_spec_created_error_emits_scaffold_failed(tmp_path):
    agent = _make_agent(tmp_path)
    failed = []
    agent._bus.subscribe("ScaffoldFailed", failed.append)
    from agents.orchestrator.events import SpecCreated
    agent._bus.publish(SpecCreated(agent_name="spec", payload={"spec_id": "spec_nonexistent"}))
    assert len(failed) == 1
    assert failed[0].status == "failed"


def test_list_returns_all_scaffolds(tmp_path):
    agent = _make_agent(tmp_path)
    _write_manifest(tmp_path, "spec_001")
    _write_manifest(tmp_path, "spec_002")
    result = agent.run(args=["list"])
    assert len(result["scaffolds"]) == 2
