"""Tests for agents.spec_writer.parser.SpecParser."""
import pytest
from agents.spec_writer.parser import SpecParser


# ── Section-header extraction ─────────────────────────────────────────────────

def test_section_header_extracts_language():
    text = "## Tech Stack\n- python\n- fastapi"
    spec = SpecParser().parse(text)
    assert spec.project.language == "python"


def test_section_header_extracts_framework():
    text = "## Tech Stack\n- python\n- fastapi"
    spec = SpecParser().parse(text)
    assert spec.project.framework == "fastapi"


def test_section_header_extracts_features_from_requirements():
    text = "## Requirements\n- User can log in\n- User can log out"
    spec = SpecParser().parse(text)
    assert len(spec.features) == 2
    assert spec.features[0].description == "User can log in"
    assert spec.features[1].description == "User can log out"


def test_section_header_extracts_acceptance_criteria():
    text = "## Requirements\n- Implement login\n## Acceptance Criteria\n- Returns 200\n- Invalid password returns 401"
    spec = SpecParser().parse(text)
    assert "Returns 200" in spec.features[-1].acceptance_criteria


def test_section_header_extracts_performance_constraint():
    text = "## Constraints\n- Response time under 200ms"
    spec = SpecParser().parse(text)
    assert len(spec.constraints.performance) == 1
    assert "200ms" in spec.constraints.performance[0]


def test_section_header_extracts_security_constraint():
    text = "## Constraints\n- All endpoints must use HTTPS\n- Auth required"
    spec = SpecParser().parse(text)
    assert len(spec.constraints.security) >= 1


def test_feature_ids_are_sequential():
    text = "## Requirements\n- Feature A\n- Feature B\n- Feature C"
    spec = SpecParser().parse(text)
    assert [f.id for f in spec.features] == ["F001", "F002", "F003"]


def test_raw_description_stored():
    text = "Build a REST API"
    spec = SpecParser().parse(text)
    assert spec.input.raw_description == text


# ── Keyword heuristics ─────────────────────────────────────────────────────────

def test_keyword_detects_language_no_header():
    spec = SpecParser().parse("Build a CLI tool in Python that reads CSV files")
    assert spec.project.language == "python"


def test_keyword_detects_framework_no_header():
    spec = SpecParser().parse("Build a REST API with FastAPI and Python")
    assert spec.project.framework == "fastapi"


def test_keyword_detects_project_type_api():
    spec = SpecParser().parse("Build a REST API for user management")
    assert spec.project.type == "api"


def test_keyword_detects_project_type_cli():
    spec = SpecParser().parse("Build a CLI tool for file conversion")
    assert spec.project.type == "cli"


def test_keyword_detects_project_type_frontend():
    spec = SpecParser().parse("Build a frontend web app with Vue")
    assert spec.project.type == "frontend"


def test_feature_priority_must():
    spec = SpecParser().parse("## Requirements\n- Must support authentication")
    assert spec.features[0].priority == "must"


def test_feature_priority_could():
    spec = SpecParser().parse("## Requirements\n- Could add dark mode")
    assert spec.features[0].priority == "could"


def test_feature_priority_default_should():
    spec = SpecParser().parse("## Requirements\n- Support CSV export")
    assert spec.features[0].priority == "should"


# ── Robustness ────────────────────────────────────────────────────────────────

def test_empty_input_returns_todo_fields():
    spec = SpecParser().parse("")
    assert spec.project.language == "TODO"
    assert spec.project.type == "TODO"


def test_empty_input_has_warning():
    spec = SpecParser().parse("")
    assert any("empty" in w.lower() for w in spec.warnings)


def test_vague_input_never_raises():
    spec = SpecParser().parse("something something ???")
    assert spec is not None


def test_vague_input_produces_warnings():
    spec = SpecParser().parse("something unclear")
    assert len(spec.warnings) >= 1


def test_unstructured_list_items_become_features():
    spec = SpecParser().parse("- User login\n- User registration\n- Password reset")
    assert len(spec.features) == 3


def test_fallback_to_single_feature_when_no_list():
    spec = SpecParser().parse("Build me a thing that does stuff")
    assert len(spec.features) >= 1
