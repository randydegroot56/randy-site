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
