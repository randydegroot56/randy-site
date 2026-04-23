# Scaffolder Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a ScaffolderAgent that reads a SpecDoc and generates a complete project skeleton using declarative Jinja2 blueprints, with auto-scaffold on `SpecCreated` events.

**Architecture:** Two-stage pipeline — BlueprintResolver selects a blueprint, StructureGenerator renders Jinja2 templates into `RenderedFile` objects, FileGenerator writes them to `~/.agent-orchestrator/scaffolds/<spec_id>/`, and a `manifest.json` persists the scaffold state for `show`/`validate`/`re-scaffold`. ScaffolderAgent subscribes to `SpecCreated` on construction (always enabled).

**Tech Stack:** Python 3.11+, Jinja2 3.x (already installed), pytest, pydantic v2 (via spec_writer.schema), argparse (stdlib)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agents/orchestrator/events.py` | Modify | Add `ScaffoldCompleted`, `ScaffoldFailed`, `ScaffoldCleaned` |
| `agents/orchestrator/orchestrator.py` | Modify | Add `"scaffold"` to `INTENT_MAP`, pass `registry` |
| `agents/orchestrator/tests/test_events.py` | Modify | Add scaffold event tests |
| `main.py` | Modify | Register `ScaffolderAgent` in `build_registry()` |
| `agents/scaffolder/__init__.py` | Create | Package marker |
| `agents/scaffolder/blueprint_resolver.py` | Create | Blueprint selection + `Blueprint`/`BlueprintFile` dataclasses |
| `agents/scaffolder/structure_generator.py` | Create | Jinja2 rendering + `RenderedFile` dataclass + `_derive_name_variants` |
| `agents/scaffolder/file_generator.py` | Create | File writing, `.git` safety check, header injection, `ScaffoldError` |
| `agents/scaffolder/validator.py` | Create | Manifest-based completeness check, `ValidationResult` |
| `agents/scaffolder/agent.py` | Create | `ScaffolderAgent` — argparse dispatch, auto-subscribe, `_generate()` pipeline |
| `agents/scaffolder/blueprints/fastapi-service/blueprint.json` | Create | Declarative file list for FastAPI projects |
| `agents/scaffolder/blueprints/fastapi-service/templates/*.jinja2` | Create | 6 templates |
| `agents/scaffolder/blueprints/python-library/blueprint.json` | Create | Declarative file list for Python libraries |
| `agents/scaffolder/blueprints/python-library/templates/*.jinja2` | Create | 5 templates |
| `agents/scaffolder/blueprints/python-cli/blueprint.json` | Create | Declarative file list for Python CLIs |
| `agents/scaffolder/blueprints/python-cli/templates/*.jinja2` | Create | 6 templates |
| `agents/scaffolder/blueprints/express-api/blueprint.json` | Create | Declarative file list for Express APIs |
| `agents/scaffolder/blueprints/express-api/templates/*.jinja2` | Create | 6 templates |
| `agents/scaffolder/blueprints/nextjs-app/blueprint.json` | Create | Declarative file list for Next.js apps |
| `agents/scaffolder/blueprints/nextjs-app/templates/*.jinja2` | Create | 6 templates |
| `agents/scaffolder/tests/__init__.py` | Create | Package marker |
| `agents/scaffolder/tests/test_blueprint_resolver.py` | Create | 9 tests for BlueprintResolver |
| `agents/scaffolder/tests/test_structure_generator.py` | Create | 4 tests for StructureGenerator |
| `agents/scaffolder/tests/test_file_generator.py` | Create | 8 tests for FileGenerator |
| `agents/scaffolder/tests/test_validator.py` | Create | 7 tests for ScaffoldValidator |
| `agents/scaffolder/tests/test_agent.py` | Create | 8 tests for ScaffolderAgent |

---

## Task 1: Scaffold events

**Files:**
- Modify: `agents/orchestrator/events.py` (after line 101 — after `CoverageReport`)
- Modify: `agents/orchestrator/tests/test_events.py` (append)

- [ ] **Step 1: Write failing tests** — append to `agents/orchestrator/tests/test_events.py`:

```python
# ── Scaffold events ────────────────────────────────────────────────────────────

def test_scaffold_completed_event():
    from agents.orchestrator.events import ScaffoldCompleted
    e = ScaffoldCompleted(
        agent_name="scaffold",
        payload={"spec_id": "spec_001", "blueprint": "fastapi-service", "files_written": 5},
    )
    assert e.event_type == "ScaffoldCompleted"
    assert e.status == "success"


def test_scaffold_failed_event():
    from agents.orchestrator.events import ScaffoldFailed
    e = ScaffoldFailed(agent_name="scaffold", error="blueprint not found")
    assert e.event_type == "ScaffoldFailed"
    assert e.status == "failed"
    assert e.error == "blueprint not found"


def test_scaffold_cleaned_event():
    from agents.orchestrator.events import ScaffoldCleaned
    e = ScaffoldCleaned(agent_name="scaffold", payload={"spec_id": "spec_001"})
    assert e.event_type == "ScaffoldCleaned"
    assert e.status == "success"
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest agents/orchestrator/tests/test_events.py::test_scaffold_completed_event -v
```
Expected: `ImportError` — `ScaffoldCompleted` does not exist yet

- [ ] **Step 3: Add events to `agents/orchestrator/events.py`** — append after `CoverageReport`:

```python
@dataclass
class ScaffoldCompleted(AgentEvent):
    event_type: str = "ScaffoldCompleted"


@dataclass
class ScaffoldFailed(AgentEvent):
    event_type: str = "ScaffoldFailed"
    status: str = "failed"


@dataclass
class ScaffoldCleaned(AgentEvent):
    event_type: str = "ScaffoldCleaned"
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest agents/orchestrator/tests/test_events.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/orchestrator/events.py agents/orchestrator/tests/test_events.py
git commit -m "feat(scaffold): add ScaffoldCompleted, ScaffoldFailed, ScaffoldCleaned events"
```

---

## Task 2: BlueprintResolver

**Files:**
- Create: `agents/scaffolder/__init__.py`
- Create: `agents/scaffolder/blueprint_resolver.py`
- Create: `agents/scaffolder/tests/__init__.py`
- Create: `agents/scaffolder/tests/test_blueprint_resolver.py`

- [ ] **Step 1: Create package markers**

`agents/scaffolder/__init__.py`:
```python
"""Scaffolder Agent package."""
```

`agents/scaffolder/tests/__init__.py`:
```python
```

- [ ] **Step 2: Write failing tests** — create `agents/scaffolder/tests/test_blueprint_resolver.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```
pytest agents/scaffolder/tests/test_blueprint_resolver.py -v
```
Expected: `ModuleNotFoundError` — `blueprint_resolver` does not exist yet

- [ ] **Step 4: Create `agents/scaffolder/blueprint_resolver.py`**:

```python
"""Blueprint resolver — selects a project blueprint from a SpecDoc."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BLUEPRINTS_DIR = Path(__file__).parent / "blueprints"

_FALLBACK = "python-library"

_SELECTION: list[tuple[str, frozenset[str], str]] = [
    ("python",     frozenset({"api", "fullstack"}), "fastapi-service"),
    ("python",     frozenset({"cli"}),              "python-cli"),
    ("python",     frozenset({"library"}),          "python-library"),
    ("typescript", frozenset({"api"}),              "express-api"),
    ("typescript", frozenset({"frontend"}),         "nextjs-app"),
]


@dataclass
class BlueprintFile:
    path: str        # may contain Jinja2 {{ var }} expressions
    template: str    # relative path to .jinja2 file within blueprints_dir
    header: bool     # whether FileGenerator should prepend the generated-by comment


@dataclass
class Blueprint:
    name: str
    version: str
    description: str
    language: str
    files: list[BlueprintFile]
    required_spec_fields: list[str]
    optional_spec_fields: list[str]
    blueprints_dir: Path


class BlueprintResolver:
    """Selects a Blueprint based on spec.project.language and spec.project.type."""

    def __init__(self, blueprints_dir: Path = DEFAULT_BLUEPRINTS_DIR) -> None:
        self._dir = blueprints_dir

    def resolve(self, spec) -> tuple[Blueprint, list[str]]:
        """Return (blueprint, warnings). Always returns a Blueprint; never raises."""
        warnings: list[str] = []
        lang = (spec.project.language or "").lower()
        ptype = (spec.project.type or "").lower()

        blueprint_name = _FALLBACK
        matched = False

        for row_lang, row_types, row_name in _SELECTION:
            if lang == row_lang and ptype in row_types:
                blueprint_name = row_name
                matched = True
                break

        if not matched:
            if lang in ("todo", ""):
                warnings.append(
                    f"spec.project.language is '{spec.project.language}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )
            elif ptype in ("todo", ""):
                warnings.append(
                    f"spec.project.type is '{spec.project.type}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )
            else:
                warnings.append(
                    f"No blueprint for language='{lang}' type='{ptype}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )

        return self._load(blueprint_name), warnings

    def _load(self, name: str) -> Blueprint:
        path = self._dir / name / "blueprint.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        files = [
            BlueprintFile(
                path=f["path"],
                template=f["template"],
                header=f.get("header", True),
            )
            for f in data["files"]
        ]
        return Blueprint(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            language=data["language"],
            files=files,
            required_spec_fields=data.get("required_spec_fields", []),
            optional_spec_fields=data.get("optional_spec_fields", []),
            blueprints_dir=self._dir / name,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest agents/scaffolder/tests/test_blueprint_resolver.py -v
```
Expected: all 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/scaffolder/__init__.py agents/scaffolder/blueprint_resolver.py agents/scaffolder/tests/__init__.py agents/scaffolder/tests/test_blueprint_resolver.py
git commit -m "feat(scaffold): add BlueprintResolver with selection table and fallback"
```

---

## Task 3: StructureGenerator

**Files:**
- Create: `agents/scaffolder/structure_generator.py`
- Create: `agents/scaffolder/tests/test_structure_generator.py`

- [ ] **Step 1: Write failing tests** — create `agents/scaffolder/tests/test_structure_generator.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest agents/scaffolder/tests/test_structure_generator.py -v
```
Expected: `ModuleNotFoundError` — `structure_generator` does not exist yet

- [ ] **Step 3: Create `agents/scaffolder/structure_generator.py`**:

```python
"""StructureGenerator — renders Jinja2 templates into RenderedFile objects."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from jinja2 import Environment, FileSystemLoader

from agents.scaffolder.blueprint_resolver import Blueprint


@dataclass
class RenderedFile:
    relative_path: str
    content: str
    header: bool


def _derive_name_variants(name: str) -> dict[str, str]:
    """Return snake_case, PascalCase, and kebab-case variants of a project name."""
    clean = (name or "project").strip()
    snake = re.sub(r"[^a-z0-9]+", "_", clean.lower()).strip("_") or "project"
    pascal = "".join(w.capitalize() for w in re.split(r"[^a-zA-Z0-9]+", clean) if w)
    kebab = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-") or "project"
    return {
        "project_name_snake": snake,
        "project_name_pascal": pascal,
        "project_name_kebab": kebab,
    }


class StructureGenerator:
    """Renders a Blueprint's Jinja2 templates into a list of RenderedFile objects."""

    def generate(self, blueprint: Blueprint, context: dict) -> list[RenderedFile]:
        """Render all blueprint templates. Returns RenderedFile list; never raises on missing optional fields."""
        env = Environment(
            loader=FileSystemLoader(str(blueprint.blueprints_dir / "templates")),
            keep_trailing_newline=True,
        )
        path_env = Environment()  # separate env for expanding path strings

        files: list[RenderedFile] = []
        for bf in blueprint.files:
            rendered_path = path_env.from_string(bf.path).render(context)
            tpl_name = bf.template.split("/")[-1]
            template = env.get_template(tpl_name)
            content = template.render(context)
            files.append(RenderedFile(
                relative_path=rendered_path,
                content=content,
                header=bf.header,
            ))
        return files
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest agents/scaffolder/tests/test_structure_generator.py -v
```
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/scaffolder/structure_generator.py agents/scaffolder/tests/test_structure_generator.py
git commit -m "feat(scaffold): add StructureGenerator with Jinja2 rendering and name variants"
```

---

## Task 4: FileGenerator

**Files:**
- Create: `agents/scaffolder/file_generator.py`
- Create: `agents/scaffolder/tests/test_file_generator.py`

- [ ] **Step 1: Write failing tests** — create `agents/scaffolder/tests/test_file_generator.py`:

```python
"""Tests for FileGenerator."""
import pytest
from pathlib import Path
from agents.scaffolder.file_generator import FileGenerator, ScaffoldError
from agents.scaffolder.structure_generator import RenderedFile


def test_writes_file_to_disk(tmp_path):
    gen = FileGenerator()
    files = [RenderedFile(relative_path="src/main.py", content="print('hello')\n", header=True)]
    written = gen.write(files, tmp_path, spec_id="spec_001")
    assert len(written) == 1
    assert (tmp_path / "src" / "main.py").exists()


def test_header_prepended_for_py(tmp_path):
    gen = FileGenerator()
    files = [RenderedFile(relative_path="main.py", content="pass\n", header=True)]
    gen.write(files, tmp_path, spec_id="spec_001")
    first_line = (tmp_path / "main.py").read_text().splitlines()[0]
    assert first_line == "# Generated by Scaffolder Agent from spec spec_001"


def test_header_prepended_for_ts(tmp_path):
    gen = FileGenerator()
    files = [RenderedFile(relative_path="index.ts", content="export {}\n", header=True)]
    gen.write(files, tmp_path, spec_id="spec_001")
    first_line = (tmp_path / "index.ts").read_text().splitlines()[0]
    assert first_line == "// Generated by Scaffolder Agent from spec spec_001"


def test_no_header_when_header_false(tmp_path):
    gen = FileGenerator()
    files = [RenderedFile(relative_path="pyproject.toml", content="[project]\n", header=False)]
    gen.write(files, tmp_path, spec_id="spec_001")
    content = (tmp_path / "pyproject.toml").read_text()
    assert content.startswith("[project]")


def test_no_header_for_unsupported_extension(tmp_path):
    gen = FileGenerator()
    # .toml has no header prefix even with header=True — falls through gracefully
    files = [RenderedFile(relative_path="config.toml", content="[x]\n", header=False)]
    gen.write(files, tmp_path, spec_id="spec_001")
    content = (tmp_path / "config.toml").read_text()
    assert not content.startswith("#")


def test_git_dir_raises_scaffold_error(tmp_path):
    (tmp_path / ".git").mkdir()
    gen = FileGenerator()
    files = [RenderedFile(relative_path="main.py", content="", header=False)]
    with pytest.raises(ScaffoldError, match=r"\.git"):
        gen.write(files, tmp_path, spec_id="spec_001")


def test_git_dir_with_force_writes_files(tmp_path):
    (tmp_path / ".git").mkdir()
    gen = FileGenerator()
    files = [RenderedFile(relative_path="main.py", content="pass\n", header=False)]
    written = gen.write(files, tmp_path, force=True, spec_id="spec_001")
    assert len(written) == 1
    assert (tmp_path / "main.py").exists()


def test_subdirectories_created_automatically(tmp_path):
    gen = FileGenerator()
    files = [RenderedFile(relative_path="a/b/c/deep.py", content="pass\n", header=False)]
    gen.write(files, tmp_path, spec_id="spec_001")
    assert (tmp_path / "a" / "b" / "c" / "deep.py").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest agents/scaffolder/tests/test_file_generator.py -v
```
Expected: `ModuleNotFoundError` — `file_generator` does not exist yet

- [ ] **Step 3: Create `agents/scaffolder/file_generator.py`**:

```python
"""FileGenerator — writes RenderedFile objects to disk with safety checks."""
from __future__ import annotations

from pathlib import Path

from agents.scaffolder.structure_generator import RenderedFile

_HEADER_PREFIXES: dict[str, str] = {
    ".py":  "# Generated by Scaffolder Agent from spec {spec_id}",
    ".ts":  "// Generated by Scaffolder Agent from spec {spec_id}",
    ".js":  "// Generated by Scaffolder Agent from spec {spec_id}",
    ".tsx": "// Generated by Scaffolder Agent from spec {spec_id}",
    ".jsx": "// Generated by Scaffolder Agent from spec {spec_id}",
}


class ScaffoldError(Exception):
    """Raised when scaffolding is blocked (e.g. target has a .git directory)."""


class FileGenerator:
    """Writes RenderedFile objects to an output directory."""

    def write(
        self,
        files: list[RenderedFile],
        output_dir: Path,
        force: bool = False,
        spec_id: str = "",
    ) -> list[Path]:
        """Write files to output_dir. Raises ScaffoldError if .git found (unless force=True)."""
        if not force and (output_dir / ".git").exists():
            raise ScaffoldError(
                f"Target directory '{output_dir}' contains a .git repository. "
                "Use force=True to override."
            )

        written: list[Path] = []
        for rf in files:
            dest = output_dir / rf.relative_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = rf.content

            if rf.header:
                suffix = Path(rf.relative_path).suffix
                prefix_template = _HEADER_PREFIXES.get(suffix)
                if prefix_template:
                    header_line = prefix_template.format(spec_id=spec_id)
                    content = header_line + "\n" + content

            dest.write_text(content, encoding="utf-8")
            written.append(dest)

        return written
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest agents/scaffolder/tests/test_file_generator.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/scaffolder/file_generator.py agents/scaffolder/tests/test_file_generator.py
git commit -m "feat(scaffold): add FileGenerator with .git safety check and header injection"
```

---

## Task 5: ScaffoldValidator

**Files:**
- Create: `agents/scaffolder/validator.py`
- Create: `agents/scaffolder/tests/test_validator.py`

- [ ] **Step 1: Write failing tests** — create `agents/scaffolder/tests/test_validator.py`:

```python
"""Tests for ScaffoldValidator."""
import json
import pytest
from pathlib import Path
from agents.scaffolder.validator import ScaffoldValidator, ValidationResult


def _write_manifest(tmp_path: Path, files: list[dict]) -> None:
    manifest = {"spec_id": "spec_001", "files": files}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_all_present_returns_ok(tmp_path):
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "main.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is True
    assert result.missing == []
    assert result.empty == []


def test_missing_file_detected(tmp_path):
    _write_manifest(tmp_path, [{"relative_path": "missing.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert "missing.py" in result.missing


def test_empty_file_with_header_true_flagged(tmp_path):
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "main.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert "main.py" in result.empty


def test_empty_file_with_header_false_not_flagged(tmp_path):
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "README.md", "header": False}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is True


def test_missing_manifest_returns_not_ok(tmp_path):
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert any("manifest.json" in w for w in result.warnings)


def test_corrupt_manifest_returns_not_ok(tmp_path):
    (tmp_path / "manifest.json").write_text("not {{ valid json", encoding="utf-8")
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert any("could not be parsed" in w for w in result.warnings)


def test_never_raises_for_nonexistent_dir(tmp_path):
    result = ScaffoldValidator().validate(tmp_path / "does_not_exist")
    assert isinstance(result, ValidationResult)
    assert result.ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest agents/scaffolder/tests/test_validator.py -v
```
Expected: `ModuleNotFoundError` — `validator` does not exist yet

- [ ] **Step 3: Create `agents/scaffolder/validator.py`**:

```python
"""ScaffoldValidator — verifies a scaffold is complete using its manifest."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    ok: bool
    missing: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ScaffoldValidator:
    """Checks that all files listed in manifest.json exist and are non-empty."""

    def validate(self, output_dir: Path) -> ValidationResult:
        """Return ValidationResult; never raises."""
        manifest_path = output_dir / "manifest.json"
        if not manifest_path.exists():
            return ValidationResult(
                ok=False,
                warnings=["manifest.json not found in scaffold directory"],
            )

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return ValidationResult(
                ok=False,
                warnings=[f"manifest.json could not be parsed: {exc}"],
            )

        missing: list[str] = []
        empty: list[str] = []

        for entry in manifest.get("files", []):
            rel = entry["relative_path"]
            path = output_dir / rel
            if not path.exists():
                missing.append(rel)
            elif path.stat().st_size == 0 and entry.get("header", True):
                empty.append(rel)

        return ValidationResult(ok=not missing and not empty, missing=missing, empty=empty)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest agents/scaffolder/tests/test_validator.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/scaffolder/validator.py agents/scaffolder/tests/test_validator.py
git commit -m "feat(scaffold): add ScaffoldValidator with manifest-based completeness check"
```

---

## Task 6: Blueprints

**Files:** 5 × `blueprint.json` + 5 × `templates/` directory (26 template files total)

- [ ] **Step 1: Create `agents/scaffolder/blueprints/fastapi-service/blueprint.json`**:

```json
{
    "name": "fastapi-service",
    "version": "1.0.0",
    "description": "FastAPI service with pytest and pyproject.toml",
    "language": "python",
    "files": [
        {"path": "src/{{ project_name_snake }}/__init__.py",    "template": "templates/pkg_init.py.jinja2",     "header": true},
        {"path": "src/{{ project_name_snake }}/main.py",        "template": "templates/main.py.jinja2",         "header": true},
        {"path": "tests/__init__.py",                           "template": "templates/tests_init.py.jinja2",   "header": true},
        {"path": "tests/test_{{ project_name_snake }}.py",      "template": "templates/test_main.py.jinja2",    "header": true},
        {"path": "pyproject.toml",                              "template": "templates/pyproject.toml.jinja2",  "header": false},
        {"path": "README.md",                                   "template": "templates/README.md.jinja2",       "header": false}
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

- [ ] **Step 2: Create fastapi-service templates**

`agents/scaffolder/blueprints/fastapi-service/templates/pkg_init.py.jinja2`:
```
"""{{ project.name }} service."""
```

`agents/scaffolder/blueprints/fastapi-service/templates/main.py.jinja2`:
```python
from fastapi import FastAPI

app = FastAPI(title="{{ project.name }}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

`agents/scaffolder/blueprints/fastapi-service/templates/tests_init.py.jinja2`:
```
```
(empty file — intentionally blank)

`agents/scaffolder/blueprints/fastapi-service/templates/test_main.py.jinja2`:
```python
from fastapi.testclient import TestClient
from {{ project_name_snake }}.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

`agents/scaffolder/blueprints/fastapi-service/templates/pyproject.toml.jinja2`:
```toml
[project]
name = "{{ project_name_kebab }}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
{% for dep in technical.dependencies %}    "{{ dep }}",
{% endfor %}]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`agents/scaffolder/blueprints/fastapi-service/templates/README.md.jinja2`:
```markdown
# {{ project.name }}

> Generated by Scaffolder Agent from spec {{ spec_id }}

## Setup

```bash
pip install -e .
uvicorn {{ project_name_snake }}.main:app --reload
```

## Test

```bash
pytest
```
```

- [ ] **Step 3: Create `agents/scaffolder/blueprints/python-library/blueprint.json`**:

```json
{
    "name": "python-library",
    "version": "1.0.0",
    "description": "Python library with pytest and pyproject.toml",
    "language": "python",
    "files": [
        {"path": "src/{{ project_name_snake }}/__init__.py",   "template": "templates/init.py.jinja2",         "header": true},
        {"path": "tests/__init__.py",                          "template": "templates/tests_init.py.jinja2",   "header": true},
        {"path": "tests/test_{{ project_name_snake }}.py",     "template": "templates/test_lib.py.jinja2",     "header": true},
        {"path": "pyproject.toml",                             "template": "templates/pyproject.toml.jinja2",  "header": false},
        {"path": "README.md",                                  "template": "templates/README.md.jinja2",       "header": false}
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

- [ ] **Step 4: Create python-library templates**

`agents/scaffolder/blueprints/python-library/templates/init.py.jinja2`:
```python
"""{{ project.name }}."""

__version__ = "0.1.0"
```

`agents/scaffolder/blueprints/python-library/templates/tests_init.py.jinja2`:
```
```
(empty file)

`agents/scaffolder/blueprints/python-library/templates/test_lib.py.jinja2`:
```python
from {{ project_name_snake }} import __version__


def test_version() -> None:
    assert isinstance(__version__, str)
```

`agents/scaffolder/blueprints/python-library/templates/pyproject.toml.jinja2`:
```toml
[project]
name = "{{ project_name_kebab }}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
{% for dep in technical.dependencies %}    "{{ dep }}",
{% endfor %}]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`agents/scaffolder/blueprints/python-library/templates/README.md.jinja2`:
```markdown
# {{ project.name }}

> Generated by Scaffolder Agent from spec {{ spec_id }}

## Setup

```bash
pip install -e .
```

## Test

```bash
pytest
```
```

- [ ] **Step 5: Create `agents/scaffolder/blueprints/python-cli/blueprint.json`**:

```json
{
    "name": "python-cli",
    "version": "1.0.0",
    "description": "Python CLI tool with Click, pytest and pyproject.toml",
    "language": "python",
    "files": [
        {"path": "src/{{ project_name_snake }}/__init__.py",   "template": "templates/pkg_init.py.jinja2",     "header": true},
        {"path": "src/{{ project_name_snake }}/cli.py",        "template": "templates/cli.py.jinja2",          "header": true},
        {"path": "tests/__init__.py",                          "template": "templates/tests_init.py.jinja2",   "header": true},
        {"path": "tests/test_{{ project_name_snake }}.py",     "template": "templates/test_cli.py.jinja2",     "header": true},
        {"path": "pyproject.toml",                             "template": "templates/pyproject.toml.jinja2",  "header": false},
        {"path": "README.md",                                  "template": "templates/README.md.jinja2",       "header": false}
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

- [ ] **Step 6: Create python-cli templates**

`agents/scaffolder/blueprints/python-cli/templates/pkg_init.py.jinja2`:
```python
"""{{ project.name }} CLI."""
```

`agents/scaffolder/blueprints/python-cli/templates/cli.py.jinja2`:
```python
import click


@click.group()
def cli() -> None:
    """{{ project.name }} command-line interface."""


@cli.command()
def version() -> None:
    """Print version."""
    click.echo("0.1.0")


if __name__ == "__main__":
    cli()
```

`agents/scaffolder/blueprints/python-cli/templates/tests_init.py.jinja2`:
```
```
(empty file)

`agents/scaffolder/blueprints/python-cli/templates/test_cli.py.jinja2`:
```python
from click.testing import CliRunner
from {{ project_name_snake }}.cli import cli


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

`agents/scaffolder/blueprints/python-cli/templates/pyproject.toml.jinja2`:
```toml
[project]
name = "{{ project_name_kebab }}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
{% for dep in technical.dependencies %}    "{{ dep }}",
{% endfor %}]

[project.scripts]
{{ project_name_kebab }} = "{{ project_name_snake }}.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`agents/scaffolder/blueprints/python-cli/templates/README.md.jinja2`:
```markdown
# {{ project.name }}

> Generated by Scaffolder Agent from spec {{ spec_id }}

## Setup

```bash
pip install -e .
```

## Usage

```bash
{{ project_name_kebab }} version
```

## Test

```bash
pytest
```
```

- [ ] **Step 7: Create `agents/scaffolder/blueprints/express-api/blueprint.json`**:

```json
{
    "name": "express-api",
    "version": "1.0.0",
    "description": "Express TypeScript API with Jest",
    "language": "typescript",
    "files": [
        {"path": "src/app.ts",          "template": "templates/app.ts.jinja2",          "header": true},
        {"path": "src/index.ts",        "template": "templates/index.ts.jinja2",        "header": true},
        {"path": "tests/app.test.ts",   "template": "templates/app.test.ts.jinja2",     "header": true},
        {"path": "package.json",        "template": "templates/package.json.jinja2",    "header": false},
        {"path": "tsconfig.json",       "template": "templates/tsconfig.json.jinja2",   "header": false},
        {"path": "README.md",           "template": "templates/README.md.jinja2",       "header": false}
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

- [ ] **Step 8: Create express-api templates**

`agents/scaffolder/blueprints/express-api/templates/app.ts.jinja2`:
```typescript
import express, { Request, Response } from "express";

const app = express();
app.use(express.json());

app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
});

export default app;
```

`agents/scaffolder/blueprints/express-api/templates/index.ts.jinja2`:
```typescript
import app from "./app";

const PORT = process.env.PORT ?? 3000;

app.listen(PORT, () => {
    console.log(`{{ project.name }} listening on port ${PORT}`);
});
```

`agents/scaffolder/blueprints/express-api/templates/app.test.ts.jinja2`:
```typescript
import request from "supertest";
import app from "../src/app";

describe("GET /health", () => {
    it("returns ok", async () => {
        const res = await request(app).get("/health");
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({ status: "ok" });
    });
});
```

`agents/scaffolder/blueprints/express-api/templates/package.json.jinja2`:
```json
{
    "name": "{{ project_name_kebab }}",
    "version": "0.1.0",
    "scripts": {
        "dev": "ts-node src/index.ts",
        "build": "tsc",
        "test": "jest"
    },
    "dependencies": {
        "express": "^4.18.0"
    },
    "devDependencies": {
        "@types/express": "^4.17.0",
        "@types/jest": "^29.0.0",
        "@types/supertest": "^6.0.0",
        "jest": "^29.0.0",
        "supertest": "^6.0.0",
        "ts-jest": "^29.0.0",
        "typescript": "^5.0.0"
    }
}
```

`agents/scaffolder/blueprints/express-api/templates/tsconfig.json.jinja2`:
```json
{
    "compilerOptions": {
        "target": "ES2022",
        "module": "commonjs",
        "outDir": "./dist",
        "strict": true,
        "esModuleInterop": true
    },
    "include": ["src/**/*"],
    "exclude": ["node_modules", "dist"]
}
```

`agents/scaffolder/blueprints/express-api/templates/README.md.jinja2`:
```markdown
# {{ project.name }}

