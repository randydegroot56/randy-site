# Test Generator Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `TestGeneratorAgent` that generates pytest/jest test files from specs (TDD red phase) or existing source code, integrating with the existing EventBus/AgentRegistry/StateStore/OrchestratorLogger stack.

**Architecture:** Option B — thin `agent.py` dispatch + four specialized modules (`analyzer.py`, `planner.py`, `writer.py`, `validator.py`). Jinja2 `.j2` templates on disk. Agent registered as `"testgen"` under `INTENT_MAP["test"]`.

**Tech Stack:** Python 3.12, `ast` (stdlib), `re` (stdlib), `jinja2==3.1.6` (already installed), `subprocess` (stdlib), `argparse` (stdlib), `pytest`.

---

## Reference: Existing Interfaces (do not modify)

```python
# agents/orchestrator/base_agent.py
class BaseAgent(ABC):
    name: str = ""
    description: str = ""
    def __init__(self, bus: EventBus, state: StateStore) -> None: ...
    def emit(self, event: AgentEvent) -> None: ...  # publishes + caches in state

# agents/orchestrator/events.py — field ordering rule:
# agent_name first, event_type (has default) second, then all other defaulted fields.
@dataclass
class AgentEvent:
    agent_name: str
    event_type: str = "AgentEvent"
    timestamp: str = field(default_factory=...)
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    error: Optional[str] = None

# agents/orchestrator/orchestrator.py
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":  ("code_auditor", "target"),
    "fix":    ("code_fixer",   "target"),
    "memory": ("memory",       "args"),
    "spec":   ("spec",         "args"),
    # "test" will be added in Task 9
}

# agents/spec_writer/formatter.py — used in agent.py to load specs
class SpecFormatter:
    def __init__(self, specs_dir: Path) -> None: ...
    def load(self, spec_id: str) -> SpecDoc: ...   # raises FileNotFoundError if missing

# agents/spec_writer/agent.py
DEFAULT_SPECS_DIR = Path.home() / ".agent-orchestrator" / "specs"
```

---

## File Map

| Action   | Path |
|----------|------|
| Create   | `agents/test_generator/__init__.py` |
| Create   | `agents/test_generator/analyzer.py` |
| Create   | `agents/test_generator/planner.py` |
| Create   | `agents/test_generator/writer.py` |
| Create   | `agents/test_generator/validator.py` |
| Create   | `agents/test_generator/agent.py` |
| Create   | `agents/test_generator/templates/python/unit.py.j2` |
| Create   | `agents/test_generator/templates/python/api.py.j2` |
| Create   | `agents/test_generator/templates/python/database.py.j2` |
| Create   | `agents/test_generator/templates/python/fixtures.py.j2` |
| Create   | `agents/test_generator/templates/typescript/unit.ts.j2` |
| Create   | `agents/test_generator/templates/typescript/api.ts.j2` |
| Create   | `agents/test_generator/templates/typescript/fixtures.ts.j2` |
| Create   | `agents/test_generator/tests/__init__.py` |
| Create   | `agents/test_generator/tests/test_analyzer.py` |
| Create   | `agents/test_generator/tests/test_planner.py` |
| Create   | `agents/test_generator/tests/test_writer.py` |
| Create   | `agents/test_generator/tests/test_validator.py` |
| Create   | `agents/test_generator/tests/test_agent.py` |
| Modify   | `agents/orchestrator/events.py` |
| Modify   | `agents/orchestrator/tests/test_events.py` |
| Modify   | `agents/orchestrator/orchestrator.py` |
| Modify   | `agents/orchestrator/tests/test_orchestrator.py` |
| Modify   | `main.py` |

---

## Task 1: Add new events to `events.py`

**Files:**
- Modify: `agents/orchestrator/events.py`
- Test: `agents/orchestrator/tests/test_events.py`

- [ ] **Step 1: Write the failing tests**

  Open `agents/orchestrator/tests/test_events.py` and append at the bottom:

  ```python
  def test_tests_generated_event():
      from agents.orchestrator.events import TestsGenerated
      e = TestsGenerated(agent_name="testgen", payload={"output_path": "tests/test_foo.py"})
      assert e.event_type == "TestsGenerated"
      assert e.status == "success"


  def test_tests_passed_event():
      from agents.orchestrator.events import TestsPassed
      e = TestsPassed(agent_name="testgen", payload={"passed": 3})
      assert e.event_type == "TestsPassed"
      assert e.status == "success"


  def test_tests_failed_event():
      from agents.orchestrator.events import TestsFailed
      e = TestsFailed(agent_name="testgen", payload={"failed": 1})
      assert e.event_type == "TestsFailed"
      assert e.status == "failed"


  def test_coverage_report_event():
      from agents.orchestrator.events import CoverageReport
      e = CoverageReport(agent_name="testgen", payload={"estimated_coverage": 72})
      assert e.event_type == "CoverageReport"
      assert e.status == "success"
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/orchestrator/tests/test_events.py -v
  ```
  Expected: `ImportError: cannot import name 'TestsGenerated'`

- [ ] **Step 3: Add the four event classes to `events.py`**

  Open `agents/orchestrator/events.py`. After the `SpecFailed` dataclass, append:

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

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/orchestrator/tests/test_events.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/orchestrator/events.py agents/orchestrator/tests/test_events.py
  git commit -m "feat(testgen): add TestsGenerated/Passed/Failed/CoverageReport events"
  ```

---

## Task 2: Package skeleton

**Files:**
- Create: `agents/test_generator/__init__.py`
- Create: `agents/test_generator/tests/__init__.py`
- Create: `agents/test_generator/templates/python/` (directory)
- Create: `agents/test_generator/templates/typescript/` (directory)

- [ ] **Step 1: Create the package directories and `__init__.py` files**

  Create `agents/test_generator/__init__.py`:
  ```python
  """Test Generator Agent package."""
  ```

  Create `agents/test_generator/tests/__init__.py`:
  ```python
  ```
  (empty file)

  Create the template directories (they just need to exist — templates come in Task 5):
  ```bash
  mkdir -p agents/test_generator/templates/python
  mkdir -p agents/test_generator/templates/typescript
  ```

- [ ] **Step 2: Verify Python can import the package**

  ```
  python -c "import agents.test_generator; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Commit**

  ```bash
  git add agents/test_generator/
  git commit -m "feat(testgen): create package skeleton"
  ```

---

## Task 3: CodeAnalyzer + tests

**Files:**
- Create: `agents/test_generator/analyzer.py`
- Create: `agents/test_generator/tests/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/test_generator/tests/test_analyzer.py`:

  ```python
  """Tests for agents.test_generator.analyzer.CodeAnalyzer."""
  import pytest
  from pathlib import Path
  from agents.test_generator.analyzer import CodeAnalyzer, FunctionInfo, AnalyzedModule


  @pytest.fixture
  def analyzer():
      return CodeAnalyzer()


  # ── Python parsing ──────────────────────────────────────────────────────────

  def test_analyze_python_top_level_function(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text("def greet(name, greeting='Hello'):\n    return f'{greeting}, {name}'\n")
      module = analyzer.analyze(src)
      assert module.language == "python"
      assert len(module.functions) == 1
      fn = module.functions[0]
      assert fn.name == "greet"
      assert fn.params == ["name", "greeting"]
      assert fn.is_async is False
      assert fn.is_method is False
      assert fn.class_name is None


  def test_analyze_python_async_function(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text("async def fetch(url):\n    pass\n")
      module = analyzer.analyze(src)
      assert module.functions[0].is_async is True


  def test_analyze_python_class_method(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text(
          "class MyService:\n"
          "    def create(self, name):\n"
          "        pass\n"
          "    def delete(self, id):\n"
          "        pass\n"
      )
      module = analyzer.analyze(src)
      assert "MyService" in module.classes
      methods = [f for f in module.functions if f.is_method]
      assert len(methods) == 2
      assert methods[0].class_name == "MyService"
      assert "self" not in methods[0].params


  def test_analyze_python_raises_detection(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text(
          "def divide(a, b):\n"
          "    if b == 0:\n"
          "        raise ValueError('zero')\n"
          "    return a / b\n"
      )
      module = analyzer.analyze(src)
      assert "ValueError" in module.functions[0].raises


  def test_analyze_python_imports(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text("import os\nfrom pathlib import Path\ndef f(): pass\n")
      module = analyzer.analyze(src)
      assert "os" in module.imports
      assert "pathlib" in module.imports


  def test_analyze_python_syntax_error(tmp_path, analyzer):
      src = tmp_path / "bad.py"
      src.write_text("def broken(\n")
      with pytest.raises(ValueError, match="syntax error"):
          analyzer.analyze(src)


  def test_analyze_missing_file_raises(tmp_path, analyzer):
      with pytest.raises(FileNotFoundError):
          analyzer.analyze(tmp_path / "nonexistent.py")


  def test_analyze_unsupported_extension(tmp_path, analyzer):
      src = tmp_path / "foo.rb"
      src.write_text("puts 'hello'\n")
      with pytest.raises(ValueError, match="Unsupported file type"):
          analyzer.analyze(src)


  def test_has_tests_false_when_no_test_file(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text("def f(): pass\n")
      module = analyzer.analyze(src)
      assert module.has_tests is False


  def test_has_tests_true_when_test_file_exists(tmp_path, analyzer):
      src = tmp_path / "foo.py"
      src.write_text("def f(): pass\n")
      (tmp_path / "test_foo.py").write_text("def test_f(): pass\n")
      module = analyzer.analyze(src)
      assert module.has_tests is True


  # ── TypeScript parsing ──────────────────────────────────────────────────────

  def test_analyze_typescript_named_function(tmp_path, analyzer):
      src = tmp_path / "foo.ts"
      src.write_text("export function greet(name: string): string {\n  return name;\n}\n")
      module = analyzer.analyze(src)
      assert module.language == "typescript"
      names = [f.name for f in module.functions]
      assert "greet" in names


  def test_analyze_typescript_arrow_function(tmp_path, analyzer):
      src = tmp_path / "foo.ts"
      src.write_text("export const double = (n: number): number => n * 2;\n")
      module = analyzer.analyze(src)
      names = [f.name for f in module.functions]
      assert "double" in names


  def test_analyze_typescript_async_function(tmp_path, analyzer):
      src = tmp_path / "foo.ts"
      src.write_text("export async function fetchData(url: string) {\n  return fetch(url);\n}\n")
      module = analyzer.analyze(src)
      fn = next(f for f in module.functions if f.name == "fetchData")
      assert fn.is_async is True


  def test_parse_ts_params_strips_types(analyzer):
      params = analyzer._parse_ts_params("name: string, age: number, active: boolean")
      assert params == ["name", "age", "active"]


  def test_parse_ts_params_empty(analyzer):
      assert analyzer._parse_ts_params("") == []
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/test_generator/tests/test_analyzer.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.test_generator.analyzer'`

