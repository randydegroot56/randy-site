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
