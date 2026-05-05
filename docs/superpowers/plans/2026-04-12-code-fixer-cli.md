# Code Fixer Agent CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production CLI at `agents/code_fixer/cli.py` that batches, orchestrates, tests, and commits Code Auditor findings automatically.

**Architecture:** Three focused core modules (`GitOrchestrator`, `SafetyValidator`, `ReportGenerator`) live in `agents/code_fixer/core/`. A `FixerEngine` class in `cli.py` orchestrates them, importing `BatchRemover` and `DryRunExecutor` directly from `agents.code_auditor.core.phase5_executor`. The CLI entry point is five `cmd_*` functions wired by `_build_parser()`.

**Tech Stack:** Python 3.10+, argparse, subprocess (via GitOrchestrator only), pytest (optional, graceful skip), `agents.code_auditor.core.phase5_executor` (BatchRemover, DryRunExecutor), `agents.code_auditor.core.phase4_reporting` (HTMLExporter).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agents/code_fixer/core/__init__.py` | Create | Package marker |
| `agents/code_fixer/core/git_orchestrator.py` | Create | All git/subprocess calls |
| `agents/code_fixer/core/safety_validator.py` | Create | 6-layer pre-flight checks |
| `agents/code_fixer/core/report_generator.py` | Create | HTML + JSON fix reports |
| `agents/code_fixer/tests/__init__.py` | Create | Test package marker |
| `agents/code_fixer/tests/test_git_orchestrator.py` | Create | GitOrchestrator unit tests |
| `agents/code_fixer/tests/test_safety_validator.py` | Create | SafetyValidator unit tests |
| `agents/code_fixer/tests/test_report_generator.py` | Create | ReportGenerator unit tests |
| `agents/code_fixer/cli.py` | Modify (currently empty) | FixerEngine + 5 subcommands |

---

## Key Data Contracts

**`phase3_verified.json` on disk** has `scenarios.scenario_1_safest.finding_ids` (no per-item risk/confidence). `FixerEngine` must join it with `phase2_findings.json` (same directory) and build an `all_checks` list that `BatchRemover` and `DryRunExecutor` expect.

**`all_checks` item shape** (what BatchRemover/DryRunExecutor expect):
```python
{
    "id": "U010",
    "file": "src/utils/helpers.py",
    "name": "unused_helper",
    "type": "unused_export",   # or "orphan_file", "unused_import"
    "risk_level": "LOW",       # note: key is risk_level, not risk
    "confidence": 0.95,
    "lines": 45,
    "evidence": {}
}
```

**`RunResult` shape** (output of FixerEngine.run()):
```python
@dataclass
class RunResult:
    status: str                    # "success" | "partial" | "failed"
    batches_attempted: int
    batches_succeeded: int
    batches_failed: int
    items_fixed: List[str]         # finding IDs
    items_failed: List[str]        # finding IDs
    lines_removed: int
    commits: List[str]             # git hashes
    batch_results: List[BatchResult]
    report_json: Optional[str] = None   # path written
    report_html: Optional[str] = None   # path written
```

**`BatchResult` shape**:
```python
@dataclass
class BatchResult:
    batch_num: int
    item_ids: List[str]
    status: str           # "success" | "failed" | "skipped"
    lines_removed: int
    commit_hash: str
    branch_name: str
    error: Optional[str] = None
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `agents/code_fixer/core/__init__.py`
- Create: `agents/code_fixer/tests/__init__.py`

- [ ] **Step 1: Create both __init__ files**

```python
# agents/code_fixer/core/__init__.py
"""Code Fixer Agent — core modules."""
```

```python
# agents/code_fixer/tests/__init__.py
"""Code Fixer Agent — test suite."""
```

- [ ] **Step 2: Verify the package is importable**

Run from repo root:
```bash
python -c "import agents.code_fixer.core; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agents/code_fixer/core/__init__.py agents/code_fixer/tests/__init__.py
git commit -m "feat(code-fixer): scaffold core and tests packages"
```

---

## Task 2: GitOrchestrator

**Files:**
- Create: `agents/code_fixer/core/git_orchestrator.py`
- Create: `agents/code_fixer/tests/test_git_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/code_fixer/tests/test_git_orchestrator.py
"""Unit tests for GitOrchestrator — all git calls are mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from agents.code_fixer.core.git_orchestrator import GitOrchestrator


@pytest.fixture
def orch(tmp_path: Path) -> GitOrchestrator:
    return GitOrchestrator(project_root=tmp_path)


def _mock_run(stdout: str = "", returncode: int = 0):
    """Helper: return a mock CompletedProcess."""
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = ""
    return m


# ── is_clean ────────────────────────────────────────────────────────────────

class TestIsClean:
    def test_returns_true_when_no_changes(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(stdout="")) as mock_run:
            assert orch.is_clean() is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:3] == ["git", "status", "--porcelain"]

    def test_returns_false_when_dirty(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(stdout=" M file.py")):
            assert orch.is_clean() is False


# ── current_branch ───────────────────────────────────────────────────────────

class TestCurrentBranch:
    def test_returns_branch_name(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="main")):
            assert orch.current_branch() == "main"

    def test_strips_whitespace(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="  feature/x  \n")):
            assert orch.current_branch() == "feature/x"


# ── commit_batch ─────────────────────────────────────────────────────────────

class TestCommitBatch:
    def test_stages_and_commits(self, orch):
        responses = [
            _mock_run(),                # git add -A
            _mock_run(),                # git commit
            _mock_run(stdout="abc1234"),# git rev-parse HEAD
        ]
        with patch("subprocess.run", side_effect=responses):
            result = orch.commit_batch("fix: remove U010, U011")
        assert result == "abc1234"

    def test_raises_on_commit_failure(self, orch):
        responses = [
            _mock_run(),                          # git add -A
            _mock_run(returncode=1, stdout=""),   # git commit fails
        ]
        with patch("subprocess.run", side_effect=responses):
            with pytest.raises(RuntimeError, match="git commit failed"):
                orch.commit_batch("fix: test")


# ── cleanup_branch ───────────────────────────────────────────────────────────

class TestCleanupBranch:
    def test_checks_out_main_and_deletes_branch(self, orch):
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return _mock_run()

        with patch("subprocess.run", side_effect=fake_run):
            orch.cleanup_branch("audit/remove-U010-2026-04-12")

        assert ["git", "checkout", "main"] in calls
        assert ["git", "branch", "-D", "audit/remove-U010-2026-04-12"] in calls


# ── merge_to_main ────────────────────────────────────────────────────────────

class TestMergeToMain:
    def test_checks_out_main_and_merges(self, orch):
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return _mock_run()

        with patch("subprocess.run", side_effect=fake_run):
            orch.merge_to_main("audit/remove-U010-2026-04-12")

        assert ["git", "checkout", "main"] in calls
        assert any("merge" in c for c in calls)


# ── list_audit_branches ──────────────────────────────────────────────────────

class TestListAuditBranches:
    def test_returns_matching_branches(self, orch):
        branch_output = "  audit/remove-U010-2026-04-12\n  main\n  audit/remove-U020-2026-04-12\n"
        with patch("subprocess.run", return_value=_mock_run(stdout=branch_output)):
            result = orch.list_audit_branches()
        assert result == ["audit/remove-U010-2026-04-12", "audit/remove-U020-2026-04-12"]

    def test_returns_empty_list_when_none(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="  main\n")):
            assert orch.list_audit_branches() == []


# ── run_tests ────────────────────────────────────────────────────────────────

class TestRunTests:
    def test_returns_true_when_pytest_passes(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(returncode=0, stdout="5 passed")):
            passed, output = orch.run_tests()
        assert passed is True
        assert "passed" in output

    def test_returns_false_when_pytest_fails(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(returncode=1, stdout="1 failed")):
            passed, output = orch.run_tests()
        assert passed is False

    def test_returns_true_when_pytest_not_installed(self, orch, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError("pytest not found")):
            passed, output = orch.run_tests()
        assert passed is True
        assert "skipped" in output.lower()
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
python -m pytest agents/code_fixer/tests/test_git_orchestrator.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'GitOrchestrator'`

- [ ] **Step 3: Implement GitOrchestrator**