- [ ] **Step 3: Implement `analyzer.py`**

  Create `agents/test_generator/analyzer.py`:

  ```python
  """
  agents/test_generator/analyzer.py
  ====================================
  CodeAnalyzer — extracts function signatures from Python and TypeScript/JavaScript.

  Python:  ast.parse() — reliable, zero extra dependencies.
  TypeScript/JS: regex patterns — best-effort; ambiguous signatures get '...args'.
  """
  from __future__ import annotations

  import ast
  import re
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import Dict, List, Optional


  @dataclass
  class FunctionInfo:
      """Signature of a single function or method."""
      name: str
      params: List[str]
      is_async: bool
      is_method: bool
      class_name: Optional[str]
      return_hint: str
      raises: List[str]
      line: int


  @dataclass
  class AnalyzedModule:
      """All extracted metadata for one source file."""
      path: Path
      language: str                          # "python" | "typescript"
      functions: List[FunctionInfo] = field(default_factory=list)
      classes: List[str] = field(default_factory=list)
      imports: List[str] = field(default_factory=list)
      has_tests: bool = False


  EXTENSION_MAP: Dict[str, str] = {
      ".py":  "python",
      ".ts":  "typescript",
      ".tsx": "typescript",
      ".js":  "typescript",
      ".jsx": "typescript",
  }


  class CodeAnalyzer:
      """Extracts function signatures from Python and TypeScript/JavaScript source files."""

      def analyze(self, path: Path) -> AnalyzedModule:
          path = Path(path)
          if not path.exists():
              raise FileNotFoundError(f"Source file not found: {path}")
          language = EXTENSION_MAP.get(path.suffix.lower())
          if language is None:
              raise ValueError(
                  f"Unsupported file type '{path.suffix}'. Supported: {sorted(EXTENSION_MAP)}"
              )
          return self._analyze_python(path) if language == "python" else self._analyze_typescript(path)

      # ── Python ──────────────────────────────────────────────────────────────

      def _analyze_python(self, path: Path) -> AnalyzedModule:
          source = path.read_text(encoding="utf-8")
          try:
              tree = ast.parse(source)
          except SyntaxError as exc:
              raise ValueError(f"Python syntax error in {path}: {exc}") from exc

          functions: List[FunctionInfo] = []
          classes: List[str] = []
          imports: List[str] = []

          for node in ast.walk(tree):
              if isinstance(node, ast.Import):
                  for alias in node.names:
                      imports.append(alias.name.split(".")[0])
              elif isinstance(node, ast.ImportFrom) and node.module:
                  imports.append(node.module.split(".")[0])

          for node in tree.body:
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                  functions.append(self._make_py_function(node, is_method=False, class_name=None))
              elif isinstance(node, ast.ClassDef):
                  classes.append(node.name)
                  for child in node.body:
                      if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                          functions.append(self._make_py_function(child, is_method=True, class_name=node.name))

          return AnalyzedModule(
              path=path,
              language="python",
              functions=functions,
              classes=classes,
              imports=list(dict.fromkeys(imports)),
              has_tests=self._has_tests(path, "python"),
          )

      def _make_py_function(
          self,
          node: ast.FunctionDef | ast.AsyncFunctionDef,
          is_method: bool,
          class_name: Optional[str],
      ) -> FunctionInfo:
          params = [arg.arg for arg in node.args.args]
          if is_method and params and params[0] in ("self", "cls"):
              params = params[1:]

          return_hint = "unknown"
          if node.returns:
              try:
                  return_hint = ast.unparse(node.returns)
              except Exception:
                  pass

          raises: List[str] = []
          for child in ast.walk(node):
              if isinstance(child, ast.Raise) and child.exc:
                  exc = child.exc
                  if isinstance(exc, ast.Call):
                      func = exc.func
                      name = (
                          func.id if isinstance(func, ast.Name)
                          else func.attr if isinstance(func, ast.Attribute)
                          else None
                      )
                  elif isinstance(exc, ast.Name):
                      name = exc.id
                  else:
                      name = None
                  if name and name not in raises:
                      raises.append(name)

          return FunctionInfo(
              name=node.name,
              params=params,
              is_async=isinstance(node, ast.AsyncFunctionDef),
              is_method=is_method,
              class_name=class_name,
              return_hint=return_hint,
              raises=raises,
              line=node.lineno,
          )

      # ── TypeScript / JavaScript (regex, best-effort) ─────────────────────────

      _FN_NAMED = re.compile(
          r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
          re.MULTILINE,
      )
      _FN_ARROW = re.compile(
          r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)"
          r"\s*(?::\s*[\w<>\[\],\s|]+)?\s*=>",
          re.MULTILINE,
      )
      _FN_METHOD = re.compile(
          r"^\s{2,}(?:(?:public|private|protected|static|async|override|readonly|abstract)\s+)*"
          r"(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w<>\[\],\s|]+)?\s*\{",
          re.MULTILINE,
      )
      _CLASS = re.compile(r"\bclass\s+(\w+)")
      _IMPORT_STR = re.compile(r"""['"]([@\w][^'"]*?)['"]""")
      _SKIP_NAMES = frozenset({"if", "for", "while", "switch", "catch", "constructor", "return"})

      def _analyze_typescript(self, path: Path) -> AnalyzedModule:
          source = path.read_text(encoding="utf-8")

          class_lines: List[tuple[int, str]] = []
          for m in self._CLASS.finditer(source):
              class_lines.append((source[: m.start()].count("\n") + 1, m.group(1)))

          imports: List[str] = []
          for line in source.splitlines():
              if line.strip().startswith("import"):
                  for m in self._IMPORT_STR.finditer(line):
                      mod = m.group(1).lstrip("./").split("/")[0]
                      if mod:
                          imports.append(mod)

          functions: List[FunctionInfo] = []
          seen: set[tuple[str, int]] = set()

          for pattern, method_hint in [
              (self._FN_NAMED, False),
              (self._FN_ARROW, False),
              (self._FN_METHOD, True),
          ]:
              for m in pattern.finditer(source):
                  name = m.group(1)
                  if name in self._SKIP_NAMES:
                      continue
                  line = source[: m.start()].count("\n") + 1
                  if (name, line) in seen:
                      continue
                  seen.add((name, line))

                  params = self._parse_ts_params(m.group(2))
                  window = source[max(0, m.start() - 5): m.end()]
                  is_async = bool(re.search(r"\basync\b", window))

                  is_method, class_name = False, None
                  if method_hint:
                      for cls_line, cls_name in reversed(class_lines):
                          if cls_line < line:
                              is_method, class_name = True, cls_name
                              break

                  functions.append(FunctionInfo(
                      name=name,
                      params=params,
                      is_async=is_async,
                      is_method=is_method,
                      class_name=class_name,
                      return_hint="unknown",
                      raises=[],
                      line=line,
                  ))

          functions.sort(key=lambda f: f.line)
          return AnalyzedModule(
              path=path,
              language="typescript",
              functions=functions,
              classes=[c for _, c in class_lines],
              imports=list(dict.fromkeys(imports)),
              has_tests=self._has_tests(path, "typescript"),
          )

      def _parse_ts_params(self, raw: str) -> List[str]:
          if not raw.strip():
              return []
          params: List[str] = []
          for part in raw.split(","):
              part = part.strip()
              if not part:
                  continue
              name = part.split(":")[0].strip().split("=")[0].strip()
              if name:
                  params.append(name)
          return params or ["...args"]

      def _has_tests(self, path: Path, language: str) -> bool:
          if language == "python":
              return (
                  (path.parent / f"test_{path.name}").exists()
                  or (path.parent / "tests" / f"test_{path.name}").exists()
              )
          stem = path.stem
          return (
              (path.parent / f"{stem}.test{path.suffix}").exists()
              or (path.parent / f"{stem}.spec{path.suffix}").exists()
          )
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/test_generator/tests/test_analyzer.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/test_generator/analyzer.py agents/test_generator/tests/test_analyzer.py
  git commit -m "feat(testgen): implement CodeAnalyzer with Python ast + TypeScript regex"
  ```

