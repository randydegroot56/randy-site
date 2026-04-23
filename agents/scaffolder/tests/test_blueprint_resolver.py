"""Tests for BlueprintResolver."""
import pytest
from pathlib import Path
from agents.scaffolder.blueprint_resolver import BlueprintResolver, Blueprint
from agents.spec_writer.schema import SpecDoc, ProjectSection


def _spec(language: str, type_: str) -> SpecDoc:
    doc = SpecDoc()
    doc.project = ProjectSection(name="MyProject", language=language, type=type_, framework="")
    return doc


class _FakeBlueprint:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "1.0.0"
        self.description = ""
        self.language = "python"
        self.files = []
        self.required_spec_fields: list = []
        self.optional_spec_fields: list = []
        self.blueprints_dir = Path(".")


def test_python_api_selects_fastapi(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("python", "api"))
    assert bp.name == "fastapi-service"
    assert warnings == []


def test_python_fullstack_selects_fastapi(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("python", "fullstack"))
    assert bp.name == "fastapi-service"
    assert warnings == []


def test_python_cli_selects_python_cli(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("python", "cli"))
    assert bp.name == "python-cli"
    assert warnings == []


def test_python_library_selects_python_library(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("python", "library"))
    assert bp.name == "python-library"
    assert warnings == []


def test_typescript_api_selects_express(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("typescript", "api"))
    assert bp.name == "express-api"
    assert warnings == []


def test_typescript_frontend_selects_nextjs(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("typescript", "frontend"))
    assert bp.name == "nextjs-app"
    assert warnings == []


def test_unknown_language_falls_back_with_warning(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("rust", "api"))
    assert bp.name == "python-library"
    assert len(warnings) == 1
    assert "fallback" in warnings[0]


def test_todo_language_falls_back_with_warning(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("TODO", "TODO"))
    assert bp.name == "python-library"
    assert len(warnings) == 1


def test_always_returns_blueprint_never_raises(monkeypatch):
    r = BlueprintResolver()
    monkeypatch.setattr(r, "_load", lambda name: _FakeBlueprint(name))
    bp, warnings = r.resolve(_spec("cobol", "mainframe"))
    assert bp is not None
    assert isinstance(warnings, list)
