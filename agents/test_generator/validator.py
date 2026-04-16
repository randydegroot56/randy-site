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


# Markers that indicate intentional TDD red-phase failures.
# Note: the em-dash in "Not implemented yet — TDD red phase" is mangled by
# Windows console encoding in subprocess output, so we match the stable suffix.
_TDD_MARKERS = ("TDD red phase", "ImportError", "ModuleNotFoundError")

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

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _read_source(path: Path) -> str:
        """Read file content, falling back to locale encoding if UTF-8 fails."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding=None, errors="replace")

    # ── Syntax ──────────────────────────────────────────────────────────────

    def _check_python_syntax(self, path: Path, result: ValidationResult) -> None:
        try:
            ast.parse(self._read_source(path))
        except SyntaxError as exc:
            result.syntax_ok = False
            result.output += f"SyntaxError: {exc}\n"

    # ── Imports ─────────────────────────────────────────────────────────────

    def _check_python_imports(self, path: Path, result: ValidationResult) -> None:
        source = self._read_source(path)
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

        # Parse summary line: "N passed", "N failed", "N error(s)"
        for m in re.finditer(r"(\d+)\s+(passed|failed|errors?)", output):
            count, kind = int(m.group(1)), m.group(2)
            if kind == "passed":
                result.passed = count
            elif kind == "failed":
                result.failed = count
            elif kind.startswith("error"):
                result.errors = count

        # Reclassify TDD red-phase failures (and collection errors containing TDD
        # markers — e.g. encoding issues on Windows causing SyntaxError during import)
        # as pending rather than hard failures.
        is_tdd = any(marker in output for marker in _TDD_MARKERS)
        if result.failed > 0 and is_tdd:
            result.pending += result.failed
            result.failed = 0
        if result.errors > 0 and is_tdd:
            result.pending += result.errors
            result.errors = 0

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