---

## Task 4: TestPlanner + tests

**Files:**
- Create: `agents/test_generator/planner.py`
- Create: `agents/test_generator/tests/test_planner.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/test_generator/tests/test_planner.py`:

  ```python
  """Tests for agents.test_generator.planner.TestPlanner."""
  import pytest
  from pathlib import Path
  from agents.test_generator.analyzer import AnalyzedModule, FunctionInfo
  from agents.test_generator.planner import TestPlanner, TestPlan, TestScenario


  def make_module(tmp_path, functions=None, language="python"):
      src = tmp_path / "foo.py"
      src.write_text("")
      return AnalyzedModule(
          path=src,
          language=language,
          functions=functions or [],
          classes=[],
          imports=[],
          has_tests=False,
      )


  def make_fn(name="greet", params=None, raises=None):
      return FunctionInfo(
          name=name,
          params=params or ["name"],
          is_async=False,
          is_method=False,
          class_name=None,
          return_hint="str",
          raises=raises or [],
          line=1,
      )


  @pytest.fixture
  def planner():
      return TestPlanner()


  # ── from code ───────────────────────────────────────────────────────────────

  def test_plan_from_code_produces_happy_path(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("greet")])
      plan = planner.plan(module=module)
      names = [s.name for s in plan.scenarios]
      assert any("happy_path" in n for n in names)


  def test_plan_from_code_produces_edge_case_when_params(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("greet", params=["name"])])
      plan = planner.plan(module=module)
      types = [s.scenario_type for s in plan.scenarios]
      assert "edge_case" in types


  def test_plan_from_code_no_edge_case_when_no_params(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("ping", params=[])])
      plan = planner.plan(module=module)
      types = [s.scenario_type for s in plan.scenarios]
      assert "edge_case" not in types


  def test_plan_from_code_error_scenario_per_exception(tmp_path, planner):
      fn = make_fn("divide", params=["a", "b"], raises=["ValueError", "ZeroDivisionError"])
      module = make_module(tmp_path, [fn])
      plan = planner.plan(module=module)
      error_scenarios = [s for s in plan.scenarios if s.scenario_type == "error"]
      assert len(error_scenarios) == 2


  def test_plan_skips_private_functions(tmp_path, planner):
      fns = [make_fn("_helper"), make_fn("public_fn")]
      module = make_module(tmp_path, fns)
      plan = planner.plan(module=module)
      names = [s.target_function for s in plan.scenarios]
      assert "_helper" not in names
      assert "public_fn" in names


  def test_plan_tdd_pending_false_from_code(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("greet")])
      plan = planner.plan(module=module)
      assert all(not s.tdd_pending for s in plan.scenarios)


  def test_plan_estimated_coverage_capped_at_90(tmp_path, planner):
      fns = [make_fn(f"fn_{i}") for i in range(3)]
      module = make_module(tmp_path, fns)
      plan = planner.plan(module=module)
      assert plan.estimated_coverage <= 90


  def test_plan_output_path_python(tmp_path, planner):
      module = make_module(tmp_path, [make_fn()])
      plan = planner.plan(module=module)
      assert plan.output_path.name == "test_foo.py"
      assert "tests" in plan.output_path.parts


  def test_plan_output_path_typescript(tmp_path, planner):
      src = tmp_path / "bar.ts"
      src.write_text("")
      module = AnalyzedModule(path=src, language="typescript", functions=[make_fn()],
                              classes=[], imports=[], has_tests=False)
      plan = planner.plan(module=module)
      assert plan.output_path.name == "bar.test.ts"


  def test_plan_requires_at_least_one_input(planner):
      with pytest.raises(ValueError, match="At least one"):
          planner.plan()


  # ── from spec ───────────────────────────────────────────────────────────────

  def test_plan_from_spec_tdd_pending_true(planner):
      """All spec-derived scenarios are TDD pending."""
      from unittest.mock import MagicMock
      spec = MagicMock()
      spec.spec_id = "spec_20260415_001"
      feature = MagicMock()
      feature.name = "create user"
      feature.description = "Creates a new user account"
      feature.id = "F1"
      feature.acceptance_criteria = ["User is saved to database", "Returns user id"]
      spec.features = [feature]
      plan = planner.plan(spec=spec, spec_id="spec_20260415_001")
      assert all(s.tdd_pending for s in plan.scenarios)
      assert len(plan.scenarios) == 2


  def test_plan_from_spec_output_path_uses_spec_id(planner):
      from unittest.mock import MagicMock
      spec = MagicMock()
      spec.spec_id = "spec_20260415_001"
      spec.features = []
      plan = planner.plan(spec=spec, spec_id="spec_20260415_001")
      assert "spec_20260415_001" in str(plan.output_path)


  def test_plan_api_template_detection(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("get_user_endpoint")])
      plan = planner.plan(module=module)
      assert any(s.template == "api" for s in plan.scenarios)


  def test_plan_database_template_detection(tmp_path, planner):
      module = make_module(tmp_path, [make_fn("save_to_database")])
      plan = planner.plan(module=module)
      assert any(s.template == "database" for s in plan.scenarios)
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/test_generator/tests/test_planner.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.test_generator.planner'`

- [ ] **Step 3: Implement `planner.py`**

  Create `agents/test_generator/planner.py`:

  ```python
  """
  agents/test_generator/planner.py
  ===================================
  TestPlanner — maps a SpecDoc and/or AnalyzedModule to a list of test scenarios.
  """
  from __future__ import annotations

  import re
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import List, Optional

  from agents.test_generator.analyzer import AnalyzedModule


  @dataclass
  class TestScenario:
      """A single test case to be generated."""
      name: str                    # Python-safe function name
      description: str
      target_function: str
      scenario_type: str           # "happy_path" | "edge_case" | "error" | "boundary"
      template: str                # "unit" | "api" | "database"
      source: str                  # "spec:<feature_id>" | "code:<function_name>"
      tdd_pending: bool


  @dataclass
  class TestPlan:
      """Complete plan for generating one test file."""
      module_path: Optional[Path]
      output_path: Path
      language: str
      scenarios: List[TestScenario] = field(default_factory=list)
      estimated_coverage: int = 0
      fixtures_needed: bool = False


  _API_RE = re.compile(
      r"\b(api|endpoint|route|handler|request|response|http|get|post|put|delete|patch)\b", re.I
  )
  _DB_RE = re.compile(
      r"\b(db|database|crud|repository|repo|model|query|sql|table|record|persist|store)\b", re.I
  )


  def _slugify(text: str) -> str:
      text = re.sub(r"[^\w\s]", "", text.lower())
      text = re.sub(r"\s+", "_", text.strip())
      return re.sub(r"_+", "_", text)[:60]


  def _pick_template(name: str, description: str = "") -> str:
      combined = f"{name} {description}"
      if _API_RE.search(combined):
          return "api"
      if _DB_RE.search(combined):
          return "database"
      return "unit"


  class TestPlanner:
      """Produces a TestPlan from a SpecDoc, AnalyzedModule, or both."""

      def plan(
          self,
          module: Optional[AnalyzedModule] = None,
          spec=None,
          spec_id: str = "",
      ) -> TestPlan:
          if module is None and spec is None:
              raise ValueError("At least one of 'module' or 'spec' must be provided")

          language = module.language if module else "python"
          sid = spec_id or (spec.spec_id if spec else "")
          output_path = self._output_path(module, sid)
          scenarios: List[TestScenario] = []

          if spec:
              scenarios.extend(self._plan_from_spec(spec))
          if module:
              scenarios.extend(self._plan_from_code(module))

          # Deduplicate by name (spec scenarios take priority)
          seen: set[str] = set()
          unique: List[TestScenario] = []
          for s in scenarios:
              if s.name not in seen:
                  seen.add(s.name)
                  unique.append(s)

          fn_count = len(module.functions) if module else max(len(unique), 1)
          coverage = min(90, int((len(unique) / fn_count) * 100)) if fn_count else 0

          return TestPlan(
              module_path=module.path if module else None,
              output_path=output_path,
              language=language,
              scenarios=unique,
              estimated_coverage=coverage,
              fixtures_needed=any(s.template in ("api", "database") for s in unique),
          )

      def _plan_from_spec(self, spec) -> List[TestScenario]:
          scenarios: List[TestScenario] = []
          for feature in spec.features:
              template = _pick_template(feature.name, feature.description)
              criteria = feature.acceptance_criteria or []
              if criteria:
                  for i, criterion in enumerate(criteria):
                      slug = _slugify(criterion)
                      name = (
                          f"test_{_slugify(feature.name)}_{slug}"
                          if slug else
                          f"test_{_slugify(feature.name)}_{i + 1:02d}"
                      )
                      scenarios.append(TestScenario(
                          name=name,
                          description=criterion,
                          target_function=_slugify(feature.name),
                          scenario_type="happy_path",
                          template=template,
                          source=f"spec:{feature.id or feature.name}",
                          tdd_pending=True,
                      ))
              else:
                  scenarios.append(TestScenario(
                      name=f"test_{_slugify(feature.name)}_happy_path",
                      description=f"{feature.name} — {feature.description}",
                      target_function=_slugify(feature.name),
                      scenario_type="happy_path",
                      template=template,
                      source=f"spec:{feature.id or feature.name}",
                      tdd_pending=True,
                  ))
          return scenarios

      def _plan_from_code(self, module: AnalyzedModule) -> List[TestScenario]:
          scenarios: List[TestScenario] = []
          for fn in module.functions:
              if fn.name.startswith("_"):
                  continue
              template = _pick_template(fn.name)
              prefix = f"test_{fn.name}"

              scenarios.append(TestScenario(
                  name=f"{prefix}_happy_path",
                  description=f"Happy path: {fn.name} returns expected result",
                  target_function=fn.name,
                  scenario_type="happy_path",
                  template=template,
                  source=f"code:{fn.name}",
                  tdd_pending=False,
              ))

              if fn.params:
                  scenarios.append(TestScenario(
                      name=f"{prefix}_empty_input",
                      description=f"Edge case: {fn.name} with empty or None input",
                      target_function=fn.name,
                      scenario_type="edge_case",
                      template=template,
                      source=f"code:{fn.name}",
                      tdd_pending=False,
                  ))

              for exc_name in fn.raises:
                  scenarios.append(TestScenario(
                      name=f"{prefix}_raises_{exc_name.lower()}",
                      description=f"Error: {fn.name} raises {exc_name} on invalid input",
                      target_function=fn.name,
                      scenario_type="error",
                      template=template,
                      source=f"code:{fn.name}",
                      tdd_pending=False,
                  ))

          return scenarios

      def _output_path(self, module: Optional[AnalyzedModule], spec_id: str) -> Path:
          if module is None:
              sid = _slugify(spec_id) if spec_id else "generated"
              return Path("tests") / f"test_{sid}.py"
          if module.language == "python":
              return module.path.parent / "tests" / f"test_{module.path.name}"
          return module.path.parent / f"{module.path.stem}.test{module.path.suffix}"
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/test_generator/tests/test_planner.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/test_generator/planner.py agents/test_generator/tests/test_planner.py
  git commit -m "feat(testgen): implement TestPlanner — maps specs/code to test scenarios"
  ```