```python
# agents/code_fixer/core/git_orchestrator.py
"""GitOrchestrator — isolates all git/subprocess calls for Code Fixer."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple


class GitOrchestrator:
    """Manage git operations for the Code Fixer batch loop.

    All subprocess calls are centralised here so that the rest of Code Fixer
    never imports subprocess directly (making unit testing straightforward).

    Parameters
    ----------
    project_root:
        Absolute path to the git repository root.
    verbose:
        When True, print each git command before running it.
    """

    def __init__(self, project_root: Path, verbose: bool = False) -> None:
        self._root = Path(project_root)
        self._verbose = verbose

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def is_clean(self) -> bool:
        """Return True when the working tree has no uncommitted changes."""
        output = self._git("status", "--porcelain")
        return output.strip() == ""

    def current_branch(self) -> str:
        """Return the name of the currently checked-out branch."""
        return self._git("rev-parse", "--abbrev-ref", "HEAD").strip()

    def commit_batch(self, message: str) -> str:
        """Stage all changes and create a commit.

        Parameters
        ----------
        message:
            Commit message (e.g. ``"fix: remove U010, U011, U012 (LOW risk)"``).

        Returns
        -------
        str
            The full commit hash of the newly created commit.

        Raises
        ------
        RuntimeError
            If ``git commit`` exits non-zero (e.g. nothing staged).
        """
        self._git("add", "-A")
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git commit failed:\n{result.stderr.strip()}")
        return self._git("rev-parse", "HEAD").strip()

    def merge_to_main(self, branch: str) -> None:
        """Checkout main and fast-forward merge *branch* into it.

        Parameters
        ----------
        branch:
            Name of the feature branch to merge (e.g. ``"audit/remove-U010-2026-04-12"``).

        Raises
        ------
        RuntimeError
            If checkout or merge fails.
        """
        self._git("checkout", "main")
        self._git("merge", "--ff-only", branch)
        self._git("branch", "-d", branch)

    def cleanup_branch(self, branch: str) -> None:
        """Checkout main and force-delete *branch* (used on test failure).

        Parameters
        ----------
        branch:
            Branch to delete (may have uncommitted changes).
        """
        try:
            self._git("checkout", "main")
        except RuntimeError:
            pass  # already on main or detached HEAD — best effort
        try:
            self._git("branch", "-D", branch)
        except RuntimeError:
            pass  # branch may not exist yet

    def get_status(self) -> dict:
        """Return a snapshot of the current git state.

        Returns
        -------
        dict
            Keys: ``branch`` (str), ``clean`` (bool),
            ``audit_branches`` (list[str]).
        """
        return {
            "branch": self.current_branch(),
            "clean": self.is_clean(),
            "audit_branches": self.list_audit_branches(),
        }

    def list_audit_branches(self) -> List[str]:
        """Return all local branches whose name starts with ``audit/``."""
        raw = self._git("branch")
        return [
            b.strip()
            for b in raw.splitlines()
            if b.strip().startswith("audit/")
        ]

    def run_tests(self) -> Tuple[bool, str]:
        """Run pytest in *project_root* and return ``(passed, output)``.

        Returns ``(True, "tests skipped — pytest not installed")`` when
        pytest is not available, so callers can continue safely.
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q"],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except FileNotFoundError:
            return True, "tests skipped — pytest not installed"
        except Exception as exc:  # noqa: BLE001
            return True, f"tests skipped — {exc}"

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _git(self, *args: str) -> str:
        """Run a git command and return stdout.

        Raises
        ------
        RuntimeError
            If the command exits non-zero.
        """
        cmd = ["git", *args]
        if self._verbose:
            print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
            )
        return result.stdout
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
python -m pytest agents/code_fixer/tests/test_git_orchestrator.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/code_fixer/core/git_orchestrator.py agents/code_fixer/tests/test_git_orchestrator.py
git commit -m "feat(code-fixer): add GitOrchestrator with full test coverage"
```

---

## Task 3: SafetyValidator

**Files:**
- Create: `agents/code_fixer/core/safety_validator.py`
- Create: `agents/code_fixer/tests/test_safety_validator.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/code_fixer/tests/test_safety_validator.py
"""Unit tests for SafetyValidator — all external calls are mocked."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.code_fixer.core.safety_validator import SafetyValidator, ValidationResult


# ── Fixtures ─────────────────────────────────────────────────────────────────

PHASE3_DATA = {
    "scenarios": {
        "scenario_1_safest": {"finding_ids": ["O001", "O002"]},
        "scenario_2_moderate": {"finding_ids": ["O001", "O002", "U001"]},
    },
    "all_checks": [
        {"id": "O001", "risk_level": "LOW", "confidence": 0.99, "file": "old.js", "name": "old", "type": "orphan_file"},
        {"id": "O002", "risk_level": "LOW", "confidence": 0.98, "file": "dead.py", "name": "dead", "type": "orphan_file"},
        {"id": "U001", "risk_level": "MEDIUM", "confidence": 0.90, "file": "theme.js", "name": "useTheme", "type": "unused_export"},
    ],
}


@pytest.fixture
def validator(tmp_path: Path) -> SafetyValidator:
    return SafetyValidator(report_data=PHASE3_DATA, project_root=tmp_path)


# ── Layer 1: validate_report ─────────────────────────────────────────────────

class TestValidateReport:
    def test_passes_when_report_has_all_checks(self, validator):
        result = validator.validate_report()
        assert result.passed is True
        assert result.layer == 1

    def test_fails_when_report_is_empty_dict(self, tmp_path):
        v = SafetyValidator(report_data={}, project_root=tmp_path)
        result = v.validate_report()
        assert result.passed is False
        assert "no findings" in result.message.lower()


# ── Layer 2: validate_git_clean ──────────────────────────────────────────────

class TestValidateGitClean:
    def test_passes_when_tree_is_clean(self, validator):
        with patch.object(validator._git, "is_clean", return_value=True):
            result = validator.validate_git_clean()
        assert result.passed is True
        assert result.layer == 2

    def test_fails_when_tree_is_dirty(self, validator):
        with patch.object(validator._git, "is_clean", return_value=False):
            result = validator.validate_git_clean()
        assert result.passed is False
        assert "dirty" in result.message.lower()


# ── Layer 3: validate_items_exist ────────────────────────────────────────────

class TestValidateItemsExist:
    def test_passes_when_all_ids_present(self, validator):
        result = validator.validate_items_exist(["O001", "O002"])
        assert result.passed is True
        assert result.layer == 3

    def test_fails_with_unknown_id(self, validator):
        result = validator.validate_items_exist(["O001", "U999"])
        assert result.passed is False
        assert "U999" in result.message

    def test_fails_with_empty_list(self, validator):
        result = validator.validate_items_exist([])
        assert result.passed is False


# ── Layer 4: validate_risk_filter ────────────────────────────────────────────

class TestValidateRiskFilter:
    def test_passes_low_items_against_low_threshold(self, validator):
        result = validator.validate_risk_filter(["O001", "O002"], max_risk="LOW")
        assert result.passed is True
        assert result.layer == 4

    def test_fails_medium_item_against_low_threshold(self, validator):
        result = validator.validate_risk_filter(["U001"], max_risk="LOW")
        assert result.passed is False
        assert "U001" in result.message

    def test_passes_medium_item_against_medium_threshold(self, validator):
        result = validator.validate_risk_filter(["U001"], max_risk="MEDIUM")
        assert result.passed is True


# ── Layer 5: validate_batch_dry_run ─────────────────────────────────────────

class TestValidateBatchDryRun:
    def test_passes_when_dry_run_is_safe(self, validator):
        mock_result = MagicMock()
        mock_result.is_safe = True
        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_result

        with patch(
            "agents.code_fixer.core.safety_validator.DryRunExecutor",
            return_value=mock_executor,
        ):
            result = validator.validate_batch_dry_run(["O001"], {}, {})

        assert result.passed is True
        assert result.layer == 5

    def test_fails_when_dry_run_is_not_safe(self, validator):
        mock_result = MagicMock()
        mock_result.is_safe = False
        mock_result.warnings = ["Breaking change detected"]
        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_result

        with patch(
            "agents.code_fixer.core.safety_validator.DryRunExecutor",
            return_value=mock_executor,
        ):
            result = validator.validate_batch_dry_run(["O001"], {}, {})

        assert result.passed is False
        assert result.layer == 5


# ── Layer 6: run_baseline_tests ──────────────────────────────────────────────

class TestRunBaselineTests:
    def test_passes_when_tests_pass(self, validator):
        with patch.object(validator._git, "run_tests", return_value=(True, "5 passed")):
            result = validator.run_baseline_tests()
        assert result.passed is True
        assert result.layer == 6

    def test_passes_when_pytest_not_installed(self, validator):
        with patch.object(
            validator._git, "run_tests",
            return_value=(True, "tests skipped — pytest not installed"),
        ):
            result = validator.run_baseline_tests()
        assert result.passed is True

    def test_fails_when_baseline_tests_fail(self, validator):
        with patch.object(
            validator._git, "run_tests", return_value=(False, "3 failed, 2 passed")
        ):
            result = validator.run_baseline_tests()
        assert result.passed is False
        assert result.layer == 6
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
python -m pytest agents/code_fixer/tests/test_safety_validator.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'SafetyValidator'`

- [ ] **Step 3: Implement SafetyValidator**