> Generated by Scaffolder Agent from spec {{ spec_id }}

## Setup

```bash
npm install
npm run dev
```

## Test

```bash
npm test
```
```

- [ ] **Step 9: Create `agents/scaffolder/blueprints/nextjs-app/blueprint.json`**:

```json
{
    "name": "nextjs-app",
    "version": "1.0.0",
    "description": "Next.js 14 app with TypeScript and Jest",
    "language": "typescript",
    "files": [
        {"path": "src/app/page.tsx",        "template": "templates/page.tsx.jinja2",         "header": true},
        {"path": "src/app/layout.tsx",      "template": "templates/layout.tsx.jinja2",       "header": true},
        {"path": "tests/page.test.tsx",     "template": "templates/page.test.tsx.jinja2",    "header": true},
        {"path": "package.json",            "template": "templates/package.json.jinja2",     "header": false},
        {"path": "tsconfig.json",           "template": "templates/tsconfig.json.jinja2",    "header": false},
        {"path": "README.md",               "template": "templates/README.md.jinja2",        "header": false}
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

- [ ] **Step 10: Create nextjs-app templates**

`agents/scaffolder/blueprints/nextjs-app/templates/page.tsx.jinja2`:
```tsx
export default function Home() {
    return (
        <main>
            <h1>{{ project.name }}</h1>
        </main>
    );
}
```

`agents/scaffolder/blueprints/nextjs-app/templates/layout.tsx.jinja2`:
```tsx
export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
```

`agents/scaffolder/blueprints/nextjs-app/templates/page.test.tsx.jinja2`:
```tsx
import { render, screen } from "@testing-library/react";
import Home from "../src/app/page";

describe("Home", () => {
    it("renders heading", () => {
        render(<Home />);
        expect(screen.getByRole("heading")).toBeInTheDocument();
    });
});
```

`agents/scaffolder/blueprints/nextjs-app/templates/package.json.jinja2`:
```json
{
    "name": "{{ project_name_kebab }}",
    "version": "0.1.0",
    "scripts": {
        "dev": "next dev",
        "build": "next build",
        "test": "jest"
    },
    "dependencies": {
        "next": "^14.0.0",
        "react": "^18.0.0",
        "react-dom": "^18.0.0"
    },
    "devDependencies": {
        "@testing-library/jest-dom": "^6.0.0",
        "@testing-library/react": "^14.0.0",
        "@types/react": "^18.0.0",
        "jest": "^29.0.0",
        "typescript": "^5.0.0"
    }
}
```

`agents/scaffolder/blueprints/nextjs-app/templates/tsconfig.json.jinja2`:
```json
{
    "compilerOptions": {
        "target": "ES2022",
        "lib": ["dom", "dom.iterable", "esnext"],
        "allowJs": true,
        "strict": true,
        "jsx": "preserve",
        "moduleResolution": "bundler"
    },
    "include": ["src/**/*", "tests/**/*"],
    "exclude": ["node_modules"]
}
```

`agents/scaffolder/blueprints/nextjs-app/templates/README.md.jinja2`:
```markdown
# {{ project.name }}

> Generated by Scaffolder Agent from spec {{ spec_id }}

## Setup

```bash
npm install
npm run dev
```

## Test

```bash
npm test
```
```

- [ ] **Step 11: Smoke-test BlueprintResolver loads real blueprints**

```
python -c "
from agents.scaffolder.blueprint_resolver import BlueprintResolver
from agents.spec_writer.schema import SpecDoc, ProjectSection

r = BlueprintResolver()
for lang, ptype in [('python','api'),('python','cli'),('python','library'),('typescript','api'),('typescript','frontend')]:
    doc = SpecDoc(); doc.project = ProjectSection(name='Test', language=lang, type=ptype, framework='')
    bp, w = r.resolve(doc)
    print(f'{lang}/{ptype} -> {bp.name}  files={len(bp.files)}')
"
```
Expected output:
```
python/api -> fastapi-service  files=6
python/cli -> python-cli  files=6
python/library -> python-library  files=5
typescript/api -> express-api  files=6
typescript/frontend -> nextjs-app  files=6
```

- [ ] **Step 12: Commit blueprints**

```bash
git add agents/scaffolder/blueprints/
git commit -m "feat(scaffold): add 5 declarative blueprints with Jinja2 templates"
```

---

## Task 7: ScaffolderAgent

**Files:**
- Create: `agents/scaffolder/agent.py`
- Create: `agents/scaffolder/tests/test_agent.py`

- [ ] **Step 1: Write failing tests** — create `agents/scaffolder/tests/test_agent.py`:

```python
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
    """Create a minimal valid scaffold directory for testing show/validate/clean."""
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
    # spec_nonexistent does not exist → _generate raises FileNotFoundError
    agent._bus.publish(SpecCreated(agent_name="spec", payload={"spec_id": "spec_nonexistent"}))
    assert len(failed) == 1
    assert failed[0].status == "failed"


def test_list_returns_all_scaffolds(tmp_path):
    agent = _make_agent(tmp_path)
    _write_manifest(tmp_path, "spec_001")
    _write_manifest(tmp_path, "spec_002")
    result = agent.run(args=["list"])
    assert len(result["scaffolds"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest agents/scaffolder/tests/test_agent.py -v
```
Expected: `ModuleNotFoundError` — `agent` does not exist yet

- [ ] **Step 3: Create `agents/scaffolder/agent.py`**:

```python
"""ScaffolderAgent — generates project skeletons from SpecDocs."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import ScaffoldCleaned, ScaffoldCompleted, ScaffoldFailed
from agents.orchestrator.state import StateStore
from agents.scaffolder.blueprint_resolver import BlueprintResolver
from agents.scaffolder.file_generator import FileGenerator
from agents.scaffolder.structure_generator import StructureGenerator, _derive_name_variants
from agents.scaffolder.validator import ScaffoldValidator

DEFAULT_SCAFFOLDS_DIR = Path.home() / ".agent-orchestrator" / "scaffolds"


class ScaffolderAgent(BaseAgent):
    """Generates project skeletons from specs using declarative blueprints."""

    name = "scaffold"
    description = "Generates project skeletons from specs using declarative blueprints"

    def __init__(
        self,
        bus: EventBus,
        state: StateStore,
        registry=None,
        scaffolds_dir: Path = DEFAULT_SCAFFOLDS_DIR,
    ) -> None:
        super().__init__(bus=bus, state=state)
        self._registry = registry
        self._scaffolds_dir = Path(scaffolds_dir)
        self._resolver = BlueprintResolver()
        self._generator = StructureGenerator()
        self._file_gen = FileGenerator()
        self._validator = ScaffoldValidator()
        bus.subscribe("SpecCreated", self._on_spec_event)

    # ── Auto-generate ──────────────────────────────────────────────────────────

    def _on_spec_event(self, event) -> None:
        spec_id = event.payload.get("spec_id")
        if not spec_id:
            return
        try:
            self._generate(spec_id=spec_id, force=False)
        except Exception as exc:
            self.emit(ScaffoldFailed(
                agent_name=self.name,
                error=str(exc),
                payload={"spec_id": spec_id, "error": str(exc)},
            ))

    # ── Dispatch ───────────────────────────────────────────────────────────────

    def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
        args = list(args or [])
        parser = argparse.ArgumentParser(
            prog="orchestrator scaffold", add_help=False, exit_on_error=False
        )
        sub = parser.add_subparsers(dest="subcommand")

        gen_p = sub.add_parser("generate")
        gen_p.add_argument("spec_id")
        gen_p.add_argument("--force", action="store_true")

        re_p = sub.add_parser("re-scaffold")
        re_p.add_argument("spec_id")

        sub.add_parser("list")

        show_p = sub.add_parser("show")
        show_p.add_argument("spec_id")

        val_p = sub.add_parser("validate")
        val_p.add_argument("spec_id")

        clean_p = sub.add_parser("clean")
        clean_p.add_argument("spec_id")

        try:
            parsed = parser.parse_args(args)
        except (argparse.ArgumentError, SystemExit) as exc:
            available = "generate, re-scaffold, list, show, validate, clean"
            raise ValueError(
                f"Unknown scaffold subcommand. Available: {available}"
            ) from exc

        dispatch = {
            "generate":    self._cmd_generate,
            "re-scaffold": self._cmd_rescaffold,
            "list":        self._cmd_list,
            "show":        self._cmd_show,
            "validate":    self._cmd_validate,
            "clean":       self._cmd_clean,
        }
        if not parsed.subcommand or parsed.subcommand not in dispatch:
            available = ", ".join(sorted(dispatch))
            raise ValueError(f"Unknown scaffold subcommand. Available: {available}")
        return dispatch[parsed.subcommand](parsed)

    # ── Subcommands ────────────────────────────────────────────────────────────

    def _cmd_generate(self, parsed) -> Dict[str, Any]:
        return self._generate(spec_id=parsed.spec_id, force=parsed.force)

    def _cmd_rescaffold(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        if not (output_dir / "manifest.json").exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")

        from agents.spec_writer.formatter import SpecFormatter
        from agents.spec_writer.agent import DEFAULT_SPECS_DIR

        spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(parsed.spec_id)
        variants = _derive_name_variants(spec.project.name or "project")
        blueprint, _ = self._resolver.resolve(spec)
        context = {
            "spec_id": parsed.spec_id,
            "project": spec.project,
            "features": spec.features,
            "technical": spec.technical,
            "constraints": spec.constraints,
            "conventions": [],
            "blueprint_name": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).date().isoformat(),
            **variants,
        }
        rendered_files = self._generator.generate(blueprint, context)
        to_write = [
            rf for rf in rendered_files
            if not (output_dir / rf.relative_path).exists()
            or (output_dir / rf.relative_path).stat().st_size == 0
        ]
        written_paths = self._file_gen.write(to_write, output_dir, spec_id=parsed.spec_id)
        vr = self._validator.validate(output_dir)
        payload = {
            "spec_id": parsed.spec_id,
            "blueprint": blueprint.name,
            "output_dir": str(output_dir),
            "files_written": len(written_paths),
            "warnings": vr.warnings,
        }
        self.emit(ScaffoldCompleted(agent_name=self.name, payload=payload))
        print(f"Re-scaffolded {len(written_paths)} file(s) in {output_dir}")
        return payload

    def _cmd_list(self, parsed) -> Dict[str, Any]:
        scaffolds = []
        if self._scaffolds_dir.exists():
            for d in sorted(self._scaffolds_dir.iterdir()):
                mp = d / "manifest.json"
                if mp.exists():
                    try:
                        m = json.loads(mp.read_text(encoding="utf-8"))
                        scaffolds.append({
                            "spec_id":       m.get("spec_id", d.name),
                            "blueprint":     m.get("blueprint", "?"),
                            "scaffold_date": m.get("scaffold_date", "?"),
                        })
                    except Exception:
                        pass
        for s in scaffolds:
            print(f"  [{s['blueprint']:20}] {s['spec_id']}  {s['scaffold_date']}")
        return {"scaffolds": scaffolds}

    def _cmd_show(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        mp = output_dir / "manifest.json"
        if not mp.exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        print(f"Scaffold: {parsed.spec_id}  Blueprint: {manifest.get('blueprint')}")
        for f in manifest.get("files", []):
            exists = "✓" if (output_dir / f["relative_path"]).exists() else "✗"
            print(f"  {exists} {f['relative_path']}")
        return manifest

    def _cmd_validate(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        vr = self._validator.validate(output_dir)
        status = "OK" if vr.ok else "FAIL"
        print(f"Validation [{status}]: {parsed.spec_id}")
        for m in vr.missing:
            print(f"  ✗ missing: {m}")
        for e in vr.empty:
            print(f"  ⚠ empty:   {e}")
        for w in vr.warnings:
            print(f"  ⚠ {w}")
        return {"ok": vr.ok, "missing": vr.missing, "empty": vr.empty, "warnings": vr.warnings}

    def _cmd_clean(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        if not output_dir.exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")
        shutil.rmtree(output_dir)
        self.emit(ScaffoldCleaned(
            agent_name=self.name,
            payload={"spec_id": parsed.spec_id},
        ))
        print(f"Scaffold cleaned: {parsed.spec_id}")
        return {"spec_id": parsed.spec_id, "cleaned": True}

    # ── Internal pipeline ──────────────────────────────────────────────────────

    def _generate(self, spec_id: str, force: bool = False) -> Dict[str, Any]:
        from agents.spec_writer.formatter import SpecFormatter
        from agents.spec_writer.agent import DEFAULT_SPECS_DIR

        spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(spec_id)
        output_dir = self._scaffolds_dir / spec_id
        output_dir.mkdir(parents=True, exist_ok=True)

        conventions: list[str] = []
        if self._registry:
            try:
                result = self._registry.get("memory", self._bus, self._state).run(
                    args=["query", f"{spec.project.name} patterns"]
                )
                conventions = [e["content"] for e in result.get("results", [])]
            except Exception:
                pass

        variants = _derive_name_variants(spec.project.name or "project")
        blueprint, bp_warnings = self._resolver.resolve(spec)
        context = {
            "spec_id": spec_id,
            "project": spec.project,
            "features": spec.features,
            "technical": spec.technical,
            "constraints": spec.constraints,
            "conventions": conventions,
            "blueprint_name": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).date().isoformat(),
            **variants,
        }

        rendered_files = self._generator.generate(blueprint, context)
        written_paths = self._file_gen.write(rendered_files, output_dir, force=force, spec_id=spec_id)

        manifest = {
            "spec_id": spec_id,
            "blueprint": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(output_dir),
            "warnings": bp_warnings,
            "files": [
                {
                    "relative_path": rf.relative_path,
                    "header": rf.header,
                    "size_bytes": (output_dir / rf.relative_path).stat().st_size,
                }
                for rf in rendered_files
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        vr = self._validator.validate(output_dir)
        all_warnings = bp_warnings + vr.warnings

        payload = {
            "spec_id": spec_id,
            "blueprint": blueprint.name,
            "output_dir": str(output_dir),
            "files_written": len(written_paths),
            "warnings": all_warnings,
        }
        self.emit(ScaffoldCompleted(agent_name=self.name, payload=payload))
        print(f"Scaffold generated: {output_dir}")
        print(f"  Blueprint: {blueprint.name} v{blueprint.version}")
        print(f"  Files: {len(written_paths)}")
        for w in all_warnings:
            print(f"  ⚠ {w}")
        return payload
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest agents/scaffolder/tests/test_agent.py -v
```
Expected: all 10 tests PASS

- [ ] **Step 5: Run full scaffolder test suite**

```
pytest agents/scaffolder/tests/ -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/scaffolder/agent.py agents/scaffolder/tests/test_agent.py
git commit -m "feat(scaffold): add ScaffolderAgent with argparse dispatch and auto-subscribe"
```

---

## Task 8: Orchestrator & main.py wiring

**Files:**
- Modify: `agents/orchestrator/orchestrator.py`
- Modify: `main.py`

- [ ] **Step 1: Add `"scaffold"` to `INTENT_MAP` in `agents/orchestrator/orchestrator.py`**

In `INTENT_MAP` (after `"test"` entry), add:
```python
    "scaffold": ("scaffold", "args"),    # scaffolder receives full arg list
```

In the `run()` method, after the `if command == "test":` block, add:
```python
        if command == "scaffold":
            extra["registry"] = self._registry
```

The `INTENT_MAP` block should now look like:
```python
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":    ("code_auditor", "target"),
    "fix":      ("code_fixer",   "target"),
    "memory":   ("memory",       "args"),
    "spec":     ("spec",         "args"),
    "test":     ("testgen",      "args"),
    "scaffold": ("scaffold",     "args"),
}
```

And the extra-kwargs block in `run()`:
```python
        extra: Dict[str, Any] = {}
        if command == "spec":
            extra["registry"] = self._registry
        if command == "test":
            extra["registry"] = self._registry
        if command == "scaffold":
            extra["registry"] = self._registry
```

- [ ] **Step 2: Register ScaffolderAgent in `main.py`**

In `build_registry()`, after `registry.register(TestGeneratorAgent)`, add:
```python
    from agents.scaffolder.agent import ScaffolderAgent
    registry.register(ScaffolderAgent)
```

Also update the argparse help string in `main()`:
```python
    parser.add_argument("command", help="Command to run: audit | fix | memory | spec | test | scaffold | list")
```

- [ ] **Step 3: Verify orchestrator test still passes**

```
pytest agents/orchestrator/tests/test_orchestrator.py -v
```
Expected: all tests PASS

- [ ] **Step 4: Smoke-test the full CLI integration**

```
python main.py list
```
Expected output includes:
```
  scaffold: Generates project skeletons from specs using declarative blueprints
```

- [ ] **Step 5: Commit**

```bash
git add agents/orchestrator/orchestrator.py main.py
git commit -m "feat(scaffold): wire ScaffolderAgent into orchestrator INTENT_MAP and main.py"
```

---

## Task 9: Full test suite verification

- [ ] **Step 1: Run all scaffolder tests**

```
pytest agents/scaffolder/tests/ -v
```
Expected: all tests PASS, no warnings

- [ ] **Step 2: Run all orchestrator tests to confirm no regressions**

```
pytest agents/orchestrator/tests/ -v
```
Expected: all tests PASS

- [ ] **Step 3: Run complete test suite**

```
pytest agents/ -v --tb=short
```
Expected: all existing tests continue to PASS

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat(scaffold): complete Scaffolder Agent implementation

Adds ScaffolderAgent (registered as 'scaffold') with:
- BlueprintResolver: selects from 5 declarative blueprints
- StructureGenerator: Jinja2 rendering with spec context
- FileGenerator: file writing with .git safety check and header injection
- ScaffoldValidator: manifest-based completeness check
- Auto-scaffold on SpecCreated events
- CLI: generate, re-scaffold, list, show, validate, clean"
```