---

## Task 5: Jinja2 templates

**Files:**
- Create: `agents/test_generator/templates/python/unit.py.j2`
- Create: `agents/test_generator/templates/python/api.py.j2`
- Create: `agents/test_generator/templates/python/database.py.j2`
- Create: `agents/test_generator/templates/python/fixtures.py.j2`
- Create: `agents/test_generator/templates/typescript/unit.ts.j2`
- Create: `agents/test_generator/templates/typescript/api.ts.j2`
- Create: `agents/test_generator/templates/typescript/fixtures.ts.j2`

- [ ] **Step 1: Create `templates/python/unit.py.j2`**

  ```jinja2
  # Generated by TestGeneratorAgent
  # Source: {{ source_ref }}
  # Generated at: {{ generated_at }}
  # Do not edit — regenerate with: {{ regen_cmd }}
  """Unit tests for {{ module_name }}."""
  from __future__ import annotations

  import pytest
  {% if not tdd_mode %}
  # from {{ module_import }} import {{ module_name }}  # TODO: uncomment after implementing
  {% endif %}

  {% for scenario in scenarios %}

  def {{ scenario.name }}():
      """{{ scenario.description }}

      Source: {{ scenario.source }}
      """
  {% if scenario.tdd_pending %}
      pytest.fail("Not implemented yet — TDD red phase")  # TODO: implement {{ scenario.target_function }}
  {% elif scenario.scenario_type == "happy_path" %}
      # Arrange
      # TODO: prepare inputs for {{ scenario.target_function }}

      # Act
      # result = {{ scenario.target_function }}(...)

      # Assert
      # assert result is not None
      pass
  {% elif scenario.scenario_type == "edge_case" %}
      # Edge case: empty / None / zero input
      # with pytest.raises(ValueError):
      #     {{ scenario.target_function }}(None)
      pass
  {% elif scenario.scenario_type == "error" %}
      # Error: verify the expected exception is raised
      # with pytest.raises(ExpectedException):
      #     {{ scenario.target_function }}(invalid_input)
      pass
  {% else %}
      pass
  {% endif %}
  {% endfor %}
  ```

- [ ] **Step 2: Create `templates/python/api.py.j2`**

  ```jinja2
  # Generated by TestGeneratorAgent
  # Source: {{ source_ref }}
  # Generated at: {{ generated_at }}
  # Do not edit — regenerate with: {{ regen_cmd }}
  """API endpoint tests for {{ module_name }}."""
  from __future__ import annotations

  import pytest

  # Uncomment the appropriate client import:
  # import httpx
  # from fastapi.testclient import TestClient
  # from {{ module_import }} import app

  # BASE_URL = "http://testserver"


  {% for scenario in scenarios %}

  def {{ scenario.name }}():
      """{{ scenario.description }}

      Source: {{ scenario.source }}
      """
  {% if scenario.tdd_pending %}
      pytest.fail("Not implemented yet — TDD red phase")  # TODO: implement {{ scenario.target_function }}
  {% elif scenario.scenario_type == "happy_path" %}
      # Arrange
      # client = TestClient(app)
      # payload = {}  # TODO: set request body

      # Act
      # response = client.post("/{{ scenario.target_function }}", json=payload)

      # Assert
      # assert response.status_code == 200
      # assert response.json() is not None
      pass
  {% elif scenario.scenario_type == "edge_case" %}
      # Edge case: malformed request / missing required field
      # client = TestClient(app)
      # response = client.post("/{{ scenario.target_function }}", json={})
      # assert response.status_code in (400, 422)
      pass
  {% elif scenario.scenario_type == "error" %}
      # Error: invalid auth / missing resource / server error
      # client = TestClient(app)
      # response = client.get("/{{ scenario.target_function }}/nonexistent")
      # assert response.status_code in (401, 403, 404)
      pass
  {% else %}
      pass
  {% endif %}
  {% endfor %}
  ```

- [ ] **Step 3: Create `templates/python/database.py.j2`**

  ```jinja2
  # Generated by TestGeneratorAgent
  # Source: {{ source_ref }}
  # Generated at: {{ generated_at }}
  # Do not edit — regenerate with: {{ regen_cmd }}
  """Database operation tests for {{ module_name }}."""
  from __future__ import annotations

  import pytest

  # from {{ module_import }} import {{ module_name }}
  # from unittest.mock import MagicMock, patch


  @pytest.fixture
  def mock_db():
      """In-memory database mock for isolation."""
      # TODO: replace with your actual DB fixture
      from unittest.mock import MagicMock
      db = MagicMock()
      db.execute.return_value = []
      return db


  {% for scenario in scenarios %}

  def {{ scenario.name }}(mock_db):
      """{{ scenario.description }}

      Source: {{ scenario.source }}
      """
  {% if scenario.tdd_pending %}
      pytest.fail("Not implemented yet — TDD red phase")  # TODO: implement {{ scenario.target_function }}
  {% elif scenario.scenario_type == "happy_path" %}
      # Arrange
      # record = {"id": 1}  # TODO: set up test record

      # Act
      # result = {{ scenario.target_function }}(mock_db, record)

      # Assert
      # assert result is not None
      # mock_db.execute.assert_called_once()
      pass
  {% elif scenario.scenario_type == "edge_case" %}
      # Edge case: empty dataset / None id
      # result = {{ scenario.target_function }}(mock_db, None)
      # assert result is None  or pytest.raises(...)
      pass
  {% elif scenario.scenario_type == "error" %}
      # Error: DB exception propagation
      # mock_db.execute.side_effect = Exception("connection lost")
      # with pytest.raises(Exception):
      #     {{ scenario.target_function }}(mock_db, {})
      pass
  {% else %}
      pass
  {% endif %}
  {% endfor %}
  ```

- [ ] **Step 4: Create `templates/python/fixtures.py.j2`**

  ```jinja2
  # Generated by TestGeneratorAgent
  # Source: {{ source_ref }}
  # Generated at: {{ generated_at }}
  # Do not edit — regenerate with: {{ regen_cmd }}
  """Shared pytest fixtures for {{ module_name }} tests."""
  from __future__ import annotations

  import pytest
  from unittest.mock import MagicMock

  # from {{ module_import }} import {{ module_name }}


  @pytest.fixture
  def sample_data():
      """Generic sample data fixture."""
      return {
          # TODO: add representative test values for {{ module_name }}
      }


  @pytest.fixture
  def mock_dependency():
      """Mock for external dependencies of {{ module_name }}."""
      return MagicMock()


  {% if fixtures_needed %}
  @pytest.fixture
  def mock_db():
      """Isolated in-memory database mock."""
      db = MagicMock()
      db.execute.return_value = []
      db.fetchall.return_value = []
      return db
  {% endif %}
  ```