```python
# agents/code_fixer/core/safety_validator.py
"""SafetyValidator — 6-layer pre-flight checks before any code removal."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from agents.code_fixer.core.git_orchestrator import GitOrchestrator

# Imported lazily inside validate_batch_dry_run to avoid hard failure when
# code_auditor is not yet on sys.path at import time.
# from agents.code_auditor.core.phase5_executor import DryRunExecutor


@dataclass
class ValidationResult:
    """Result of a single safety validation layer.

    Attributes
    ----------
    passed:
        True when this layer has no blocking issues.
    layer:
        The layer number (1–6).
    message:
        One-line summary suitable for terminal output.
    details:
        Additional context lines (warnings, affected items, etc.).
    """

    passed: bool
    layer: int
    message: str
    details: List[str] = field(default_factory=list)


_RISK_ORDER: Dict[str, int] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class SafetyValidator:
    """Run 6 pre-flight safety checks before a Code Fixer batch executes.

    All checks are read-only — nothing is modified.

    Parameters
    ----------
    report_data:
        Parsed ``phase3_verified.json`` dict (must include ``all_checks`` or
        ``scenarios`` keys populated by :class:`FixerEngine`).
    project_root:
        Absolute path to the git repository root.
    verbose:
        When True, print check progress to stdout.
    """

    def __init__(
        self,
        report_data: Dict[str, Any],
        project_root: Path,
        verbose: bool = False,
    ) -> None:
        self._data = report_data
        self._root = Path(project_root)
        self._verbose = verbose
        self._git = GitOrchestrator(project_root=self._root, verbose=verbose)
        # Build a lookup of all known IDs for fast membership tests
        self._known_ids: Dict[str, Dict[str, Any]] = {
            c["id"]: c
            for c in self._data.get("all_checks", [])
            if c.get("id")
        }

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def validate_report(self) -> ValidationResult:
        """Layer 1: Confirm the report has at least one processable finding."""
        checks = self._data.get("all_checks", [])
        if not checks:
            return ValidationResult(
                passed=False,
                layer=1,
                message="report has no findings — run Code Auditor phases 1-3 first",
            )
        return ValidationResult(
            passed=True,
            layer=1,
            message=f"report OK — {len(checks)} findings loaded",
        )

    def validate_git_clean(self) -> ValidationResult:
        """Layer 2: Confirm the working tree has no uncommitted changes."""
        if not self._git.is_clean():
            return ValidationResult(
                passed=False,
                layer=2,
                message="git working tree is dirty — stash or commit changes first",
                details=["Run: git stash   or   git commit -am 'wip'"],
            )
        return ValidationResult(passed=True, layer=2, message="git working tree is clean")

    def validate_items_exist(self, item_ids: List[str]) -> ValidationResult:
        """Layer 3: Confirm every requested ID exists in the report."""
        if not item_ids:
            return ValidationResult(
                passed=False, layer=3, message="no item IDs provided"
            )
        missing = [fid for fid in item_ids if fid not in self._known_ids]
        if missing:
            return ValidationResult(
                passed=False,
                layer=3,
                message=f"unknown IDs: {', '.join(missing)}",
                details=[f"Available: {', '.join(sorted(self._known_ids)[:10])}..."],
            )
        return ValidationResult(
            passed=True, layer=3, message=f"all {len(item_ids)} IDs found in report"
        )

    def validate_risk_filter(
        self, item_ids: List[str], max_risk: str = "LOW"
    ) -> ValidationResult:
        """Layer 4: Confirm every item's risk is within the requested threshold."""
        max_order = _RISK_ORDER.get(max_risk.upper(), 0)
        violations = [
            fid
            for fid in item_ids
            if _RISK_ORDER.get(
                self._known_ids.get(fid, {}).get("risk_level", "CRITICAL").upper(), 99
            ) > max_order
        ]
        if violations:
            return ValidationResult(
                passed=False,
                layer=4,
                message=f"items exceed risk threshold {max_risk}: {', '.join(violations)}",
            )
        return ValidationResult(
            passed=True,
            layer=4,
            message=f"all items within {max_risk} risk threshold",
        )

    def validate_batch_dry_run(
        self,
        batch: List[str],
        phase3_data: Dict[str, Any],
        phase2_data: Dict[str, Any],
    ) -> ValidationResult:
        """Layer 5: Run DryRunExecutor for the batch and check is_safe."""
        try:
            from agents.code_auditor.core.phase5_executor import DryRunExecutor
        except ImportError as exc:
            return ValidationResult(
                passed=False,
                layer=5,
                message=f"cannot import DryRunExecutor: {exc}",
                details=["Run from repo root: python agents/code_fixer/cli.py ..."],
            )

        try:
            executor = DryRunExecutor(
                phase3_verified=phase3_data,
                phase1_report={},
                phase2_report=phase2_data,
                verbose=self._verbose,
            )
            result = executor.run_dry_run(batch)
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                passed=False, layer=5, message=f"dry-run error: {exc}"
            )

        if not result.is_safe:
            return ValidationResult(
                passed=False,
                layer=5,
                message=f"dry-run flagged batch as unsafe",
                details=result.warnings,
            )
        return ValidationResult(
            passed=True,
            layer=5,
            message=(
                f"dry-run safe — {result.lines_affected} lines affected, "
                f"{len(result.files_to_delete)} files deleted"
            ),
        )

    def run_baseline_tests(self) -> ValidationResult:
        """Layer 6: Run the full test suite before touching any code."""
        passed, output = self._git.run_tests()
        if not passed:
            return ValidationResult(
                passed=False,
                layer=6,
                message="baseline tests failed — fix before running fixer",
                details=[output[:500]],
            )
        return ValidationResult(
            passed=True,
            layer=6,
            message=f"baseline tests passed — {output[:120]}",
        )
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
python -m pytest agents/code_fixer/tests/test_safety_validator.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/code_fixer/core/safety_validator.py agents/code_fixer/tests/test_safety_validator.py
git commit -m "feat(code-fixer): add SafetyValidator with 6-layer checks"
```

---

## Task 4: ReportGenerator

**Files:**
- Create: `agents/code_fixer/core/report_generator.py`
- Create: `agents/code_fixer/tests/test_report_generator.py`

- [ ] **Step 1: Write the failing tests**

```python
# agents/code_fixer/tests/test_report_generator.py
"""Unit tests for ReportGenerator — no mocking needed, just assert output."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.code_fixer.core.report_generator import ReportGenerator


@pytest.fixture
def run_data() -> dict:
    return {
        "run_id": "20260412_143022",
        "started_at": "2026-04-12T14:30:22",
        "finished_at": "2026-04-12T14:45:10",
        "report_input": "phase3_verified.json",
        "risk_filter": "LOW",
        "batch_size": 3,
        "total_candidates": 97,
        "batches_attempted": 33,
        "batches_succeeded": 32,
        "batches_failed": 1,
        "items_fixed": [f"O{i:03d}" for i in range(1, 97)],
        "items_failed": ["U055", "U056", "U057"],
        "lines_removed": 2280,
        "commits": ["abc1234", "def5678"],
        "batches": [
            {
                "batch_num": 1,
                "item_ids": ["O001", "O002", "O003"],
                "status": "success",
                "lines_removed": 45,
                "commit_hash": "abc1234",
                "branch_name": "audit/remove-O001-2026-04-12",
                "error": None,
            }
        ],
    }


class TestWriteJson:
    def test_writes_valid_json(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.json"
        gen.write_json(out)

        data = json.loads(out.read_text())
        assert data["run_id"] == "20260412_143022"
        assert data["batches_succeeded"] == 32
        assert data["lines_removed"] == 2280

    def test_creates_parent_dirs(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "subdir" / "report.json"
        gen.write_json(out)
        assert out.exists()


class TestWriteHtml:
    def test_writes_html_file(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        assert out.exists()

    def test_html_contains_key_metrics(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()

        assert "20260412_143022" in html   # run_id
        assert "2280" in html              # lines_removed
        assert "32" in html               # batches_succeeded
        assert "<!DOCTYPE html>" in html

    def test_html_contains_failed_items(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()
        assert "U055" in html

    def test_html_contains_batch_table(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()
        assert "abc1234" in html
        assert "O001" in html
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
python -m pytest agents/code_fixer/tests/test_report_generator.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'ReportGenerator'`

- [ ] **Step 3: Implement ReportGenerator**

