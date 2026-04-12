"""SafetyValidator — 6-layer pre-flight checks before any code removal."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from agents.code_fixer.core.git_orchestrator import GitOrchestrator

# Lazily populated on first call to validate_batch_dry_run so that
# code_auditor does not need to be importable at module load time.
# The test suite patches this name at:
#   agents.code_fixer.core.safety_validator.DryRunExecutor
DryRunExecutor = None


@dataclass
class ValidationResult:
    """Result of a single safety validation layer.

    Attributes
    ----------
    passed:
        True when this layer has no blocking issues.
    layer:
        The layer number (1-6).
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
        import agents.code_fixer.core.safety_validator as _self_module

        # Use the module-level name so tests can patch it
        executor_cls = _self_module.DryRunExecutor

        if executor_cls is None:
            # Attempt real import and cache at module level
            try:
                from agents.code_auditor.core.phase5_executor import DryRunExecutor as _DRE
                _self_module.DryRunExecutor = _DRE
                executor_cls = _DRE
            except ImportError as exc:
                return ValidationResult(
                    passed=False,
                    layer=5,
                    message=f"cannot import DryRunExecutor: {exc}",
                    details=["Run from repo root: python agents/code_fixer/cli.py ..."],
                )

        try:
            executor = executor_cls(
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
                message="dry-run flagged batch as unsafe",
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