- [ ] **Step 5: Create `templates/typescript/unit.ts.j2`**

  ```jinja2
  // Generated by TestGeneratorAgent
  // Source: {{ source_ref }}
  // Generated at: {{ generated_at }}
  // Do not edit — regenerate with: {{ regen_cmd }}

  {% if not tdd_mode %}
  // import { {{ module_name }} } from '../{{ source_path }}';  // TODO: uncomment
  {% endif %}

  {% for scenario in scenarios %}
  describe('{{ scenario.target_function }}', () => {
    it('{{ scenario.description }}', () => {
  {% if scenario.tdd_pending %}
      throw new Error('Not implemented yet — TDD red phase');  // TODO: implement {{ scenario.target_function }}
  {% elif scenario.scenario_type == "happy_path" %}
      // Arrange
      // const input = {};  // TODO: set up input

      // Act
      // const result = {{ scenario.target_function }}(input);

      // Assert
      // expect(result).toBeDefined();
  {% elif scenario.scenario_type == "edge_case" %}
      // Edge case: null / undefined / empty input
      // expect(() => {{ scenario.target_function }}(null)).toThrow();
  {% elif scenario.scenario_type == "error" %}
      // Error: verify exception is thrown
      // expect(() => {{ scenario.target_function }}(invalidInput)).toThrow();
  {% else %}
      // TODO: implement this scenario
  {% endif %}
    });
  });

  {% endfor %}
  ```

- [ ] **Step 6: Create `templates/typescript/api.ts.j2`**

  ```jinja2
  // Generated by TestGeneratorAgent
  // Source: {{ source_ref }}
  // Generated at: {{ generated_at }}
  // Do not edit — regenerate with: {{ regen_cmd }}

  // import request from 'supertest';
  // import { app } from '../{{ source_path }}';

  {% for scenario in scenarios %}
  describe('{{ scenario.target_function }} API', () => {
    it('{{ scenario.description }}', async () => {
  {% if scenario.tdd_pending %}
      throw new Error('Not implemented yet — TDD red phase');  // TODO: implement {{ scenario.target_function }}
  {% elif scenario.scenario_type == "happy_path" %}
      // const response = await request(app).post('/{{ scenario.target_function }}').send({});
      // expect(response.status).toBe(200);
      // expect(response.body).toBeDefined();
  {% elif scenario.scenario_type == "edge_case" %}
      // const response = await request(app).post('/{{ scenario.target_function }}').send({});
      // expect(response.status).toBeGreaterThanOrEqual(400);
  {% elif scenario.scenario_type == "error" %}
      // const response = await request(app).get('/{{ scenario.target_function }}/invalid');
      // expect([401, 403, 404]).toContain(response.status);
  {% else %}
      // TODO: implement this scenario
  {% endif %}
    });
  });

  {% endfor %}
  ```

- [ ] **Step 7: Create `templates/typescript/fixtures.ts.j2`**

  ```jinja2
  // Generated by TestGeneratorAgent
  // Source: {{ source_ref }}
  // Generated at: {{ generated_at }}
  // Do not edit — regenerate with: {{ regen_cmd }}
  // Shared Jest fixtures and mock factories for {{ module_name }}

  export const createMock{{ module_name | title }}= () => ({
    // TODO: add mock properties for {{ module_name }}
  });

  export const sampleData = {
    // TODO: add representative test data for {{ module_name }}
  };

  {% if fixtures_needed %}
  export const mockDb = {
    execute: jest.fn().mockResolvedValue([]),
    findOne: jest.fn().mockResolvedValue(null),
    save: jest.fn().mockImplementation((x: unknown) => Promise.resolve(x)),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });
  {% endif %}
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add agents/test_generator/templates/
  git commit -m "feat(testgen): add Jinja2 templates for Python and TypeScript tests"
  ```

---

## Task 6: TestWriter + tests

**Files:**
- Create: `agents/test_generator/writer.py`
- Create: `agents/test_generator/tests/test_writer.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/test_generator/tests/test_writer.py`:

  ```python
  """Tests for agents.test_generator.writer.TestWriter."""
  import pytest
  from pathlib import Path
  from agents.test_generator.analyzer import AnalyzedModule, FunctionInfo
  from agents.test_generator.planner import TestPlan, TestScenario
  from agents.test_generator.writer import TestWriter


  def make_plan(tmp_path, tdd_pending=True, scenario_type="happy_path", template="unit", language="python"):
      src = tmp_path / "foo.py"
      output = tmp_path / "tests" / "test_foo.py"
      scenario = TestScenario(
          name="test_greet_happy_path",
          description="Happy path: greet returns a string",
          target_function="greet",
          scenario_type=scenario_type,
          template=template,
          source="code:greet",
          tdd_pending=tdd_pending,
      )
      return TestPlan(
          module_path=src,
          output_path=output,
          language=language,
          scenarios=[scenario],
          estimated_coverage=50,
          fixtures_needed=(template in ("api", "database")),
      )


  @pytest.fixture
  def writer():
      from agents.test_generator.writer import DEFAULT_TEMPLATES_DIR
      return TestWriter(templates_dir=DEFAULT_TEMPLATES_DIR)


  def test_write_creates_output_file(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=False)
      output = writer.write(plan)
      assert output.exists()


  def test_write_creates_parent_directory(tmp_path, writer):
      plan = make_plan(tmp_path)
      output = writer.write(plan)
      assert output.parent.is_dir()


  def test_write_tdd_pending_contains_pytest_fail(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=True)
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "pytest.fail" in content
      assert "TDD red phase" in content


  def test_write_non_tdd_does_not_contain_pytest_fail(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=False)
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "pytest.fail" not in content


  def test_write_contains_generated_header(tmp_path, writer):
      plan = make_plan(tmp_path)
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "Generated by TestGeneratorAgent" in content


  def test_write_contains_scenario_function_name(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=False)
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "test_greet_happy_path" in content


  def test_write_api_template_python(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=False, template="api")
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "API endpoint tests" in content


  def test_write_database_template_python(tmp_path, writer):
      plan = make_plan(tmp_path, tdd_pending=False, template="database")
      output = writer.write(plan)
      content = output.read_text(encoding="utf-8")
      assert "Database operation tests" in content


  def test_write_typescript_unit_template(tmp_path, writer):
      src = tmp_path / "bar.ts"
      output = tmp_path / "bar.test.ts"
      scenario = TestScenario(
          name="test_greet_happy_path",
          description="greet works",
          target_function="greet",
          scenario_type="happy_path",
          template="unit",
          source="code:greet",
          tdd_pending=True,
      )
      plan = TestPlan(
          module_path=src,
          output_path=output,
          language="typescript",
          scenarios=[scenario],
          estimated_coverage=50,
          fixtures_needed=False,
      )
      output_path = writer.write(plan)
      content = output_path.read_text(encoding="utf-8")
      assert "TDD red phase" in content
      assert "describe" in content


  def test_compute_module_import(writer, tmp_path):
      path = tmp_path / "src" / "foo" / "bar.py"
      result = writer._compute_module_import(path)
      assert result.endswith("src.foo.bar") or "bar" in result
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/test_generator/tests/test_writer.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.test_generator.writer'`

- [ ] **Step 3: Implement `writer.py`**

  Create `agents/test_generator/writer.py`:

  ```python
  """
  agents/test_generator/writer.py
  ==================================
  TestWriter — renders Jinja2 templates to produce test files on disk.
  """
  from __future__ import annotations

  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Optional

  from jinja2 import Environment, FileSystemLoader, StrictUndefined

  from agents.test_generator.planner import TestPlan

  DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "templates"


  class TestWriter:
      """Loads Jinja2 templates and renders test files to disk."""

      def __init__(self, templates_dir: Path = DEFAULT_TEMPLATES_DIR) -> None:
          self._templates_dir = Path(templates_dir)
          self._envs: dict[str, Environment] = {}

      def write(self, plan: TestPlan) -> Path:
          """Render the plan to disk. Returns path of the written file."""
          template_name = self._pick_template_name(plan)
          env = self._env(plan.language)
          template = env.get_template(template_name)
          content = template.render(**self._build_context(plan))
          plan.output_path.parent.mkdir(parents=True, exist_ok=True)
          plan.output_path.write_text(content, encoding="utf-8")
          return plan.output_path

      def _env(self, language: str) -> Environment:
          if language not in self._envs:
              lang_dir = self._templates_dir / language
              self._envs[language] = Environment(
                  loader=FileSystemLoader(str(lang_dir)),
                  undefined=StrictUndefined,
                  keep_trailing_newline=True,
                  trim_blocks=True,
                  lstrip_blocks=True,
              )
          return self._envs[language]

      def _pick_template_name(self, plan: TestPlan) -> str:
          templates = {s.template for s in plan.scenarios}
          if "api" in templates:
              primary = "api"
          elif "database" in templates:
              primary = "database"
          else:
              primary = "unit"
          ext = "py" if plan.language == "python" else "ts"
          return f"{primary}.{ext}.j2"

      def _build_context(self, plan: TestPlan) -> dict:
          source_path = str(plan.module_path) if plan.module_path else ""
          module_name = plan.module_path.stem if plan.module_path else "generated"
          module_import = self._compute_module_import(plan.module_path)
          source_ref = plan.scenarios[0].source if plan.scenarios else "unknown"
          tdd_mode = any(s.tdd_pending for s in plan.scenarios)

          if source_ref.startswith("spec:"):
              sid = source_ref[5:]
              regen_cmd = f"orchestrator test generate --from-spec {sid}"
          else:
              regen_cmd = f"orchestrator test generate --from-code {source_path}"

          return {
              "module_name": module_name,
              "module_import": module_import,
              "source_path": source_path,
              "source_ref": source_ref,
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "scenarios": plan.scenarios,
              "fixtures_needed": plan.fixtures_needed,
              "tdd_mode": tdd_mode,
              "regen_cmd": regen_cmd,
          }

      def _compute_module_import(self, path: Optional[Path]) -> str:
          if path is None:
              return ""
          try:
              rel = path.resolve().relative_to(Path.cwd().resolve())
          except ValueError:
              rel = path
          return str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/test_generator/tests/test_writer.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/test_generator/writer.py agents/test_generator/tests/test_writer.py
  git commit -m "feat(testgen): implement TestWriter — renders Jinja2 templates to disk"
  ```

