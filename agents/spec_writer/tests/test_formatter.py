"""Tests for agents.spec_writer.formatter.SpecFormatter."""
import json
import pytest
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc
from agents.spec_writer.formatter import SpecFormatter


def make_spec(spec_id="spec_20260415_001") -> SpecDoc:
    return SpecDoc(
        spec_id=spec_id,
        project=ProjectSection(name="TestApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in",
                          acceptance_criteria=["Returns 200 on success"])],
    )


def test_save_writes_json_file(tmp_path):
    path = SpecFormatter(specs_dir=tmp_path).save(make_spec())
    assert path.exists()
    assert path.suffix == ".json"


def test_save_filename_matches_spec_id(tmp_path):
    path = SpecFormatter(specs_dir=tmp_path).save(make_spec("spec_20260415_042"))
    assert path.name == "spec_20260415_042.json"


def test_load_round_trip(tmp_path):
    formatter = SpecFormatter(specs_dir=tmp_path)
    formatter.save(make_spec())
    loaded = formatter.load("spec_20260415_001")
    assert loaded.spec_id == "spec_20260415_001"
    assert loaded.project.language == "python"
    assert loaded.features[0].name == "Login"


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        SpecFormatter(specs_dir=tmp_path).load("spec_no_such_id")


def test_to_json_is_valid_json(tmp_path):
    result = SpecFormatter(specs_dir=tmp_path).to_json(make_spec())
    data = json.loads(result)
    assert data["spec_id"] == "spec_20260415_001"


def test_list_specs_returns_metadata(tmp_path):
    formatter = SpecFormatter(specs_dir=tmp_path)
    formatter.save(make_spec("spec_20260415_001"))
    formatter.save(make_spec("spec_20260415_002"))
    items = formatter.list_specs()
    assert len(items) == 2
    assert all("spec_id" in item for item in items)
    assert all("status" in item for item in items)


def test_list_specs_empty_dir(tmp_path):
    assert SpecFormatter(specs_dir=tmp_path).list_specs() == []


# ── Markdown output ────────────────────────────────────────────────────────────

def test_to_markdown_contains_project_name(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "TestApp" in md


def test_to_markdown_contains_feature_name(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "Login" in md


def test_to_markdown_contains_feature_id(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "F001" in md


def test_to_markdown_contains_acceptance_criteria(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "Returns 200 on success" in md


def test_to_markdown_warnings_section(tmp_path):
    spec = make_spec()
    spec.warnings = ["project.name is TODO"]
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(spec)
    assert "Warnings" in md
    assert "project.name is TODO" in md
