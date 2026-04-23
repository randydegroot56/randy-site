"""Tests for StructureGenerator."""
import pytest
from pathlib import Path
from agents.scaffolder.structure_generator import (
    StructureGenerator,
    RenderedFile,
    _derive_name_variants,
)
from agents.scaffolder.blueprint_resolver import Blueprint, BlueprintFile


def _make_blueprint(tmp_path: Path, files: list[dict]) -> Blueprint:
    """Build a Blueprint with in-memory templates written to tmp_path."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True)
    bp_files = []
    for f in files:
        tpl_name = f["template"].split("/")[-1]
        (templates_dir / tpl_name).write_text(f["content"], encoding="utf-8")
        bp_files.append(
            BlueprintFile(path=f["path"], template=f["template"], header=f.get("header", True))
        )
    return Blueprint(
        name="test-bp",
        version="1.0.0",
        description="test",
        language="python",
        files=bp_files,
        required_spec_fields=[],
        optional_spec_fields=[],
        blueprints_dir=tmp_path,
    )


def _ctx(name: str = "MyProject") -> dict:
    variants = _derive_name_variants(name)
    return {
        "spec_id": "spec_test_001",
        "project": type("P", (), {"name": name, "type": "api", "language": "python", "framework": "fastapi"})(),
        "features": [],
        "technical": type("T", (), {"dependencies": [], "api_endpoints": []})(),
        "constraints": type("C", (), {"performance": [], "security": []})(),
        "conventions": [],
        "blueprint_name": "test-bp",
        "blueprint_version": "1.0.0",
        "scaffold_date": "2026-04-23",
        **variants,
    }


def test_renders_file_content(tmp_path):
    bp = _make_blueprint(tmp_path, [
        {"path": "main.py", "template": "templates/main.py.jinja2",
         "content": "# {{ project.name }}\n", "header": True},
    ])
    files = StructureGenerator().generate(bp, _ctx("MyProject"))
    assert len(files) == 1
    assert "MyProject" in files[0].content


def test_path_jinja2_expansion(tmp_path):
    bp = _make_blueprint(tmp_path, [
        {"path": "src/{{ project_name_snake }}/main.py",
         "template": "templates/main.py.jinja2", "content": "", "header": True},
    ])
    files = StructureGenerator().generate(bp, _ctx("MyProject"))
    assert files[0].relative_path == "src/my_project/main.py"


def test_header_flag_passed_through(tmp_path):
    bp = _make_blueprint(tmp_path, [
        {"path": "README.md", "template": "templates/README.md.jinja2",
         "content": "# Readme\n", "header": False},
    ])
    files = StructureGenerator().generate(bp, _ctx())
    assert files[0].header is False


def test_missing_optional_features_no_exception(tmp_path):
    bp = _make_blueprint(tmp_path, [
        {"path": "main.py", "template": "templates/main.py.jinja2",
         "content": "{% for f in features %}{{ f.name }}{% endfor %}", "header": False},
    ])
    ctx = _ctx()
    ctx["features"] = []
    files = StructureGenerator().generate(bp, ctx)
    assert files[0].content == ""


def test_derive_name_variants():
    v = _derive_name_variants("My Cool Project")
    assert v["project_name_snake"] == "my_cool_project"
    assert v["project_name_pascal"] == "MyCoolProject"
    assert v["project_name_kebab"] == "my-cool-project"


def test_derive_name_variants_single_word():
    v = _derive_name_variants("alpha")
    assert v["project_name_snake"] == "alpha"
    assert v["project_name_pascal"] == "Alpha"
    assert v["project_name_kebab"] == "alpha"