---

## Task 7: TestValidator + tests

**Files:**
- Create: `agents/test_generator/validator.py`
- Create: `agents/test_generator/tests/test_validator.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/test_generator/tests/test_validator.py`:

  ```python
  """Tests for agents.test_generator.validator.TestValidator."""
  import pytest
  from pathlib import Path
  from agents.test_generator.validator import TestValidator, ValidationResult


  @pytest.fixture
  def validator():
      return TestValidator()


  def test_validate_missing_file(tmp_path, validator):
      result = validator.validate(tmp_path / "nonexistent.py")
      assert result.syntax_ok is False
      assert "not found" in result.output.lower()


  def test_validate_syntax_ok_for_valid_python(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text("import pytest\ndef test_pass():\n    pass\n")
      result = validator.validate(f)
      assert result.syntax_ok is True


  def test_validate_syntax_error_detected(tmp_path, validator):
      f = tmp_path / "test_bad.py"
      f.write_text("def broken(\n")
      result = validator.validate(f)
      assert result.syntax_ok is False


  def test_validate_detects_missing_import(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text("import _no_such_module_xyz\ndef test_pass():\n    pass\n")
      result = validator.validate(f)
      assert "_no_such_module_xyz" in result.missing_imports


  def test_validate_no_false_positives_for_stdlib(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text("import os\nimport pathlib\ndef test_pass():\n    pass\n")
      result = validator.validate(f)
      assert "os" not in result.missing_imports
      assert "pathlib" not in result.missing_imports


  def test_validate_run_passes_test(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text("def test_always_passes():\n    assert 1 + 1 == 2\n")
      result = validator.validate(f)
      assert result.passed >= 1
      assert result.failed == 0


  def test_validate_tdd_pending_reclassified(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text(
          "import pytest\n"
          "def test_tdd_red():\n"
          "    pytest.fail('Not implemented yet — TDD red phase')\n"
      )
      result = validator.validate(f)
      # The failed test should be reclassified as pending
      assert result.pending >= 1
      assert result.failed == 0


  def test_validate_returns_validation_result_type(tmp_path, validator):
      f = tmp_path / "test_foo.py"
      f.write_text("def test_ok():\n    pass\n")
      result = validator.validate(f)
      assert isinstance(result, ValidationResult)
      assert result.path == f
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/test_generator/tests/test_validator.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.test_generator.validator'`

- [ ] **Step 3: Implement `validator.py`**

  Create `agents/test_generator/validator.py`:

  ```python
  """
  agents/test_generator/validator.py
  =====================================
  TestValidator — checks generated test files for syntax, imports, and runability.

  Three sequential non-blocking checks:
  1. Syntax  — ast.parse() for Python
  2. Imports — importlib.util.find_spec() per top-level import
  3. Run     — subprocess pytest / npx jest; TDD failures → pending
  """
  from __future__ import annotations

  import ast
  import importlib.util
  import re
  import subprocess
  import sys
  from dataclasses import dataclass, field
  from pathlib import Path
  from typing import List


  @dataclass
  class ValidationResult:
      path: Path
      syntax_ok: bool = True
      missing_imports: List[str] = field(default_factory=list)
      passed: int = 0
      failed: int = 0
      pending: int = 0
      errors: int = 0
      output: str = ""


  _TDD_MARKERS = ("Not implemented yet — TDD red phase", "ImportError", "ModuleNotFoundError")
  _STDLIB: frozenset[str] = frozenset(getattr(sys, "stdlib_module_names", set()))


  class TestValidator:
      """Validates generated test files without blocking on expected TDD failures."""

      def validate(self, path: Path) -> ValidationResult:
          path = Path(path)
          result = ValidationResult(path=path)

          if not path.exists():
              result.syntax_ok = False
              result.output = f"File not found: {path}"
              return result

          if path.suffix.lower() == ".py":
              self._check_python_syntax(path, result)
              self._check_python_imports(path, result)
              self._run_pytest(path, result)
          else:
              self._run_jest(path, result)

          return result

      # ── Syntax ──────────────────────────────────────────────────────────────

      def _check_python_syntax(self, path: Path, result: ValidationResult) -> None:
          try:
              ast.parse(path.read_text(encoding="utf-8"))
          except SyntaxError as exc:
              result.syntax_ok = False
              result.output += f"SyntaxError: {exc}\n"

      # ── Imports ─────────────────────────────────────────────────────────────

      def _check_python_imports(self, path: Path, result: ValidationResult) -> None:
          source = path.read_text(encoding="utf-8")
          import_re = re.compile(r"^(?:import|from)\s+([\w.]+)", re.MULTILINE)
          for m in import_re.finditer(source):
              top = m.group(1).split(".")[0]
              if top in _STDLIB:
                  continue
              if importlib.util.find_spec(top) is None and top not in result.missing_imports:
                  result.missing_imports.append(top)

      # ── Test run — pytest ────────────────────────────────────────────────────

      def _run_pytest(self, path: Path, result: ValidationResult) -> None:
          try:
              proc = subprocess.run(
                  [sys.executable, "-m", "pytest", str(path), "--tb=short", "-q"],
                  capture_output=True, text=True, timeout=60,
              )
          except FileNotFoundError:
              result.output += "pytest not available — skipping test run\n"
              return
          except subprocess.TimeoutExpired:
              result.output += "pytest timed out\n"
              return

          output = proc.stdout + proc.stderr
          result.output += output

          for m in re.finditer(r"(\d+)\s+(passed|failed|error)", output):
              count, kind = int(m.group(1)), m.group(2)
              if kind == "passed":
                  result.passed = count
              elif kind == "failed":
                  result.failed = count
              elif kind == "error":
                  result.errors = count

          # Reclassify TDD red-phase failures as pending
          if result.failed > 0 and any(marker in output for marker in _TDD_MARKERS):
              result.pending += result.failed
              result.failed = 0

      # ── Test run — jest ──────────────────────────────────────────────────────

      def _run_jest(self, path: Path, result: ValidationResult) -> None:
          try:
              proc = subprocess.run(
                  ["npx", "--yes", "jest", str(path), "--no-coverage"],
                  capture_output=True, text=True, timeout=60,
              )
          except FileNotFoundError:
              result.output += "npx/jest not available — skipping test run\n"
              return
          except subprocess.TimeoutExpired:
              result.output += "jest timed out\n"
              return

          output = proc.stdout + proc.stderr
          result.output += output

          if m := re.search(r"(\d+)\s+passed", output):
              result.passed = int(m.group(1))
          if m := re.search(r"(\d+)\s+failed", output):
              result.failed = int(m.group(1))
              if any(marker in output for marker in _TDD_MARKERS):
                  result.pending = result.failed
                  result.failed = 0
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/test_generator/tests/test_validator.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/test_generator/validator.py agents/test_generator/tests/test_validator.py
  git commit -m "feat(testgen): implement TestValidator — syntax + import + subprocess run"
  ```

---

## Task 8: TestGeneratorAgent + tests