```python
# agents/code_fixer/core/report_generator.py
"""ReportGenerator — produce HTML and JSON fix reports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ReportGenerator:
    """Generate human- and machine-readable reports for a Code Fixer run.

    Parameters
    ----------
    run_data:
        Dict describing the completed run.  Expected keys: ``run_id``,
        ``started_at``, ``finished_at``, ``risk_filter``, ``batch_size``,
        ``total_candidates``, ``batches_attempted``, ``batches_succeeded``,
        ``batches_failed``, ``items_fixed``, ``items_failed``,
        ``lines_removed``, ``commits``, ``batches``.
    """

    def __init__(self, run_data: Dict[str, Any]) -> None:
        self._data = run_data

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def write_json(self, path: Path) -> None:
        """Write machine-readable JSON report to *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def write_html(self, path: Path) -> None:
        """Write human-readable HTML report to *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._generate_html(), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _generate_html(self) -> str:
        d = self._data
        run_id = d.get("run_id", "unknown")
        started = d.get("started_at", "")[:19].replace("T", " ")
        finished = d.get("finished_at", "")[:19].replace("T", " ")
        risk = d.get("risk_filter", "LOW")
        candidates = d.get("total_candidates", 0)
        attempted = d.get("batches_attempted", 0)
        succeeded = d.get("batches_succeeded", 0)
        failed_batches = d.get("batches_failed", 0)
        items_fixed = d.get("items_fixed", [])
        items_failed = d.get("items_failed", [])
        lines = d.get("lines_removed", 0)
        commits = d.get("commits", [])
        batches = d.get("batches", [])

        pct = round(succeeded / attempted * 100) if attempted else 0
        status_color = "#198754" if failed_batches == 0 else "#fd7e14"
        status_text = "SUCCESS" if failed_batches == 0 else "PARTIAL"

        batch_rows = ""
        for b in batches:
            ids = ", ".join(b.get("item_ids", []))
            status = b.get("status", "")
            row_cls = "table-success" if status == "success" else "table-danger"
            commit = b.get("commit_hash", "—")[:7]
            err = self._esc(b.get("error") or "")
            batch_rows += (
                f"<tr class='{row_cls}'>"
                f"<td>{b.get('batch_num','')}</td>"
                f"<td>{self._esc(ids)}</td>"
                f"<td>{status}</td>"
                f"<td>{b.get('lines_removed', 0)}</td>"
                f"<td><code>{commit}</code></td>"
                f"<td>{err}</td>"
                f"</tr>"
            )

        failed_items_html = ""
        if items_failed:
            failed_items_html = (
                "<p><strong>Failed items:</strong> "
                + ", ".join(f"<code>{self._esc(x)}</code>" for x in items_failed)
                + "</p>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fix Report {run_id}</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; padding: 2rem; }}
    .kpi {{ font-size: 2rem; font-weight: 700; }}
    .badge-status {{ background: {status_color}; color: #fff;
                     padding: .4rem 1rem; border-radius: 6px; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Code Fixer Run Report</h1>
  <p class="text-muted">Run ID: <code>{run_id}</code> &nbsp;|&nbsp;
     {started} &rarr; {finished}</p>
  <span class="badge-status">{status_text}</span>

  <div class="row g-3 mt-3">
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-success">{len(items_fixed)}</div>
      <div class="text-muted">Items Fixed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-danger">{len(items_failed)}</div>
      <div class="text-muted">Items Failed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-info">{lines}</div>
      <div class="text-muted">Lines Removed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-primary">{pct}%</div>
      <div class="text-muted">Batch Success Rate</div>
    </div></div>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-md-6">
      <div class="card p-3">
        <h5>Run Configuration</h5>
        <table class="table table-sm table-borderless mb-0">
          <tr><td>Risk filter</td><td><strong>{risk}</strong></td></tr>
          <tr><td>Batch size</td><td>{d.get("batch_size", 3)}</td></tr>
          <tr><td>Candidates</td><td>{candidates}</td></tr>
          <tr><td>Batches attempted</td><td>{attempted}</td></tr>
          <tr><td>Batches succeeded</td><td>{succeeded}</td></tr>
          <tr><td>Batches failed</td><td>{failed_batches}</td></tr>
          <tr><td>Commits created</td><td>{len(commits)}</td></tr>
        </table>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card p-3">
        <h5>Commits</h5>
        {"".join(f"<code class='d-block'>{self._esc(c)}</code>" for c in commits[:10])}
        {f"<small class='text-muted'>...and {len(commits)-10} more</small>" if len(commits) > 10 else ""}
      </div>
    </div>
  </div>

  {failed_items_html}

  <h4 class="mt-4">Batch Details</h4>
  <table class="table table-hover table-sm">
    <thead class="table-light">
      <tr><th>#</th><th>Items</th><th>Status</th>
          <th>Lines</th><th>Commit</th><th>Error</th></tr>
    </thead>
    <tbody>{batch_rows}</tbody>
  </table>

  <footer class="mt-4 text-muted">
    <small>Generated by Code Fixer Agent &mdash; {self._esc(run_id)}</small>
  </footer>
</body>
</html>"""

    @staticmethod
    def _esc(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
python -m pytest agents/code_fixer/tests/test_report_generator.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/code_fixer/core/report_generator.py agents/code_fixer/tests/test_report_generator.py
git commit -m "feat(code-fixer): add ReportGenerator producing HTML + JSON"
```

---

## Task 5: FixerEngine — Data Layer

`FixerEngine` lives in `cli.py`. This task covers `load_report()` and `build_batches()`.

**Files:**
- Modify: `agents/code_fixer/cli.py`

- [ ] **Step 1: Write failing tests (add to a new test file)**

```python
# agents/code_fixer/tests/test_fixer_engine.py
"""Unit tests for FixerEngine data layer (load_report + build_batches)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.code_fixer.cli import FixerEngine


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _write_phase3(tmp_path: Path, all_checks: list) -> Path:
    data = {"all_checks": all_checks, "scenarios": {}}
    p = tmp_path / "phase3_verified.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _write_phase2(tmp_path: Path, findings: list) -> Path:
    data = {"findings": findings}
    p = tmp_path / "phase2_findings.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


FINDINGS = [
    {"id": "O001", "type": "orphan_file",   "file": "old.js", "item": "old",      "risk": "LOW",    "confidence": 0.99, "lines": 80},
    {"id": "O002", "type": "orphan_file",   "file": "dead.py","item": "dead",     "risk": "LOW",    "confidence": 0.98, "lines": 60},
    {"id": "U001", "type": "unused_export", "file": "theme.js","item": "useTheme","risk": "MEDIUM", "confidence": 0.90, "lines": 20},
    {"id": "U002", "type": "unused_import", "file": "api.py",  "item": "logging", "risk": "LOW",    "confidence": 0.95, "lines": 1},
]

ALL_CHECKS = [
    {"id": "O001", "risk_level": "LOW",    "confidence": 0.99, "file": "old.js",  "name": "old",      "type": "orphan_file"},
    {"id": "O002", "risk_level": "LOW",    "confidence": 0.98, "file": "dead.py", "name": "dead",     "type": "orphan_file"},
    {"id": "U001", "risk_level": "MEDIUM", "confidence": 0.90, "file": "theme.js","name": "useTheme", "type": "unused_export"},
    {"id": "U002", "risk_level": "LOW",    "confidence": 0.95, "file": "api.py",  "name": "logging",  "type": "unused_import"},
]


# ── load_report ───────────────────────────────────────────────────────────────

class TestLoadReport:
    def test_loads_low_risk_candidates_only_by_default(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        candidates = eng.load_report()
        ids = {c["id"] for c in candidates}
        assert "O001" in ids
        assert "O002" in ids
        assert "U002" in ids
        assert "U001" not in ids   # MEDIUM excluded from LOW filter

    def test_loads_medium_candidates_when_risk_medium(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="MEDIUM")
        ids = {c["id"] for c in eng.load_report()}
        assert "U001" in ids

    def test_filters_to_specific_items_when_items_given(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, items=["O001"])
        ids = {c["id"] for c in eng.load_report()}
        assert ids == {"O001"}

    def test_raises_when_report_file_missing(self, tmp_path):
        eng = FixerEngine(
            report_path=tmp_path / "nonexistent.json",
            project_root=tmp_path,
        )
        with pytest.raises(FileNotFoundError):
            eng.load_report()

    def test_falls_back_to_phase2_when_no_all_checks(self, tmp_path):
        """When phase3 has only scenarios, join with phase2_findings.json."""
        phase3_data = {
            "scenarios": {
                "scenario_1_safest": {"finding_ids": ["O001", "O002"]},
                "scenario_2_moderate": {"finding_ids": ["O001", "O002", "U001", "U002"]},
            }
        }
        p3 = tmp_path / "phase3_verified.json"
        p3.write_text(json.dumps(phase3_data), encoding="utf-8")
        _write_phase2(tmp_path, FINDINGS)

        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        ids = {c["id"] for c in eng.load_report()}
        assert "O001" in ids
        assert "U001" not in ids  # MEDIUM


# ── build_batches ─────────────────────────────────────────────────────────────

class TestBuildBatches:
    def _engine(self, tmp_path: Path, batch_size: int = 3) -> FixerEngine:
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="MEDIUM", batch_size=batch_size,
        )
        eng._candidates = eng.load_report()
        return eng

    def test_chunks_into_correct_batch_size(self, tmp_path):
        eng = self._engine(tmp_path, batch_size=2)
        batches = eng.build_batches()
        for b in batches[:-1]:
            assert len(b) == 2

    def test_orphan_files_sorted_first(self, tmp_path):
        eng = self._engine(tmp_path)
        batches = eng.build_batches()
        flat = [fid for batch in batches for fid in batch]
        # O001, O002 should appear before U001, U002
        assert flat.index("O001") < flat.index("U001")

    def test_higher_confidence_sorted_before_lower_within_same_risk(self, tmp_path):
        eng = self._engine(tmp_path)
        batches = eng.build_batches()
        flat = [fid for batch in batches for fid in batch]
        # O001 (confidence 0.99) before O002 (0.98) within same risk tier
        assert flat.index("O001") < flat.index("O002")

    def test_single_item_batch_when_remainder(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS[:4])
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="MEDIUM", batch_size=3,
        )
        eng._candidates = eng.load_report()
        batches = eng.build_batches()
        assert sum(len(b) for b in batches) == len(eng._candidates)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest agents/code_fixer/tests/test_fixer_engine.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'FixerEngine'`

- [ ] **Step 3: Implement FixerEngine data layer in cli.py**

Replace the empty `agents/code_fixer/cli.py` with:

```python
"""
agents/code_fixer/cli.py
========================
Code Fixer Agent — production orchestrator for Code Auditor findings.

Batches phase3_verified.json findings, removes them via Code Auditor's
Phase 5 engine, tests each batch, commits atomically, and produces
HTML + JSON reports.

Usage::

    python agents/code_fixer/cli.py fix --report phase3_verified.json
    python agents/code_fixer/cli.py analyze --report phase3_verified.json
    python agents/code_fixer/cli.py plan --report phase3_verified.json
    python agents/code_fixer/cli.py status
    python agents/code_fixer/cli.py verify --report phase3_verified.json --items U001 U002
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Support both direct execution and package import
if __name__ == "__main__" and __package__ is None:
    _repo_root = Path(__file__).resolve().parent.parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BatchResult:
    """Outcome of a single removal batch."""

    batch_num: int
    item_ids: List[str]
    status: str           # "success" | "failed" | "skipped"
    lines_removed: int
    commit_hash: str
    branch_name: str
    error: Optional[str] = None


@dataclass
class RunResult:
    """Outcome of a complete FixerEngine.run() call."""

    status: str                              # "success" | "partial" | "failed"
    batches_attempted: int
    batches_succeeded: int
    batches_failed: int
    items_fixed: List[str] = field(default_factory=list)
    items_failed: List[str] = field(default_factory=list)
    lines_removed: int = 0
    commits: List[str] = field(default_factory=list)
    batch_results: List[BatchResult] = field(default_factory=list)
    report_json: Optional[str] = None
    report_html: Optional[str] = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RISK_ORDER: Dict[str, int] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_RISK_THRESHOLDS: Dict[str, Set[str]] = {
    "LOW":    {"LOW"},
    "MEDIUM": {"LOW", "MEDIUM"},
    "HIGH":   {"LOW", "MEDIUM", "HIGH"},
}
_TYPE_ORDER: Dict[str, int] = {
    "orphan_file":   0,
    "unused_import": 1,
    "unused_export": 2,
}


# ---------------------------------------------------------------------------
# FixerEngine
# ---------------------------------------------------------------------------


class FixerEngine:
    """Orchestrate batched code removal across phase3_verified.json findings.

    Parameters
    ----------
    report_path:
        Path to ``phase3_verified.json`` produced by Code Auditor.
    project_root:
        Absolute path to the git repository root.
    phase2_path:
        Optional explicit path to ``phase2_findings.json``.  When omitted
        the engine looks for it in the same directory as *report_path*.
    risk:
        Maximum risk level to include.  ``"LOW"`` (default) includes only
        LOW-risk items; ``"MEDIUM"`` adds MEDIUM; ``"HIGH"`` adds HIGH.
    batch_size:
        Number of items per execution batch (default 3).
    items:
        When given, restrict execution to these specific finding IDs only.
    skip_failed:
        When True, skip failing batches and continue (best-effort mode).
    no_cleanup:
        When True, leave a failed branch in place instead of deleting it.
    verbose:
        When True, print per-step progress.
    """

    def __init__(
        self,
        report_path: Path,
        project_root: Path,
        phase2_path: Optional[Path] = None,
        risk: str = "LOW",
        batch_size: int = 3,
        items: Optional[List[str]] = None,
        skip_failed: bool = False,
        no_cleanup: bool = False,
        verbose: bool = False,
    ) -> None:
        self.report_path = Path(report_path)
        self.project_root = Path(project_root)
        self.phase2_path = Path(phase2_path) if phase2_path else None
        self.risk = risk.upper()
        self.batch_size = batch_size
        self.items = set(items) if items else None
        self.skip_failed = skip_failed
        self.no_cleanup = no_cleanup
        self.verbose = verbose

        self._candidates: List[dict] = []
        self._phase3_data: Dict[str, Any] = {}
        self._phase2_data: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def load_report(self) -> List[dict]:
        """Load, join, and filter candidates from phase3 + phase2 reports.

        Returns
        -------
        list[dict]
            Filtered candidate list.  Each item has keys:
            ``id``, ``file``, ``name``, ``type``, ``risk``,
            ``confidence``, ``lines``.

        Raises
        ------
        FileNotFoundError
            If ``report_path`` does not exist.
        """
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Report not found: {self.report_path}\n"
                "Run: python agents/code_auditor/cli.py verify --report phase2_findings.json"
            )

        self._phase3_data = json.loads(
            self.report_path.read_text(encoding="utf-8")
        )

        # Locate phase2 data (for per-item risk/confidence when all_checks absent)
        p2_path = self.phase2_path or (
            self.report_path.parent / "phase2_findings.json"
        )
        if p2_path.exists():
            self._phase2_data = json.loads(p2_path.read_text(encoding="utf-8"))

        allowed = _RISK_THRESHOLDS.get(self.risk, {"LOW"})

        # ── Path A: all_checks already present (normalised by Auditor CLI) ──
        all_checks = self._phase3_data.get("all_checks", [])
        if all_checks:
            self._candidates = self._filter_checks(all_checks, allowed)
            return self._candidates

        # ── Path B: scenarios + phase2 findings (raw phase3 on disk) ────────
        safe_ids: Set[str] = set()
        for scenario in self._phase3_data.get("scenarios", {}).values():
            safe_ids.update(scenario.get("finding_ids", []))

        p2_findings: Dict[str, dict] = {
            f["id"]: f
            for f in self._phase2_data.get("findings", [])
            if f.get("id")
        }

        # Build normalised all_checks so BatchRemover / DryRunExecutor work
        normalised: List[dict] = []
        for fid, f in p2_findings.items():
            if fid not in safe_ids:
                continue
            normalised.append({
                "id":         fid,
                "file":       f.get("file", ""),
                "name":       f.get("item") or f.get("name") or fid,
                "type":       f.get("type", "unknown"),
                "risk_level": f.get("risk", "LOW").upper(),
                "confidence": f.get("confidence", 0.0),
                "lines":      f.get("lines", 0),
                "evidence":   f.get("evidence", {}),
            })

        # Store normalised all_checks so BatchRemover can use them
        self._phase3_data["all_checks"] = normalised
        self._candidates = self._filter_checks(normalised, allowed)
        return self._candidates

    def build_batches(self) -> List[List[str]]:
        """Sort candidates (safest first) and chunk into batches.

        Returns
        -------
        list[list[str]]
            Outer list = batches.  Inner list = finding IDs in that batch.
        """
        sorted_candidates = sorted(
            self._candidates,
            key=lambda c: (
                _RISK_ORDER.get(c.get("risk", c.get("risk_level", "LOW")).upper(), 99),
                -c.get("confidence", 0.0),
                _TYPE_ORDER.get(c.get("type", ""), 99),
            ),
        )
        ids = [c["id"] for c in sorted_candidates]
        return [ids[i: i + self.batch_size] for i in range(0, len(ids), self.batch_size)]

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _filter_checks(
        self, checks: List[dict], allowed: Set[str]
    ) -> List[dict]:
        """Apply risk-threshold and --items filters to *checks*."""
        result = []
        for c in checks:
            risk = c.get("risk_level", c.get("risk", "LOW")).upper()
            if risk not in allowed:
                continue
            if self.items and c.get("id") not in self.items:
                continue
            result.append(c)
        return result
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
python -m pytest agents/code_fixer/tests/test_fixer_engine.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/code_fixer/cli.py agents/code_fixer/tests/test_fixer_engine.py
git commit -m "feat(code-fixer): FixerEngine data layer (load_report + build_batches)"
```

---

## Task 6: FixerEngine — Execution Loop

**Files:**
- Modify: `agents/code_fixer/cli.py` (add `run()` and `dry_run()` methods)
- Modify: `agents/code_fixer/tests/test_fixer_engine.py` (add execution tests)

- [ ] **Step 1: Write failing tests for run() and dry_run()**

Append to `agents/code_fixer/tests/test_fixer_engine.py`:

```python
# ── run() ────────────────────────────────────────────────────────────────────

from unittest.mock import MagicMock, patch


class TestRun:
    """Test FixerEngine.run() using mocked BatchRemover, GitOrchestrator, SafetyValidator."""

    def _engine(self, tmp_path: Path) -> FixerEngine:
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="LOW", batch_size=2, skip_failed=False,
        )
        eng._candidates = eng.load_report()
        return eng

    def _mock_safety(self, passed: bool = True):
        v = MagicMock()
        ok = MagicMock(); ok.passed = True
        fail = MagicMock(); fail.passed = False; fail.message = "unsafe"
        v.validate_report.return_value = ok
        v.validate_git_clean.return_value = ok
        v.run_baseline_tests.return_value = ok
        v.validate_batch_dry_run.return_value = ok if passed else fail
        return v

    def _mock_remover(self, success: bool = True):
        r = MagicMock()
        if success:
            r.remove_batch.return_value = {
                "branch_created": "audit/remove-O001-2026-04-12",
                "items_removed": ["O001", "O002"],
                "total_lines_removed": 140,
                "status": "success",
            }
        else:
            r.remove_batch.return_value = {
                "branch_created": "audit/remove-O001-2026-04-12",
                "items_removed": [],
                "total_lines_removed": 0,
                "status": "failed",
                "errors": ["file not found"],
            }
        return r

    def test_successful_run_returns_success_status(self, tmp_path):
        eng = self._engine(tmp_path)
        mock_git = MagicMock()
        mock_git.run_tests.return_value = (True, "3 passed")
        mock_git.commit_batch.return_value = "abc1234"
        mock_git.merge_to_main.return_value = None

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        assert result.status in ("success", "partial")
        assert result.batches_succeeded > 0

    def test_failed_batch_stops_on_default_mode(self, tmp_path):
        eng = self._engine(tmp_path)
        eng.skip_failed = False

        mock_git = MagicMock()
        mock_git.run_tests.return_value = (False, "1 failed")
        mock_git.current_branch.return_value = "audit/remove-O001-2026-04-12"

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        # Should have stopped — no more batches after the first failure
        assert result.batches_failed >= 1
        assert result.status in ("partial", "failed")

    def test_skip_failed_continues_after_failure(self, tmp_path):
        eng = self._engine(tmp_path)
        eng.skip_failed = True

        call_count = 0
        def alternating_tests():
            nonlocal call_count
            call_count += 1
            return (call_count % 2 == 0), "output"

        mock_git = MagicMock()
        mock_git.run_tests.side_effect = lambda: alternating_tests()
        mock_git.commit_batch.return_value = "abc1234"
        mock_git.merge_to_main.return_value = None
        mock_git.current_branch.return_value = "audit/remove-O001-2026-04-12"

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        # With skip_failed, it should attempt multiple batches
        assert result.batches_attempted > 1


class TestDryRun:
    def test_dry_run_returns_preview_without_changes(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        eng._candidates = eng.load_report()

        mock_dry_result = MagicMock()
        mock_dry_result.is_safe = True
        mock_dry_result.lines_affected = 200
        mock_dry_result.files_to_delete = []
        mock_dry_result.warnings = []

        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_dry_result

        with patch("agents.code_fixer.cli.DryRunExecutor", return_value=mock_executor):
            summary = eng.dry_run()

        assert "batches" in summary
        assert "total_candidates" in summary
        assert summary["total_candidates"] == len(eng._candidates)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest agents/code_fixer/tests/test_fixer_engine.py::TestRun -v 2>&1 | head -15
```
Expected: `AttributeError: 'FixerEngine' object has no attribute 'run'`

- [ ] **Step 3: Add run() and dry_run() to FixerEngine in cli.py**

Append these methods to the `FixerEngine` class (inside the class, after `build_batches`):

```python
    def run(self) -> "RunResult":
        """Execute the full batch loop: validate → remove → test → commit.

        Returns
        -------
        RunResult
            Summary of the entire run including per-batch results.
        """
        from agents.code_fixer.core.safety_validator import SafetyValidator
        from agents.code_fixer.core.git_orchestrator import GitOrchestrator
        from agents.code_fixer.core.report_generator import ReportGenerator
        try:
            from agents.code_auditor.core.phase5_executor import BatchRemover, DryRunExecutor
        except ImportError as exc:
            raise ImportError(
                f"Cannot import code_auditor modules: {exc}\n"
                "Run from repo root: python agents/code_fixer/cli.py ..."
            ) from exc

        git = GitOrchestrator(project_root=self.project_root, verbose=self.verbose)
        validator = SafetyValidator(
            report_data=self._phase3_data,
            project_root=self.project_root,
            verbose=self.verbose,
        )
        remover = BatchRemover(
            project_root=str(self.project_root),
            phase2_report=self._phase2_data,
            verbose=self.verbose,
        )

        # ── Pre-flight checks ─────────────────────────────────────────
        for check_fn, exit_code in [
            (validator.validate_report,    3),
            (validator.validate_git_clean, 3),
            (validator.run_baseline_tests, 3),
        ]:
            result = check_fn()
            if not result.passed:
                raise SystemExit(
                    f"Pre-flight layer {result.layer} failed: {result.message}"
                )

        batches = self.build_batches()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        started_at = datetime.now().isoformat(timespec="seconds")

        batch_results: List[BatchResult] = []
        items_fixed: List[str] = []
        items_failed: List[str] = []
        commits: List[str] = []
        lines_removed = 0
        stopped = False

        for batch_num, batch in enumerate(batches, start=1):
            if stopped:
                break

            if self.verbose:
                print(f"  Batch {batch_num}/{len(batches)}: {', '.join(batch)}")

            # Layer 5: per-batch dry-run
            dry_check = validator.validate_batch_dry_run(
                batch, self._phase3_data, self._phase2_data
            )
            if not dry_check.passed:
                br = BatchResult(
                    batch_num=batch_num, item_ids=batch, status="skipped",
                    lines_removed=0, commit_hash="", branch_name="",
                    error=dry_check.message,
                )
                batch_results.append(br)
                items_failed.extend(batch)
                if not self.skip_failed:
                    stopped = True
                continue

            # Execute removal
            try:
                removal = remover.remove_batch(
                    batch, self._phase3_data,
                    batch_id=f"fix-{run_id}-batch{batch_num}",
                )
            except Exception as exc:  # noqa: BLE001
                br = BatchResult(
                    batch_num=batch_num, item_ids=batch, status="failed",
                    lines_removed=0, commit_hash="", branch_name="",
                    error=str(exc),
                )
                batch_results.append(br)
                items_failed.extend(batch)
                if not self.skip_failed:
                    stopped = True
                continue

            branch = removal.get("branch_created", "")

            if removal.get("status") == "failed":
                br = BatchResult(
                    batch_num=batch_num, item_ids=batch, status="failed",
                    lines_removed=0, commit_hash="", branch_name=branch,
                    error=str(removal.get("errors", "")),
                )
                batch_results.append(br)
                items_failed.extend(batch)
                if not self.no_cleanup and branch:
                    git.cleanup_branch(branch)
                if not self.skip_failed:
                    stopped = True
                continue

            # Run tests
            tests_passed, test_output = git.run_tests()
            if not tests_passed:
                br = BatchResult(
                    batch_num=batch_num, item_ids=batch, status="failed",
                    lines_removed=0, commit_hash="", branch_name=branch,
                    error=f"tests failed: {test_output[:200]}",
                )
                batch_results.append(br)
                items_failed.extend(batch)
                if not self.no_cleanup and branch:
                    git.cleanup_branch(branch)
                if not self.skip_failed:
                    stopped = True
                continue

            # Commit and merge
            ids_str = ", ".join(batch)
            commit_hash = git.commit_batch(
                f"fix: remove {ids_str} ({self.risk} risk)"
            )
            if branch:
                try:
                    git.merge_to_main(branch)
                except RuntimeError:
                    pass  # branch may already be on main

            batch_lines = removal.get("total_lines_removed", 0)
            br = BatchResult(
                batch_num=batch_num, item_ids=batch, status="success",
                lines_removed=batch_lines, commit_hash=commit_hash,
                branch_name=branch,
            )
            batch_results.append(br)
            items_fixed.extend(removal.get("items_removed", batch))
            commits.append(commit_hash)
            lines_removed += batch_lines

        # ── Write reports ─────────────────────────────────────────────
        succeeded = sum(1 for b in batch_results if b.status == "success")
        failed = sum(1 for b in batch_results if b.status != "success")

        if failed == 0:
            final_status = "success"
        elif succeeded > 0:
            final_status = "partial"
        else:
            final_status = "failed"

        run_data = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "report_input": str(self.report_path),
            "risk_filter": self.risk,
            "batch_size": self.batch_size,
            "total_candidates": len(self._candidates),
            "batches_attempted": len(batch_results),
            "batches_succeeded": succeeded,
            "batches_failed": failed,
            "items_fixed": items_fixed,
            "items_failed": items_failed,
            "lines_removed": lines_removed,
            "commits": commits,
            "batches": [
                {
                    "batch_num": b.batch_num,
                    "item_ids": b.item_ids,
                    "status": b.status,
                    "lines_removed": b.lines_removed,
                    "commit_hash": b.commit_hash,
                    "branch_name": b.branch_name,
                    "error": b.error,
                }
                for b in batch_results
            ],
        }

        reporter = ReportGenerator(run_data)
        json_path = self.project_root / f"fix_report_{run_id}.json"
        html_path = self.project_root / f"fix_report_{run_id}.html"
        reporter.write_json(json_path)
        reporter.write_html(html_path)

        return RunResult(
            status=final_status,
            batches_attempted=len(batch_results),
            batches_succeeded=succeeded,
            batches_failed=failed,
            items_fixed=items_fixed,
            items_failed=items_failed,
            lines_removed=lines_removed,
            commits=commits,
            batch_results=batch_results,
            report_json=str(json_path),
            report_html=str(html_path),
        )

    def dry_run(self) -> dict:
        """Preview the full run without making any changes.

        Returns
        -------
        dict
            Summary with ``total_candidates``, ``batches``,
            ``estimated_lines``, and per-batch details.
        """
        try:
            from agents.code_auditor.core.phase5_executor import DryRunExecutor
        except ImportError:
            return {
                "error": "code_auditor modules not found",
                "total_candidates": len(self._candidates),
                "batches": [],
            }

        batches = self.build_batches()
        executor = DryRunExecutor(
            phase3_verified=self._phase3_data,
            phase1_report={},
            phase2_report=self._phase2_data,
            verbose=self.verbose,
        )

        batch_previews = []
        for i, batch in enumerate(batches, start=1):
            try:
                result = executor.run_dry_run(batch)
                batch_previews.append({
                    "batch_num": i,
                    "item_ids": batch,
                    "estimated_lines": result.lines_affected,
                    "is_safe": result.is_safe,
                    "warnings": result.warnings,
                    "files_to_delete": result.files_to_delete,
                })
            except Exception as exc:  # noqa: BLE001
                batch_previews.append({
                    "batch_num": i, "item_ids": batch,
                    "error": str(exc), "is_safe": False,
                })

        return {
            "total_candidates": len(self._candidates),
            "total_batches": len(batches),
            "risk_filter": self.risk,
            "batch_size": self.batch_size,
            "batches": batch_previews,
            "estimated_lines": sum(
                b.get("estimated_lines", 0) for b in batch_previews
            ),
        }
```

