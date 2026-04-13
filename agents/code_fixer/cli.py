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
                print(
                    f"Pre-flight layer {result.layer} failed: {result.message}",
                    file=sys.stderr,
                )
                raise SystemExit(3)

        # Global layers 3+4: check all candidate IDs exist and are within risk threshold
        all_candidate_ids = [c["id"] for c in self._candidates]
        if all_candidate_ids:
            layer3 = validator.validate_items_exist(all_candidate_ids)
            if not layer3.passed:
                print(f"Pre-flight layer 3 failed: {layer3.message}", file=sys.stderr)
                raise SystemExit(3)
            layer4 = validator.validate_risk_filter(all_candidate_ids, max_risk=self.risk)
            if not layer4.passed:
                print(f"Pre-flight layer 4 failed: {layer4.message}", file=sys.stderr)
                raise SystemExit(3)

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
                # Attempt best-effort cleanup — we don't know if a branch was created
                if not self.no_cleanup:
                    try:
                        current = git.current_branch()
                        if current != "main":
                            git.cleanup_branch(current)
                    except RuntimeError:
                        pass  # best effort only
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


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_fix(args: argparse.Namespace) -> int:
    """Execute batched code removal.

    Loads phase3_verified.json, builds batches, runs the full remove ->
    test -> commit loop, and writes HTML + JSON reports.
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
        print("\n[DRY RUN -- no changes will be made]\n")
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
    """Print a fixability summary -- read-only, no changes."""
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
        print("\u2705 All layers passed -- safe to run: fixer fix --items " + " ".join(item_ids))
        return 0
    else:
        print("\u274c Verification failed -- do not execute until issues are resolved")
        return 3


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argparse parser."""
    parser = argparse.ArgumentParser(
        prog="code-fixer",
        description="Code Fixer Agent -- batch orchestrator for Code Auditor findings.",
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
