# Test Generator Agent — Design Spec

**Date:** 2026-04-15  
**Status:** Approved  
**Agent name:** `testgen`  
**Registered in:** `AgentRegistry` via `INTENT_MAP["test"] = ("testgen", "args")`

---

## Overview

`TestGeneratorAgent` automatically generates test files (unit, integration, API) from:

1. A spec produced by `SpecWriterAgent` — generates tests *before* implementation exists (TDD red phase)
2. Existing source code — analyses signatures and generates tests retroactively
3. Both together — spec provides scenarios, code provides signatures

No LLM calls. All generation is template-driven (Jinja2) + static code analysis.

---

## File Structure

```
agents/test_generator/
├── __init__.py
├── agent.py          # TestGeneratorAgent — dispatch only, wires modules together
├── analyzer.py       # CodeAnalyzer — extracts signatures from .py/.ts/.js/.tsx
├── planner.py        # TestPlanner — maps spec features → test scenarios
├── writer.py         # TestWriter — renders Jinja2 templates, writes files to disk
├── validator.py      # TestValidator — syntax + import + subprocess run
├── templates/
│   ├── python/
│   │   ├── unit.py.j2        # per-function happy path + edge cases
│   │   ├── api.py.j2         # HTTP endpoint tests (status codes, methods)
│   │   ├── database.py.j2    # CRUD operation tests
│   │   └── fixtures.py.j2    # conftest.py fixtures + mock data
│   └── typescript/
│       ├── unit.ts.j2        # jest describe/it blocks per function
│       ├── api.ts.j2         # supertest/fetch endpoint tests
│       └── fixtures.ts.j2    # jest beforeEach setup + mock factories
└── tests/
    ├── __init__.py
    ├── test_analyzer.py
    ├── test_planner.py
    ├── test_writer.py
    └── test_validator.py
```

Template extension is `.j2` (Jinja2 convention, recognized by editors for syntax highlighting). Adding a new language requires only a new subdirectory with templates — no Python changes.

---

## CLI Commands

Routed via `INTENT_MAP["test"] = ("testgen", "args")`. The agent receives the full arg list and dispatches internally with argparse.

```
orchestrator test generate --from-spec <spec_id>
orchestrator test generate --from-code <path>
orchestrator test generate --from-code <path> --spec <spec_id>
orchestrator test coverage <path>
orchestrator test validate <test_path>
orchestrator test list
orchestrator test run <test_path>
```

---

## Module Designs

### CodeAnalyzer (`analyzer.py`)

Produces a language-agnostic `AnalyzedModule`:

```python
@dataclass
class FunctionInfo:
    name: str
    params: List[str]          # param names (types stripped)
    is_async: bool
    is_method: bool            # True if inside a class
    class_name: Optional[str]
    return_hint: str           # "None" | "str" | "unknown" | etc.
    raises: List[str]          # exception types in body (Python only)
    line: int

@dataclass
class AnalyzedModule:
    path: Path
    language: str              # "python" | "typescript"
    functions: List[FunctionInfo]
    classes: List[str]
    imports: List[str]
    has_tests: bool            # True if test_*.py or *.test.ts already exists
```