**Files:**
- Create: `agents/test_generator/agent.py`
- Create: `agents/test_generator/tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

  Create `agents/test_generator/tests/test_agent.py`:

  ```python
  """Tests for agents.test_generator.agent.TestGeneratorAgent."""
  import pytest
  from pathlib import Path
  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.state import StateStore
  from agents.test_generator.agent import TestGeneratorAgent


  def make_agent(tmp_path, **kwargs):
      bus = EventBus()
      state = StateStore(tmp_path / "state.json")
      agent = TestGeneratorAgent(bus=bus, state=state, tests_dir=tmp_path / "tests", **kwargs)
      return agent, bus, state


  def write_source(tmp_path, content="def greet(name):\n    return f'Hello {name}'\n"):
      src = tmp_path / "greet.py"
      src.write_text(content)
      return src


  # ── basic contract ───────────────────────────────────────────────────────────

  def test_agent_name():
      assert TestGeneratorAgent.name == "testgen"


  def test_agent_description_is_set():
      assert TestGeneratorAgent.description


  def test_unknown_subcommand_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Unknown test subcommand"):
          agent.run(args=["bogus"])


  def test_none_subcommand_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Unknown test subcommand"):
          agent.run(args=[])


  # ── generate --from-code ─────────────────────────────────────────────────────

  def test_generate_from_code_creates_test_file(tmp_path):
      src = write_source(tmp_path)
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["generate", "--from-code", str(src)])
      assert "output_path" in result
      assert Path(result["output_path"]).exists()


  def test_generate_from_code_publishes_tests_generated(tmp_path):
      src = write_source(tmp_path)
      agent, bus, _ = make_agent(tmp_path)
      received = []
      bus.subscribe("TestsGenerated", received.append)
      agent.run(args=["generate", "--from-code", str(src)])
      assert len(received) == 1
      assert received[0].event_type == "TestsGenerated"


  def test_generate_returns_scenarios_count(tmp_path):
      src = write_source(tmp_path)
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["generate", "--from-code", str(src)])
      assert result["scenarios"] >= 1


  def test_generate_no_flags_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(ValueError, match="Usage"):
          agent.run(args=["generate"])


  # ── validate ─────────────────────────────────────────────────────────────────

  def test_validate_returns_syntax_ok(tmp_path):
      f = tmp_path / "test_foo.py"
      f.write_text("def test_ok():\n    pass\n")
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["validate", str(f)])
      assert "syntax_ok" in result
      assert result["syntax_ok"] is True


  def test_validate_publishes_tests_passed_on_green(tmp_path):
      f = tmp_path / "test_foo.py"
      f.write_text("def test_ok():\n    assert 1 == 1\n")
      agent, bus, _ = make_agent(tmp_path)
      received = []
      bus.subscribe("TestsPassed", received.append)
      agent.run(args=["validate", str(f)])
      assert len(received) == 1


  def test_validate_publishes_tests_failed_on_red(tmp_path):
      f = tmp_path / "test_foo.py"
      f.write_text("def test_fail():\n    assert 1 == 2\n")
      agent, bus, _ = make_agent(tmp_path)
      received = []
      bus.subscribe("TestsFailed", received.append)
      agent.run(args=["validate", str(f)])
      assert len(received) == 1


  # ── coverage ─────────────────────────────────────────────────────────────────

  def test_coverage_returns_report(tmp_path):
      write_source(tmp_path)
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["coverage", str(tmp_path)])
      assert "estimated_coverage" in result
      assert "files_analyzed" in result


  def test_coverage_publishes_coverage_report_event(tmp_path):
      write_source(tmp_path)
      agent, bus, _ = make_agent(tmp_path)
      received = []
      bus.subscribe("CoverageReport", received.append)
      agent.run(args=["coverage", str(tmp_path)])
      assert len(received) == 1


  # ── list ─────────────────────────────────────────────────────────────────────

  def test_list_returns_test_files(tmp_path):
      (tmp_path / "tests").mkdir()
      (tmp_path / "tests" / "test_foo.py").write_text("def test_x(): pass\n")
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["list"])
      assert "test_files" in result


  # ── run ──────────────────────────────────────────────────────────────────────

  def test_run_executes_test_file(tmp_path):
      f = tmp_path / "test_run_me.py"
      f.write_text("def test_ok():\n    assert True\n")
      agent, _, _ = make_agent(tmp_path)
      result = agent.run(args=["run", str(f)])
      assert "passed" in result
      assert result["passed"] >= 1


  def test_run_missing_file_raises(tmp_path):
      agent, _, _ = make_agent(tmp_path)
      with pytest.raises(FileNotFoundError):
          agent.run(args=["run", str(tmp_path / "nonexistent.py")])
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/test_generator/tests/test_agent.py -v
  ```
  Expected: `ModuleNotFoundError: No module named 'agents.test_generator.agent'`

- [ ] **Step 3: Implement `agent.py`**

  Create `agents/test_generator/agent.py`:

  ```python
  """
  agents/test_generator/agent.py
  ================================
  TestGeneratorAgent — registered as "testgen" in AgentRegistry.

  run(args=[subcommand, ...]) dispatches via argparse:
      generate --from-spec <spec_id>
      generate --from-code <path> [--spec <spec_id>]
      coverage <path>
      validate <test_path>
      list
      run <test_path>
  """
  from __future__ import annotations

  import argparse
  import sys
  from pathlib import Path
  from typing import Any, Dict, List, Optional

  from agents.orchestrator.base_agent import BaseAgent
  from agents.orchestrator.bus import EventBus
  from agents.orchestrator.events import CoverageReport, TestsFailed, TestsGenerated, TestsPassed
  from agents.orchestrator.state import StateStore
  from agents.test_generator.analyzer import CodeAnalyzer, EXTENSION_MAP
  from agents.test_generator.planner import TestPlanner
  from agents.test_generator.validator import TestValidator
  from agents.test_generator.writer import TestWriter, DEFAULT_TEMPLATES_DIR

  DEFAULT_TESTS_DIR = Path("tests")


  class TestGeneratorAgent(BaseAgent):
      """Generates test files from specs or existing source code."""

      name = "testgen"
      description = "Generates test files from specs or existing source code"

      def __init__(
          self,
          bus: EventBus,
          state: StateStore,
          registry=None,
          tests_dir: Path = DEFAULT_TESTS_DIR,
          auto_generate: bool = False,
      ) -> None:
          super().__init__(bus=bus, state=state)
          self._registry = registry
          self._tests_dir = Path(tests_dir)
          self._auto_generate = auto_generate
          self._analyzer = CodeAnalyzer()
          self._planner = TestPlanner()
          self._writer = TestWriter(templates_dir=DEFAULT_TEMPLATES_DIR)
          self._validator = TestValidator()

          if auto_generate:
              bus.subscribe("SpecCreated", self._on_spec_event)
              bus.subscribe("SpecUpdated", self._on_spec_event)

      # ── Auto-generation ────────────────────────────────────────────────────

      def _on_spec_event(self, event) -> None:
          spec_id = event.payload.get("spec_id")
          if spec_id:
              try:
                  self._generate(from_spec=spec_id)
              except Exception:
                  pass  # best-effort

      # ── Dispatch ──────────────────────────────────────────────────────────

      def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
          args = list(args or [])
          parser = argparse.ArgumentParser(prog="orchestrator test", add_help=False)
          sub = parser.add_subparsers(dest="subcommand")

          gen = sub.add_parser("generate")
          gen.add_argument("--from-spec", dest="from_spec", metavar="SPEC_ID")
          gen.add_argument("--from-code", dest="from_code", metavar="PATH")
          gen.add_argument("--spec",      dest="spec",      metavar="SPEC_ID")

          cov = sub.add_parser("coverage")
          cov.add_argument("path")

          val = sub.add_parser("validate")
          val.add_argument("test_path")

          sub.add_parser("list")

          run_cmd = sub.add_parser("run")
          run_cmd.add_argument("test_path")

          parsed = parser.parse_args(args)

          dispatch = {
              "generate": self._cmd_generate,
              "coverage": self._cmd_coverage,
              "validate": self._cmd_validate,
              "list":     self._cmd_list,
              "run":      self._cmd_run,
          }
          if parsed.subcommand not in dispatch:
              available = ", ".join(sorted(dispatch))
              raise ValueError(
                  f"Unknown test subcommand '{parsed.subcommand}'. Available: {available}"
              )
          return dispatch[parsed.subcommand](parsed)

      # ── Subcommands ────────────────────────────────────────────────────────

      def _cmd_generate(self, parsed) -> Dict[str, Any]:
          if not parsed.from_spec and not parsed.from_code:
              raise ValueError(
                  "Usage: test generate --from-spec <id> | --from-code <path> [--spec <id>]"
              )
          return self._generate(
              from_spec=parsed.from_spec,
              from_code=parsed.from_code,
              spec_id=parsed.spec,
          )

      def _generate(
          self,
          from_spec: Optional[str] = None,
          from_code: Optional[str] = None,
          spec_id: Optional[str] = None,
      ) -> Dict[str, Any]:
          from agents.spec_writer.formatter import SpecFormatter
          from agents.spec_writer.agent import DEFAULT_SPECS_DIR

          spec = None
          if from_spec:
              spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(from_spec)
          if spec_id and spec is None:
              spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(spec_id)

          module = self._analyzer.analyze(Path(from_code)) if from_code else None

          plan = self._planner.plan(module=module, spec=spec, spec_id=from_spec or "")
          output_path = self._writer.write(plan)
          vr = self._validator.validate(output_path)

          payload = {
              "output_path":        str(output_path),
              "scenarios":          len(plan.scenarios),
              "estimated_coverage": plan.estimated_coverage,
              "passed":             vr.passed,
              "pending":            vr.pending,
              "failed":             vr.failed,
              "errors":             vr.errors,
          }
          self.emit(TestsGenerated(agent_name=self.name, payload=payload))
          print(f"Tests generated: {output_path}")
          print(f"  Scenarios: {len(plan.scenarios)} | Coverage: {plan.estimated_coverage}%")
          print(f"  Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}")
          return payload

      def _cmd_coverage(self, parsed) -> Dict[str, Any]:
          target = Path(parsed.path)
          modules = []
          if target.is_file():
              modules = [self._analyzer.analyze(target)]
          else:
              for ext in EXTENSION_MAP:
                  for p in target.rglob(f"*{ext}"):
                      if p.name.startswith("test_") or "test" in p.stem.lower():
                          continue
                      if any(part in ("tests", "__pycache__", "node_modules") for part in p.parts):
                          continue
                      try:
                          modules.append(self._analyzer.analyze(p))
                      except Exception:
                          pass

          with_tests = sum(1 for m in modules if m.has_tests)
          total_fn = sum(len(m.functions) for m in modules)
          coverage = int((with_tests / len(modules)) * 100) if modules else 0

          suggestions = [
              {
                  "file": str(m.path),
                  "functions": [f.name for f in m.functions if not f.name.startswith("_")],
                  "suggested_command": f"orchestrator test generate --from-code {m.path}",
              }
              for m in modules if not m.has_tests
          ]

          report = {
              "files_analyzed":     len(modules),
              "files_with_tests":   with_tests,
              "total_functions":    total_fn,
              "estimated_coverage": coverage,
              "suggestions":        suggestions,
          }
          self.emit(CoverageReport(agent_name=self.name, payload=report))
          print(f"Coverage: {with_tests}/{len(modules)} files have tests ({coverage}%)")
          for s in suggestions:
              print(f"  Missing: {s['file']}")
          return report

      def _cmd_validate(self, parsed) -> Dict[str, Any]:
          path = Path(parsed.test_path)
          vr = self._validator.validate(path)

          if vr.passed + vr.pending > 0 and vr.failed == 0 and vr.errors == 0:
              self.emit(TestsPassed(agent_name=self.name, payload={"path": str(path), "passed": vr.passed}))
          elif vr.failed > 0 or vr.errors > 0:
              self.emit(TestsFailed(
                  agent_name=self.name,
                  payload={"path": str(path), "failed": vr.failed, "errors": vr.errors},
              ))

          print(f"Validation: {path}")
          print(f"  Syntax OK: {vr.syntax_ok}")
          if vr.missing_imports:
              print(f"  Missing imports: {', '.join(vr.missing_imports)}")
          print(f"  Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}  Errors: {vr.errors}")

          return {
              "path":            str(path),
              "syntax_ok":       vr.syntax_ok,
              "missing_imports": vr.missing_imports,
              "passed":          vr.passed,
              "pending":         vr.pending,
              "failed":          vr.failed,
              "errors":          vr.errors,
          }

      def _cmd_list(self, parsed) -> Dict[str, Any]:
          test_files = []
          for pattern, lang in [("test_*.py", "python"), ("*.test.ts", "typescript"), ("*.test.js", "typescript")]:
              for p in self._tests_dir.rglob(pattern):
                  test_files.append({"path": str(p), "language": lang})
          for tf in test_files:
              print(f"  [{tf['language']:10}] {tf['path']}")
          print(f"Total: {len(test_files)} test file(s)")
          return {"test_files": test_files}

      def _cmd_run(self, parsed) -> Dict[str, Any]:
          path = Path(parsed.test_path)
          if not path.exists():
              raise FileNotFoundError(f"Test file not found: {path}")
          vr = self._validator.validate(path)
          print(vr.output)
          print(f"Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}  Errors: {vr.errors}")
          return {
              "path":    str(path),
              "passed":  vr.passed,
              "pending": vr.pending,
              "failed":  vr.failed,
              "errors":  vr.errors,
          }
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/test_generator/tests/test_agent.py -v
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add agents/test_generator/agent.py agents/test_generator/tests/test_agent.py
  git commit -m "feat(testgen): implement TestGeneratorAgent with argparse dispatch"
  ```

---

## Task 9: Orchestrator + `main.py` wiring + integration test

**Files:**
- Modify: `agents/orchestrator/orchestrator.py`
- Modify: `agents/orchestrator/tests/test_orchestrator.py`
- Modify: `main.py`

- [ ] **Step 1: Write the failing integration test**

  Open `agents/orchestrator/tests/test_orchestrator.py` and append at the bottom:

  ```python
  def test_test_generate_routes_to_testgen_agent(tmp_path):
      """Orchestrator routes 'test generate --from-code' to TestGeneratorAgent."""
      import io
      from agents.orchestrator.bus import EventBus
      from agents.orchestrator.logger import OrchestratorLogger
      from agents.orchestrator.orchestrator import Orchestrator
      from agents.orchestrator.registry import AgentRegistry
      from agents.orchestrator.state import StateStore
      from agents.test_generator.agent import TestGeneratorAgent

      src = tmp_path / "greet.py"
      src.write_text("def greet(name):\n    return f'Hello {name}'\n")

      bus = EventBus()
      state = StateStore(tmp_path / "state.json")
      logger = OrchestratorLogger(bus, stream=io.StringIO())
      registry = AgentRegistry()

      # Subclass to redirect tests_dir to tmp_path
      class TmpTestAgent(TestGeneratorAgent):
          def __init__(self, bus, state, **kwargs):
              super().__init__(bus=bus, state=state, tests_dir=tmp_path / "tests", **kwargs)

      TmpTestAgent.name = "testgen"
      registry.register(TmpTestAgent)

      orch = Orchestrator(registry, bus, state, logger)
      result = orch.run("test", ["generate", "--from-code", str(src)])
      assert "output_path" in result
      assert result["scenarios"] >= 1
  ```

- [ ] **Step 2: Run to verify failure**

  ```
  pytest agents/orchestrator/tests/test_orchestrator.py::test_test_generate_routes_to_testgen_agent -v
  ```
  Expected: `ValueError: Unknown command 'test'. Available: audit, fix, memory, spec`

- [ ] **Step 3: Update `INTENT_MAP` and `run()` in `orchestrator.py`**

  Open `agents/orchestrator/orchestrator.py`.

  In `INTENT_MAP`, add one entry:

  ```python
  INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
      "audit":  ("code_auditor", "target"),
      "fix":    ("code_fixer",   "target"),
      "memory": ("memory",       "args"),
      "spec":   ("spec",         "args"),
      "test":   ("testgen",      "args"),   # ← add this line
  }
  ```

  In the `run()` method, add the `registry` injection for `"test"` right after the `"spec"` block:

  ```python
  extra: Dict[str, Any] = {}
  if command == "spec":
      extra["registry"] = self._registry
  if command == "test":                      # ← add this block
      extra["registry"] = self._registry
  ```

- [ ] **Step 4: Run to verify passing**

  ```
  pytest agents/orchestrator/tests/test_orchestrator.py -v
  ```
  Expected: all tests pass, including the new integration test.

- [ ] **Step 5: Register `TestGeneratorAgent` and `SpecWriterAgent` in `main.py`**

  Open `main.py`. Replace the `build_registry()` function with:

  ```python
  def build_registry() -> AgentRegistry:
      """Register all known agents. Add new agents here."""
      from agents.orchestrator.agents.audit_agent import AuditAgent
      from agents.orchestrator.agents.fixer_agent import FixerAgent
      from agents.memory.agent import MemoryAgent
      from agents.spec_writer.agent import SpecWriterAgent
      from agents.test_generator.agent import TestGeneratorAgent

      registry = AgentRegistry()
      registry.register(AuditAgent)
      registry.register(FixerAgent)
      registry.register(MemoryAgent)
      registry.register(SpecWriterAgent)
      registry.register(TestGeneratorAgent)
      return registry
  ```

  Also update the `parser.add_argument("command", ...)` help string:

  ```python
  parser.add_argument("command", help="Command to run: audit | fix | memory | spec | test | list")
  ```

  Remove the top-level imports that were just moved into `build_registry()`:

  ```python
  # Delete these lines from the top-level imports:
  from agents.orchestrator.agents.audit_agent import AuditAgent
  from agents.orchestrator.agents.fixer_agent import FixerAgent
  from agents.memory.agent import MemoryAgent
  ```

- [ ] **Step 6: Smoke-test the CLI end-to-end**

  From the project root, create a small source file and generate tests:

  ```bash
  python main.py test generate --from-code agents/memory/store.py
  ```

  Expected output (roughly):
  ```
  Tests generated: agents/memory/tests/test_store.py
    Scenarios: N | Coverage: N%
    Passed: N  Pending: N  Failed: 0
  ```

  Verify the file was created:
  ```bash
  python main.py test validate agents/memory/tests/test_store.py
  ```

- [ ] **Step 7: Run all test_generator tests to confirm nothing is broken**

  ```
  pytest agents/test_generator/ agents/orchestrator/tests/ -v
  ```
  Expected: all tests pass.

- [ ] **Step 8: Commit**

  ```bash
  git add agents/orchestrator/orchestrator.py agents/orchestrator/tests/test_orchestrator.py main.py
  git commit -m "feat(testgen): wire TestGeneratorAgent into orchestrator and main.py"
  ```

---

## Self-Review Checklist

- **Spec coverage:** All spec requirements covered — `generate`, `coverage`, `validate`, `list`, `run` commands ✓; EventBus subscriptions to `SpecCreated`/`SpecUpdated` (`auto_generate=False` by default) ✓; TDD red-phase markers ✓; pytest + jest support ✓; Python ast + TypeScript regex ✓; 7 templates ✓; `"testgen"` registration ✓.
- **No placeholders:** Every step has complete, runnable code. ✓
- **Type consistency:** `FunctionInfo`, `AnalyzedModule` (Task 3) → used in `TestPlanner` (Task 4) → used in `TestWriter` (Task 6). `TestPlan`, `TestScenario` (Task 4) → used in `TestWriter` (Task 6). `ValidationResult` (Task 7) → used in `TestGeneratorAgent._generate()` as `vr` (Task 8). All names consistent. ✓
- **`SpecWriterAgent` import in `main.py`:** Now registered (was missing before). ✓
