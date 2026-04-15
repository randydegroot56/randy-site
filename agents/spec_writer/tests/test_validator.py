"""Tests for agents.spec_writer.validator.SpecValidator."""
import pytest
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc, TechnicalSpec
from agents.spec_writer.validator import SpecValidator


def make_valid_spec() -> SpecDoc:
    return SpecDoc(
        spec_id="spec_20260415_001",
        project=ProjectSection(name="MyApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in",
                          acceptance_criteria=["Returns 200 on success"])],
        technical=TechnicalSpec(api_endpoints=[{"method": "POST", "path": "/login"}]),
    )


def test_valid_spec_has_validated_status():
    result = SpecValidator().validate(make_valid_spec())
    assert result.status == "validated"


def test_valid_spec_has_no_warnings():
    result = SpecValidator().validate(make_valid_spec())
    assert result.warnings == []


def test_missing_project_name_adds_warning():
    spec = make_valid_spec()
    spec.project.name = "TODO"
    result = SpecValidator().validate(spec)
    assert any("project.name" in w for w in result.warnings)


def test_missing_language_adds_warning():
    spec = make_valid_spec()
    spec.project.language = "TODO"
    result = SpecValidator().validate(spec)
    assert any("language" in w for w in result.warnings)


def test_empty_features_adds_warning():
    spec = make_valid_spec()
    spec.features = []
    result = SpecValidator().validate(spec)
    assert any("features" in w for w in result.warnings)


def test_feature_without_acceptance_criteria_adds_warning():
    spec = make_valid_spec()
    spec.features[0].acceptance_criteria = []
    result = SpecValidator().validate(spec)
    assert any("acceptance" in w.lower() for w in result.warnings)


def test_api_type_without_endpoints_adds_warning():
    spec = make_valid_spec()
    spec.project.type = "api"
    spec.technical.api_endpoints = []
    result = SpecValidator().validate(spec)
    assert any("endpoint" in w.lower() for w in result.warnings)


def test_frontend_with_python_adds_warning():
    spec = make_valid_spec()
    spec.project.type = "frontend"
    spec.project.language = "python"
    result = SpecValidator().validate(spec)
    assert any("frontend" in w.lower() or "python" in w.lower() for w in result.warnings)


def test_duplicate_feature_names_add_warning():
    spec = make_valid_spec()
    spec.features.append(Feature(id="F002", name="Login", description="Another login"))
    result = SpecValidator().validate(spec)
    assert any("duplicate" in w.lower() for w in result.warnings)


def test_validator_never_raises_on_empty_spec():
    result = SpecValidator().validate(SpecDoc())
    assert result is not None


def test_warnings_produce_draft_status():
    result = SpecValidator().validate(SpecDoc())  # all TODOs
    assert result.status == "draft"