**Python:** `ast.parse()` — walks `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, `Raise` nodes. Zero new dependencies.

**TypeScript/JS:** Regex patterns for:
- `export (async )?function \w+\s*\(`
- `(const|let) \w+ = (async )?\(` (arrow functions)
- `class \w+` + indented method detection
- `export default` shapes

Ambiguous signatures get `params=["...args"]` and a `# TODO: verify signature` comment injected into the generated test.

---

### TestPlanner (`planner.py`)

Takes a `SpecDoc`, an `AnalyzedModule`, or both, and produces a `TestPlan`:

```python
@dataclass
class TestScenario:
    name: str                  # e.g. "test_create_user_returns_201"
    description: str
    target_function: str
    scenario_type: str         # "happy_path" | "edge_case" | "error" | "boundary"
    template: str              # "unit" | "api" | "database"
    source: str                # "spec:<feature_id>" | "code:<function_name>"
    tdd_pending: bool          # True when generated before implementation exists

@dataclass
class TestPlan:
    module_path: Path
    output_path: Path          # e.g. tests/test_my_module.py
    language: str
    scenarios: List[TestScenario]
    estimated_coverage: int    # % rough estimate based on function count
    fixtures_needed: bool
```

**From spec:** Each `Feature.acceptance_criteria` entry → one `TestScenario`. Features with `api_endpoints` in `TechnicalSpec` → `api` template. All scenarios get `tdd_pending=True`.

**From code:** Each `FunctionInfo` → minimum two scenarios (happy path + one edge case). Functions with `raises` entries → one error scenario per exception type. `estimated_coverage = min(90, (scenarios / functions) * 100)`.

**Combined:** Spec provides scenario names and descriptions; code provides function signatures to fill the template context.

---

### TestWriter (`writer.py`)

Loads Jinja2 templates and renders them to disk.

**Template context:**
```python
{
    "module_name": "my_module",
    "source_path": "src/my_module.py",
    "source_ref": "spec:spec_20260415_001",  # or "code:src/my_module.py"
    "generated_at": "2026-04-15T...",
    "functions": [...],        # List[FunctionInfo]
    "scenarios": [...],        # List[TestScenario]
    "fixtures_needed": True,
    "tdd_mode": True,
}
```

**Output file naming:**
- Python `src/foo/bar.py` → `src/foo/tests/test_bar.py`
- TypeScript `src/foo/bar.ts` → `src/foo/bar.test.ts`
- Spec only (no source file) → `tests/test_<spec_id>.py`

**TDD red-phase markers** (when `tdd_pending=True`):
```python
# Python
pytest.fail("Not implemented yet — TDD red phase")  # TODO: implement feature

# TypeScript
throw new Error("Not implemented yet — TDD red phase");  // TODO
```

**Generated file header** (always present):
```python
# Generated by TestGeneratorAgent
# Source: spec:spec_20260415_001
# Do not edit — regenerate with: orchestrator test generate --from-spec spec_20260415_001
```

---

### TestValidator (`validator.py`)

Three sequential checks, all non-blocking (file is always saved regardless of result):

1. **Syntax check** — `ast.parse()` for Python; `node --check` (if Node.js in PATH) for TypeScript. Errors recorded in result.

2. **Import check** — Scan generated import statements, `importlib.util.find_spec()` for each. Missing modules logged as warnings.

3. **Test run** — `subprocess.run(["pytest", path, "--tb=short", "-q"])` or `["npx", "jest", path]`. Parses stdout for pass/fail/error counts. Exit code 1 with only `ImportError`/`ModuleNotFoundError` in output → reclassified as `pending`.

**Result dataclass:**
```python
@dataclass
class ValidationResult:
    path: Path
    syntax_ok: bool
    missing_imports: List[str]
    passed: int
    failed: int
    pending: int       # failed due to missing implementation (TDD expected)
    errors: int        # unexpected failures
    output: str        # raw subprocess stdout
```

---

### TestGeneratorAgent (`agent.py`)

```python
class TestGeneratorAgent(BaseAgent):
    name = "testgen"
    description = "Generates test files from specs or existing code"

    def __init__(self, bus, state, registry=None, tests_dir=Path("tests")):
        super().__init__(bus=bus, state=state)
        self._registry = registry
        self._tests_dir = Path(tests_dir)
        self._analyzer = CodeAnalyzer()
        self._planner = TestPlanner()
        self._writer = TestWriter(templates_dir=Path(__file__).parent / "templates")
        self._validator = TestValidator()
```

**`generate` flow:**
1. Load spec via `registry.get("spec", ...)` if `--from-spec` given
2. `analyzer.analyze(path)` if `--from-code` given
3. `planner.plan(module=..., spec=...)` → `TestPlan`
4. `writer.write(plan)` → output path
5. `validator.validate(output_path)` → `ValidationResult`
6. `self.emit(TestsGenerated(payload={path, passed, pending, failed}))`

The agent queries `registry.get("memory", ...)` at startup to check for stored test conventions (e.g. preferred fixture patterns, test directory layout).

---

## EventBus Integration

### New events (added to `events.py`)

```python
@dataclass
class TestsGenerated(AgentEvent):
    event_type: str = "TestsGenerated"

@dataclass
class TestsPassed(AgentEvent):
    event_type: str = "TestsPassed"

@dataclass
class TestsFailed(AgentEvent):
    event_type: str = "TestsFailed"
    status: str = "failed"

@dataclass
class CoverageReport(AgentEvent):
    event_type: str = "CoverageReport"
```

### Subscriptions

- **Subscribes to:** `SpecCreated`, `SpecUpdated` — auto-generates tests when a spec is saved. Controlled by `auto_generate: bool = False` on the agent (opt-in, default off).
- **Publishes:** `TestsGenerated`, `TestsPassed`, `TestsFailed`, `CoverageReport`

---

## Orchestrator Integration

**`orchestrator.py` changes:**
```python
INTENT_MAP["test"] = ("testgen", "args")
```

**`orchestrator.run()` addition** (same pattern as `spec`):
```python
if command == "test":
    extra["registry"] = self._registry
```

**Agent registration** (wherever agents are registered at startup):
```python
from agents.test_generator.agent import TestGeneratorAgent
registry.register(TestGeneratorAgent)
```

---

## Testing the Agent

Each module has its own test file using `tmp_path` and isolated mocks. Pattern follows existing `test_agent.py` files.

**`test_analyzer.py`:** Writes temp `.py` and `.ts` files, asserts `FunctionInfo` fields.  
**`test_planner.py`:** Constructs minimal `AnalyzedModule` and `SpecDoc`, asserts scenario count and `tdd_pending` flags.  
**`test_writer.py`:** Runs writer against a `TestPlan`, asserts output file exists and contains expected markers.  
**`test_validator.py`:** Uses temp files with known syntax errors, missing imports, and passing stubs to assert each validation path.

---

## Constraints & Non-Goals

- No LLM calls — all generation is template-driven + static analysis
- No test runner installation — validator gracefully skips run step if `pytest`/`npx` not available
- Templates must remain independently editable without touching Python modules
- TDD red-phase tests must be clearly marked; the agent never silently hides expected failures
- TypeScript parsing is best-effort regex — complex generics and decorators may produce `# TODO: verify signature` markers
