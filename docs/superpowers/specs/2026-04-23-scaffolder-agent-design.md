# Scaffolder Agent — Design Spec

**Date:** 2026-04-23
**Status:** Approved
**Integrates with:** EventBus, AgentRegistry, StateStore, OrchestratorLogger, MemoryAgent, SpecWriterAgent

---

## Overview

The Scaffolder Agent reads a SpecDoc (produced by the Spec Writer Agent) and generates a complete project skeleton: directories, boilerplate files, configuration files, dependency manifests, and placeholder code. It uses a two-stage pipeline with a persistent `ScaffoldManifest` as the bridge between generation and validation. The result is a working skeleton that a Code Generator can fill in.

Auto-scaffolding is enabled by default: the agent subscribes to `SpecCreated` events and generates a scaffold immediately when a new spec is created.

---

## Architecture

### Pipeline

```
CLI input (args=[subcommand, ...])
   │
   ▼
ScaffolderAgent.run(args)
   │
   ├─ "generate"    → load SpecDoc → BlueprintResolver → StructureGenerator
   │                  → ScaffoldManifest (JSON) → FileGenerator → ScaffoldValidator
   │                  → ScaffoldCompleted event
   │
   ├─ "re-scaffold" → load existing manifest → FileGenerator (missing/zero-byte only)
   │                  → ScaffoldValidator → ScaffoldCompleted event
   │
   ├─ "list"        → scan scaffolds dir → print table
   ├─ "show"        → load manifest → print file tree
   ├─ "validate"    → load manifest → ScaffoldValidator → print report
   └─ "clean"       → remove scaffold dir + manifest → ScaffoldCleaned event

Auto-generate path (SpecCreated event):
   SpecCreated → _on_spec_event() → self._generate(spec_id)  (same pipeline as "generate")
```

### Storage

```
~/.agent-orchestrator/
  scaffolds/
    spec_20260423_001/
      manifest.json          ← ScaffoldManifest (written after generation)
      src/
        my_project/
          main.py
      tests/
        __init__.py
      pyproject.toml
      README.md
```

`DEFAULT_SCAFFOLDS_DIR = Path.home() / ".agent-orchestrator" / "scaffolds"`

---

## Components

### `blueprint_resolver.py` — BlueprintResolver

Selects and configures a project blueprint based on `spec.project.language` and `spec.project.type`. Reads `blueprints/<name>/blueprint.json` from disk. Always returns a Blueprint — never raises.

**Selection logic (top-down, first match wins):**

| Language | Type | Blueprint |
|---|---|---|
| `python` | `api`, `fullstack` | `fastapi-service` |
| `python` | `cli` | `python-cli` |
| `python` | `library` | `python-library` |
| `python` | anything else | `python-library` + WARNING |
| `typescript` | `api` | `express-api` |
| `typescript` | `frontend` | `nextjs-app` |
| `typescript` | anything else | `express-api` + WARNING |
| unknown / `"TODO"` | any | `python-library` + WARNING |

**Public API:**
```python
resolver.resolve(spec: SpecDoc) -> tuple[Blueprint, list[str]]
# Returns (blueprint, warnings). Warnings contain reason for fallback if used.
```

**`Blueprint` dataclass:**
```python
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

@dataclass
class BlueprintFile:
    path: str          # may contain Jinja2 expressions
    template: str      # relative path to .jinja2 file within blueprint dir
    header: bool       # whether to prepend the generated-by comment
```

---

### `structure_generator.py` — StructureGenerator

Reads a Blueprint and renders each Jinja2 template to produce `RenderedFile` objects. Does not touch the filesystem.

**Template context:**
```python
{
    # Spec fields
    "spec_id":     "spec_20260423_001",
    "project":     spec.project,        # .name, .type, .language, .framework
    "features":    spec.features,
    "technical":   spec.technical,      # .dependencies, .api_endpoints, etc.
    "constraints": spec.constraints,

    # Derived name variants
    "project_name_snake":  "my_project",   # lowercase, underscores
    "project_name_pascal": "MyProject",    # UpperCamelCase
    "project_name_kebab":  "my-project",   # lowercase, hyphens

    # Blueprint metadata
    "blueprint_name":    "fastapi-service",
    "blueprint_version": "1.0.0",
    "scaffold_date":     "2026-04-23",

    # Project conventions from MemoryAgent (category "patterns"), may be empty list
    "conventions":       ["use dependency injection", "prefer dataclasses over dicts"],
}
```