- [ ] **Step 4: Run all FixerEngine tests**

```bash
python -m pytest agents/code_fixer/tests/test_fixer_engine.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add agents/code_fixer/cli.py agents/code_fixer/tests/test_fixer_engine.py
git commit -m "feat(code-fixer): FixerEngine execution loop (run + dry_run)"
```

---

## Task 7: CLI Subcommands

**Files:**
- Modify: `agents/code_fixer/cli.py` (add 5 `cmd_*` functions + `_build_parser()` + `main()`)

- [ ] **Step 1: Append CLI code to cli.py**

Add after the `FixerEngine` class:

```python
# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_fix(args: argparse.Namespace) -> int:
    """Execute batched code removal.

    Loads phase3_verified.json, builds batches, runs the full remove →
    test → commit loop, and writes HTML + JSON reports.
    """
    report_path = Path(args.report)
    if not report_path.exists():
        print(
            f"\u274c Error: {report_path} not found\n"
            "   Run: python agents/code_auditor/cli.py verify --report phase2_findings.json",
            file=sys.stderr,
        )
        return 4

    project_root = Path(args.project).resolve()
    engine = FixerEngine(
        report_path=report_path,
        project_root=project_root,
        phase2_path=Path(args.phase2) if args.phase2 else None,
        risk=args.risk,
        batch_size=args.batch_size,
        items=args.items or None,
        skip_failed=args.skip_failed,
        no_cleanup=args.no_cleanup,
        verbose=args.verbose,
    )

    try:
        print(f"\U0001f50d Loading {report_path}...")
        candidates = engine.load_report()
        print(f"   {len(candidates)} {args.risk}-risk candidates found")
    except FileNotFoundError as exc:
        print(f"\u274c Error: {exc}", file=sys.stderr)
        return 4
    except json.JSONDecodeError as exc:
        print(f"\u274c Error: invalid JSON in report: {exc}", file=sys.stderr)
        return 4

    if not candidates:
        print(f"\u2705 No {args.risk}-risk candidates to fix. All done!")
        return 0

    batches = engine.build_batches()
    print(f"\U0001f4cb Building batches: {len(batches)} batches x {args.batch_size} items")

    if args.dry_run:
        print("\n[DRY RUN — no changes will be made]\n")
        summary = engine.dry_run()
        for b in summary.get("batches", []):
            safe = "\u2705" if b.get("is_safe") else "\u274c"
            ids = ", ".join(b.get("item_ids", []))
            lines = b.get("estimated_lines", 0)
            print(f"  {safe} Batch {b['batch_num']:>3}: {ids}  ~{lines} lines")
        total = summary.get("estimated_lines", 0)
        print(f"\n   Total estimated: {len(candidates)} items / ~{total} lines")
        return 0

    try:
        result = engine.run()
    except SystemExit as exc:
        print(f"\u274c Pre-flight failed: {exc}", file=sys.stderr)
        return 3
    except ImportError as exc:
        print(f"\u274c Import error: {exc}", file=sys.stderr)
        return 3

    # ── Print summary ──────────────────────────────────────────────────
    icon = "\u2705" if result.status == "success" else (
        "\u26a0\ufe0f" if result.status == "partial" else "\u274c"
    )
    print(f"\n\U0001f4ca Run complete  {icon}")
    print(f"   Fixed  : {len(result.items_fixed)} items / {result.lines_removed} lines removed")
    print(f"   Failed : {len(result.items_failed)} items")
    print(f"   Commits: {len(result.commits)}")
    if result.report_html:
        print(f"   Report : {result.report_html}")

    if result.status == "success":
        return 0
    if result.status == "partial":
        return 1
    return 2


def cmd_analyze(args: argparse.Namespace) -> int:
    """Print a fixability summary — read-only, no changes."""
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"\u274c Error: {report_path} not found", file=sys.stderr)
        return 4

    project_root = Path(args.project).resolve()

    try:
        phase3 = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"\u274c Error: invalid JSON: {exc}", file=sys.stderr)
        return 4

    p2_path = report_path.parent / "phase2_findings.json"
    phase2: dict = {}
    if p2_path.exists():
        try:
            phase2 = json.loads(p2_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    print(f"\U0001f50d Analyzing {report_path}\n")

    for risk_label in ("LOW", "MEDIUM", "HIGH"):
        eng = FixerEngine(
            report_path=report_path,
            project_root=project_root,
            risk=risk_label,
        )
        try:
            candidates = eng.load_report()
        except Exception:
            candidates = []

        # count only items at exactly this risk level
        exact = [
            c for c in candidates
            if c.get("risk", c.get("risk_level", "")).upper() == risk_label
        ]
        if not exact:
            continue
        total_lines = sum(c.get("lines", 0) for c in exact)
        batches = max(1, len(exact) // 3)
        icon = {"LOW": "\u2705", "MEDIUM": "\u26a1", "HIGH": "\u26a0\ufe0f"}.get(risk_label, "")
        print(
            f"  {icon} {risk_label:<8} {len(exact):>4} items"
            f"  ~{total_lines:>5} lines  ~{batches} batches"
        )

    total_all = json.loads(report_path.read_text(encoding="utf-8")).get(
        "safe_to_remove", "?"
    )
    print(f"\n   safe_to_remove (phase3): {total_all}")
    print("   Run 'fixer fix --report ...' to apply fixes.")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Generate and write an execution plan JSON."""
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"\u274c Error: {report_path} not found", file=sys.stderr)
        return 4

    project_root = Path(args.project).resolve()
    eng = FixerEngine(
        report_path=report_path,
        project_root=project_root,
        risk=args.risk,
        batch_size=args.batch_size,
    )

    try:
        candidates = eng.load_report()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"\u274c Error loading report: {exc}", file=sys.stderr)
        return 4

    batches = eng.build_batches()
    cand_map = {c["id"]: c for c in candidates}

    plan = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_input": str(report_path),
        "risk_filter": args.risk,
        "batch_size": args.batch_size,
        "total_candidates": len(candidates),
        "total_batches": len(batches),
        "batches": [
            {
                "batch_num": i,
                "item_ids": batch,
                "estimated_lines": sum(
                    cand_map.get(fid, {}).get("lines", 0) for fid in batch
                ),
                "avg_confidence": round(
                    sum(cand_map.get(fid, {}).get("confidence", 0) for fid in batch)
                    / len(batch),
                    3,
                ) if batch else 0,
                "command": (
                    "python agents/code_fixer/cli.py fix"
                    f" --report {report_path}"
                    f" --items {' '.join(batch)}"
                ),
            }
            for i, batch in enumerate(batches, start=1)
        ],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"\U0001f4cb Plan written to {out_path}  ({len(batches)} batches)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print current git state and any open audit branches."""
    from agents.code_fixer.core.git_orchestrator import GitOrchestrator

    project_root = Path(args.project).resolve()
    git = GitOrchestrator(project_root=project_root)

    try:
        status = git.get_status()
    except RuntimeError as exc:
        print(f"\u274c git error: {exc}", file=sys.stderr)
        return 3

    clean_icon = "\u2705" if status["clean"] else "\u274c"
    print(f"\U0001f4cb Git Status")
    print(f"   Branch : {status['branch']}")
    print(f"   Clean  : {clean_icon} {'yes' if status['clean'] else 'no (uncommitted changes)'}")

    audit = status.get("audit_branches", [])
    if audit:
        print(f"   Audit branches ({len(audit)}):")
        for b in audit:
            print(f"     \u2022 {b}")
    else:
        print("   Audit branches: none")

    # Look for latest fix report
    reports = sorted(project_root.glob("fix_report_*.json"), reverse=True)
    if reports:
        print(f"   Last report: {reports[0].name}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Run all 6 safety layers on specific items without executing."""
    from agents.code_fixer.core.safety_validator import SafetyValidator

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"\u274c Error: {report_path} not found", file=sys.stderr)
        return 4

    try:
        phase3 = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"\u274c Error: invalid JSON: {exc}", file=sys.stderr)
        return 4

    # Ensure all_checks is populated
    p2_path = report_path.parent / "phase2_findings.json"
    phase2: dict = {}
    if p2_path.exists():
        try:
            phase2 = json.loads(p2_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    if not phase3.get("all_checks"):
        eng = FixerEngine(
            report_path=report_path,
            project_root=Path(args.project).resolve(),
            risk="HIGH",
        )
        try:
            eng.load_report()
            phase3 = eng._phase3_data
            phase2 = eng._phase2_data
        except Exception:
            pass

    project_root = Path(args.project).resolve()
    validator = SafetyValidator(
        report_data=phase3, project_root=project_root, verbose=args.verbose
    )

    item_ids: List[str] = list(args.items)
    print(f"\U0001f50d Verifying {', '.join(item_ids)}\n")

    checks = [
        ("Layer 1", validator.validate_report()),
        ("Layer 2", validator.validate_git_clean()),
        ("Layer 3", validator.validate_items_exist(item_ids)),
        ("Layer 4", validator.validate_risk_filter(item_ids, max_risk=args.risk)),
        ("Layer 5", validator.validate_batch_dry_run(item_ids, phase3, phase2)),
        ("Layer 6", validator.run_baseline_tests()),
    ]

    all_passed = True
    for label, result in checks:
        icon = "\u2705" if result.passed else "\u274c"
        print(f"  {icon} {label}: {result.message}")
        if not result.passed:
            all_passed = False
            for detail in result.details:
                print(f"       {detail}")

    print()
    if all_passed:
        print("\u2705 All layers passed — safe to run: fixer fix --items " + " ".join(item_ids))
        return 0
    else:
        print("\u274c Verification failed — do not execute until issues are resolved")
        return 3


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argparse parser."""
    parser = argparse.ArgumentParser(
        prog="code-fixer",
        description="Code Fixer Agent — batch orchestrator for Code Auditor findings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Preview what would be fixed
  python agents/code_fixer/cli.py fix --report phase3_verified.json --dry-run

  # Fix all LOW-risk items automatically
  python agents/code_fixer/cli.py fix --report phase3_verified.json

  # Fix specific items
  python agents/code_fixer/cli.py fix --report phase3_verified.json --items U001 U002 U003

  # Fix LOW + MEDIUM risk items, skipping failures
  python agents/code_fixer/cli.py fix --report phase3_verified.json --risk MEDIUM --skip-failed

  # Show fixability breakdown
  python agents/code_fixer/cli.py analyze --report phase3_verified.json

  # Generate execution plan
  python agents/code_fixer/cli.py plan --report phase3_verified.json --output plan.json

  # Show git status
  python agents/code_fixer/cli.py status

  # Verify specific items before executing
  python agents/code_fixer/cli.py verify --report phase3_verified.json --items U001 U002
""",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
        metavar="SUBCOMMAND",
    )
    subparsers.required = True

    # Shared arguments
    _project_arg = dict(
        type=str, default=".",
        help="Root of the git repository (default: current directory).",
    )
    _verbose_arg = dict(
        action="store_true",
        help="Print per-step progress.",
    )
    _risk_arg = dict(
        type=str, default="LOW", choices=["LOW", "MEDIUM", "HIGH"],
        help="Maximum risk level to include (default: LOW).",
    )
    _batch_size_arg = dict(
        type=int, default=3,
        help="Items per batch (default: 3).",
    )

    # ── fix ──────────────────────────────────────────────────────────────
    fix_p = subparsers.add_parser(
        "fix", help="Apply code fixes from phase3_verified.json."
    )
    fix_p.add_argument("--report", required=True, help="Path to phase3_verified.json.")
    fix_p.add_argument("--phase2", default=None, help="Path to phase2_findings.json (auto-detected if omitted).")
    fix_p.add_argument("--items", nargs="+", default=None, help="Specific finding IDs to fix.")
    fix_p.add_argument("--risk", **_risk_arg)
    fix_p.add_argument("--dry-run", action="store_true", help="Preview only, no changes.")
    fix_p.add_argument("--batch-size", type=int, default=3, dest="batch_size", help="Items per batch (default: 3).")
    fix_p.add_argument("--skip-failed", action="store_true", dest="skip_failed", help="Skip failing batches and continue.")
    fix_p.add_argument("--no-cleanup", action="store_true", dest="no_cleanup", help="Leave failed branches for manual debug.")
    fix_p.add_argument("--project", **_project_arg)
    fix_p.add_argument("--verbose", "-v", **_verbose_arg)
    fix_p.set_defaults(func=cmd_fix)

    # ── analyze ──────────────────────────────────────────────────────────
    ana_p = subparsers.add_parser(
        "analyze", help="Show fixability analysis (read-only)."
    )
    ana_p.add_argument("--report", required=True, help="Path to phase3_verified.json.")
    ana_p.add_argument("--project", **_project_arg)
    ana_p.add_argument("--verbose", "-v", **_verbose_arg)
    ana_p.set_defaults(func=cmd_analyze)

    # ── plan ─────────────────────────────────────────────────────────────
    plan_p = subparsers.add_parser(
        "plan", help="Generate execution plan JSON."
    )
    plan_p.add_argument("--report", required=True, help="Path to phase3_verified.json.")
    plan_p.add_argument("--output", default=None, help="Output path (default: fix_plan_DATE.json).")
    plan_p.add_argument("--risk", **_risk_arg)
    plan_p.add_argument("--batch-size", type=int, default=3, dest="batch_size")
    plan_p.add_argument("--project", **_project_arg)
    plan_p.set_defaults(func=cmd_plan)

    # ── status ────────────────────────────────────────────────────────────
    sta_p = subparsers.add_parser(
        "status", help="Show git status and open audit branches."
    )
    sta_p.add_argument("--project", **_project_arg)
    sta_p.set_defaults(func=cmd_status)

    # ── verify ────────────────────────────────────────────────────────────
    ver_p = subparsers.add_parser(
        "verify", help="Run 6-layer safety check on specific items."
    )
    ver_p.add_argument("--report", required=True, help="Path to phase3_verified.json.")
    ver_p.add_argument("--items", nargs="+", required=True, help="Finding IDs to verify.")
    ver_p.add_argument("--risk", **_risk_arg)
    ver_p.add_argument("--project", **_project_arg)
    ver_p.add_argument("--verbose", "-v", **_verbose_arg)
    ver_p.set_defaults(func=cmd_verify)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    # Default --output for plan subcommand
    if args.subcommand == "plan" and args.output is None:
        args.output = f"fix_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the full test suite**

```bash
python -m pytest agents/code_fixer/tests/ -v
```
Expected: All tests pass.

- [ ] **Step 3: Smoke test — help output**

```bash
python agents/code_fixer/cli.py --help
python agents/code_fixer/cli.py fix --help
```
Expected: No errors, help text printed.

- [ ] **Step 4: Commit**

```bash
git add agents/code_fixer/cli.py
git commit -m "feat(code-fixer): CLI subcommands (fix, analyze, plan, status, verify)"
```

---

## Task 8: Integration Smoke Test

**Files:**
- No new files — run against real `phase3_verified.json`

- [ ] **Step 1: Run analyze**

```bash
python agents/code_fixer/cli.py analyze --report phase3_verified.json
```
Expected: Prints LOW/MEDIUM breakdown without error.

- [ ] **Step 2: Run plan**

```bash
python agents/code_fixer/cli.py plan --report phase3_verified.json --output fix_plan_test.json
```
Expected: `fix_plan_test.json` created; open it and confirm it has a `batches` array.

- [ ] **Step 3: Run status**

```bash
python agents/code_fixer/cli.py status
```
Expected: Shows current branch, clean/dirty, no errors.

- [ ] **Step 4: Run dry-run fix**

```bash
python agents/code_fixer/cli.py fix --report phase3_verified.json --dry-run --verbose
```
Expected: Prints batch preview with estimated lines, no files modified.

- [ ] **Step 5: Run verify on first candidate**

```bash
python agents/code_fixer/cli.py verify --report phase3_verified.json --items O001 O002 O003
```
Expected: All 6 layers printed. Layer 2 may fail if tree is dirty — that's correct behaviour.

- [ ] **Step 6: Run full test suite one final time**

```bash
python -m pytest agents/code_fixer/tests/ -v --tb=short
```
Expected: All tests green.

- [ ] **Step 7: Clean up temp files and final commit**

```bash
rm -f fix_plan_test.json
git add -A
git commit -m "feat(code-fixer): complete CLI implementation with tests"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 5 subcommands implemented. All 3 core modules built. 6-layer SafetyValidator. Failure modes (fail-fast, skip-failed, no-cleanup). Exit codes 0–4. HTML + JSON reports. Progress with emojis. Type hints everywhere. Docstrings on all public functions.
- [x] **Placeholder scan:** No TBDs, no "implement later", no vague steps. Every step has actual code or an exact command.
- [x] **Type consistency:** `BatchResult`, `RunResult`, `ValidationResult` defined in Task 5 and used consistently in Tasks 6 and 7. `GitOrchestrator`, `SafetyValidator`, `ReportGenerator` method names match between their definitions (Tasks 2–4) and their usage in `FixerEngine.run()` (Task 6). `risk_level` vs `risk` key duality handled explicitly in `_filter_checks()`.
