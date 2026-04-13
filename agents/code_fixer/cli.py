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

# Module-level names so tests can patch them via agents.code_fixer.cli.*
try:
    from agents.code_fixer.core.safety_validator import SafetyValidator
    from agents.code_fixer.core.git_orchestrator import GitOrchestrator
    from agents.code_fixer.core.report_generator import ReportGenerator
    from agents.code_auditor.core.phase5_executor import BatchRemover, DryRunExecutor
except ImportError:
    SafetyValidator = GitOrchestrator = ReportGenerator = BatchRemover = DryRunExecutor = None  # type: ignore[assignment,misc]


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

    def run(self) -> "RunResult":
        """Execute the full batch loop: validate -> remove -> test -> commit.

        Returns
        -------
        RunResult
            Summary of the entire run including per-batch results.
        """
        global SafetyValidator, GitOrchestrator, BatchRemover, ReportGenerator  # noqa: PLW0603
        if SafetyValidator is None:
            from agents.code_fixer.core.safety_validator import SafetyValidator
        if GitOrchestrator is None:
            from agents.code_fixer.core.git_orchestrator import GitOrchestrator
        if ReportGenerator is None:
            from agents.code_fixer.core.report_generator import ReportGenerator
        if BatchRemover is None:
            try:
                from agents.code_auditor.core.phase5_executor import BatchRemover
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
        global DryRunExecutor  # noqa: PLW0603
        if DryRunExecutor is None:
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