Missing optional spec fields produce empty defaults in the context — no exceptions:
`features → []`, `technical.dependencies → []`, `technical.api_endpoints → []`, all other missing fields → `""`.

**`RenderedFile` dataclass:**
```python
@dataclass
class RenderedFile:
    relative_path: str   # resolved from blueprint path (Jinja2 expanded)
    content: str         # fully rendered template content
    header: bool         # passed through from BlueprintFile
```

**Public API:**
```python
generator.generate(blueprint: Blueprint, context: dict) -> list[RenderedFile]
```

---

### `file_generator.py` — FileGenerator

Writes `RenderedFile` objects to disk. Creates parent directories automatically.

**Header comment format:**
```
# Generated by Scaffolder Agent from spec spec_20260423_001
```
- Python (`.py`): `# Generated by ...`
- TypeScript/JavaScript (`.ts`, `.js`): `// Generated by ...`
- JSON, TOML, YAML, Markdown: no header (these formats do not support comments uniformly or the content is user-facing)

Files with `header: false` in the blueprint receive no header regardless of extension.

**Safety check:** Before any write operation, `FileGenerator` checks whether `output_dir` contains a `.git` directory. If found, raises `ScaffoldError` unless `force=True`.

**Public API:**
```python
generator.write(files: list[RenderedFile], output_dir: Path, force: bool = False) -> list[Path]
# Returns list of written paths.
```

---

### `validator.py` — ScaffoldValidator

Verifies the scaffold is complete. Never raises — always returns a `ValidationResult`.

**Checks:**
- All files listed in `manifest.json` exist on disk
- No unexpectedly empty files (0 bytes) — unless `blueprint.json` marks them as intentionally empty
- `manifest.json` itself is present and parseable

**`ValidationResult` dataclass:**
```python
@dataclass
class ValidationResult:
    ok: bool
    missing: list[str]   # relative paths of missing files
    empty: list[str]     # relative paths of unexpectedly empty files
    warnings: list[str]  # non-blocking issues
```

**Public API:**
```python
validator.validate(output_dir: Path) -> ValidationResult
```

---

### `ScaffoldManifest`

Persisted as `<output_dir>/manifest.json` immediately after `FileGenerator.write()` completes.

```json
{
    "spec_id": "spec_20260423_001",
    "blueprint": "fastapi-service",
    "blueprint_version": "1.0.0",
    "scaffold_date": "2026-04-23T10:15:00+00:00",
    "output_dir": "/home/randy/.agent-orchestrator/scaffolds/spec_20260423_001",
    "warnings": [],
    "files": [
        {
            "relative_path": "src/my_project/main.py",
            "header": true,
            "size_bytes": 842
        }
    ]
}
```

`show` and `validate` read only this file — no Jinja2 re-execution needed.
`re-scaffold` compares `files[].relative_path` against disk and writes only missing or zero-byte files.

---

### `agent.py` — ScaffolderAgent

```python
class ScaffolderAgent(BaseAgent):
    name = "scaffold"
    description = "Generates project skeletons from specs using declarative blueprints"

    def __init__(self, bus, state, registry=None, scaffolds_dir=DEFAULT_SCAFFOLDS_DIR): ...

    def run(self, args=None, **kwargs): ...
```

Subcommand dispatch uses the same `dict`-based pattern as `MemoryAgent` and `SpecWriterAgent`.

Auto-subscribe to `SpecCreated` on construction (always enabled, unlike `TestGeneratorAgent`'s opt-in):
```python
bus.subscribe("SpecCreated", self._on_spec_event)
```

`_on_spec_event` runs the full generate pipeline; errors are caught and a `ScaffoldFailed` event is emitted — best-effort, does not crash the bus.

**`_generate()` internal method — full pipeline:**
```
1. Load SpecDoc via SpecFormatter
2. Query MemoryAgent for project conventions:
       registry.get("memory", bus, state).run(args=["query", project.name + " patterns"])
   → populate context["conventions"] from results in category "patterns"
   → if "memory" not in registry: context["conventions"] = []  (graceful fallback)
3. BlueprintResolver.resolve(spec) → (blueprint, warnings)
4. StructureGenerator.generate(blueprint, context) → list[RenderedFile]
5. FileGenerator.write(files, output_dir, force) → list[Path]
6. Write ScaffoldManifest to output_dir/manifest.json
7. ScaffoldValidator.validate(output_dir) → ValidationResult
8. Emit ScaffoldCompleted (or ScaffoldFailed on error)
```

---

## Blueprint Format

`blueprints/<name>/blueprint.json` is 100% declarative — no Python logic.

```json
{
    "name": "fastapi-service",
    "version": "1.0.0",
    "description": "FastAPI service with pytest and pyproject.toml",
    "language": "python",
    "files": [
        {
            "path": "src/{{ project_name_snake }}/main.py",
            "template": "templates/main.py.jinja2",
            "header": true
        },
        {
            "path": "pyproject.toml",
            "template": "templates/pyproject.toml.jinja2",
            "header": false
        },
        {
            "path": "tests/__init__.py",
            "template": "templates/tests_init.py.jinja2",
            "header": true
        },
        {
            "path": "tests/test_{{ project_name_snake }}.py",
            "template": "templates/test_main.py.jinja2",
            "header": true
        },
        {
            "path": "README.md",
            "template": "templates/README.md.jinja2",
            "header": false
        }
    ],
    "required_spec_fields": ["project.name", "project.language"],
    "optional_spec_fields": ["technical.dependencies", "features"]
}
```

Rules:
- `files[].path` may contain Jinja2 `{{ var }}` expressions (no logic, no `{% if %}`)
- Conditional content lives inside `.jinja2` template files, not in `blueprint.json`
- `header: false` on JSON, TOML, YAML, Markdown files

---

## File Structure

```
agents/scaffolder/
├── __init__.py
├── agent.py                  ← ScaffolderAgent (BaseAgent, name="scaffold")
├── blueprint_resolver.py     ← BlueprintResolver
├── structure_generator.py    ← StructureGenerator + RenderedFile
├── file_generator.py         ← FileGenerator + ScaffoldError
├── validator.py              ← ScaffoldValidator + ValidationResult
├── blueprints/
│   ├── fastapi-service/
│   │   ├── blueprint.json
│   │   └── templates/
│   │       ├── main.py.jinja2
│   │       ├── pyproject.toml.jinja2
│   │       ├── tests_init.py.jinja2
│   │       ├── test_main.py.jinja2
│   │       └── README.md.jinja2
│   ├── express-api/
│   │   ├── blueprint.json
│   │   └── templates/
│   ├── nextjs-app/
│   │   ├── blueprint.json
│   │   └── templates/
│   ├── python-cli/
│   │   ├── blueprint.json
│   │   └── templates/
│   └── python-library/
│       ├── blueprint.json
│       └── templates/
└── tests/
    ├── __init__.py
    ├── test_blueprint_resolver.py
    ├── test_structure_generator.py
    ├── test_file_generator.py
    └── test_validator.py
```

**Modified files:**
- `agents/orchestrator/events.py` — add `ScaffoldCompleted`, `ScaffoldFailed`, `ScaffoldCleaned`
- `agents/orchestrator/orchestrator.py` — add `"scaffold"` to `INTENT_MAP`, pass `registry`
- `main.py` — register `ScaffolderAgent` in `build_registry()`

---

## EventBus Integration

| Direction | Event | Trigger |
|---|---|---|
| Subscribes | `SpecCreated` | Auto-generate scaffold |
| Publishes | `ScaffoldCompleted` | After successful generate or re-scaffold |
| Publishes | `ScaffoldFailed` | On any unrecoverable error |
| Publishes | `ScaffoldCleaned` | After clean subcommand |

`ScaffoldCompleted` payload:
```python
{
    "spec_id":       "spec_20260423_001",
    "blueprint":     "fastapi-service",
    "output_dir":    "/home/randy/.agent-orchestrator/scaffolds/spec_20260423_001",
    "files_written": 5,
    "warnings":      [],
}
```

---

## CLI Commands

All routed through `python main.py scaffold <subcommand>`:

| Command | Args | Behaviour |
|---|---|---|
| `scaffold generate <spec_id>` | spec_id | Full pipeline: resolve → generate → write → manifest → validate |
| `scaffold generate <spec_id> --force` | spec_id + `--force` | Same, bypasses `.git` check |
| `scaffold re-scaffold <spec_id>` | spec_id | Load manifest, write only missing/empty files |
| `scaffold list` | — | Table of all scaffolds with spec_id, blueprint, date |
| `scaffold show <spec_id>` | spec_id | File tree from manifest |
| `scaffold validate <spec_id>` | spec_id | Validation report: missing/empty files |
| `scaffold clean <spec_id>` | spec_id | Remove scaffold directory + manifest |

---

## Orchestrator Integration

```python
# orchestrator.py
INTENT_MAP["scaffold"] = ("scaffold", "args")

# dispatch block
if command == "scaffold":
    extra["registry"] = self._registry
```

```python
# main.py build_registry()
from agents.scaffolder.agent import ScaffolderAgent
registry.register(ScaffolderAgent)
```

---

## Testing Strategy

All tests use `tmp_path` for file isolation — no writes to `~/.agent-orchestrator/`.

### `test_blueprint_resolver.py`
- `python` + `api` → selects `fastapi-service`, no warnings
- `python` + `cli` → selects `python-cli`
- `python` + `library` → selects `python-library`
- `typescript` + `frontend` → selects `nextjs-app`
- `language="TODO"` → selects `python-library` + warning in returned list
- `language="rust"` (unknown) → selects `python-library` + warning
- Always returns a Blueprint, never raises

### `test_structure_generator.py`
- Blueprint + minimal SpecDoc → correct `RenderedFile` objects
- `project_name_snake` / `pascal` / `kebab` correctly derived from `project.name`
- Template paths with Jinja2 expressions expand correctly (`src/{{ project_name_snake }}/main.py` → `src/my_project/main.py`)
- Missing optional spec fields → no exception, empty defaults in context

### `test_file_generator.py`
- Files written to `tmp_path`
- `header: true` → first line is correct header comment
- `header: false` (e.g. `.toml`) → no header prepended
- Directory with `.git` → `ScaffoldError` raised
- Directory with `.git` + `force=True` → files written successfully
- Subdirectories created automatically

### `test_validator.py`
- All manifest files present → `ok=True`, empty lists
- Missing file → `ok=False`, filename in `missing`
- Empty file (`header: false`) → appears in `empty`
- Corrupt `manifest.json` → `ok=False` with descriptive warning
- Never raises — always returns `ValidationResult`

### `test_agent.py`
- `generate` runs full pipeline, emits `ScaffoldCompleted`
- `SpecCreated` event triggers `_on_spec_event` → same pipeline
- `ScaffoldFailed` emitted (not raised) when pipeline errors in auto-generate path
- `clean` removes directory, emits `ScaffoldCleaned`
- Unknown subcommand → `ValueError`
- `generate` with non-existent `spec_id` → `FileNotFoundError`

---

## Constraints

- No LLM calls anywhere in the pipeline
- Blueprints are 100% declarative — no Python logic in `blueprint.json`
- Templates use Jinja2 with variables from the spec context
- Never scaffold into a directory with `.git` unless `force=True`
- Every generated file includes a header comment: `# Generated by Scaffolder Agent from spec <spec_id>` (where the file format supports comments)
- If spec has insufficient info for blueprint selection, use `python-library` (most conservative) and log a warning
- Query MemoryAgent for existing project conventions via AgentRegistry (not direct import)
- All persistence in `~/.agent-orchestrator/scaffolds/`
- Python only, same style as existing agents
- Full test coverage with pytest, `tmp_path` for isolation
