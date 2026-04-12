"""
agents/code_auditor/core/phase5_analyzer.py
===========================================
Phase 5 Batch Analyzer -- compile, display, and export a summary report
after a removal batch has been executed and committed.

The analyzer is intentionally read-only: it never modifies files or runs
git commands.  Its job is to make the batch outcome human-readable and to
suggest which items should go into the *next* removal batch.

Usage::

    from agents.code_auditor.core.phase5_analyzer import Phase5BatchAnalyzer

    analyzer = Phase5BatchAnalyzer(batch_result, verbose=True)
    report   = analyzer.generate_batch_report()
    analyzer.print_summary()
    suggestion = analyzer.suggest_next_batch()
    analyzer.export_to_json("phase5_report.json")

``batch_result`` is the combined output dict produced by the STAP 1-5
pipeline.  Expected top-level keys (all optional -- missing keys are
treated as zero / unknown):

    batch_id        str
    dry_run         DryRunResult.to_dict()
    batch           BatchRemover.remove_batch() output
    import_cleanup  ImportCleaner.cleanup_imports() output
    test_verify     TestVerifier.run_tests() output
    commit          GitCommitter.commit_removal() output
    phase3_verified Phase 3 all_checks list (for next-batch suggestions)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WIDTH = 68          # console ruler width
_BATCH_SIZE = 3      # items per next-batch suggestion


# ---------------------------------------------------------------------------
# Phase5BatchAnalyzer
# ---------------------------------------------------------------------------


class Phase5BatchAnalyzer:
    """Compile and display a summary report for a completed removal batch.

    Parameters
    ----------
    batch_result:
        Combined pipeline output dict (see module docstring for shape).
    verbose:
        When ``True``, :meth:`print_summary` output is automatically shown
        after :meth:`generate_batch_report` is called.
    """

    def __init__(
        self,
        batch_result: Dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self._raw = batch_result
        self._verbose = verbose
        self._report: Optional[Dict[str, Any]] = None   # cached after first call

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_batch_report(self) -> Dict[str, Any]:
        """Compile all pipeline sub-results into one structured report.

        Returns
        -------
        dict
            Report matching the STAP 6 output schema.  The dict is also
            cached so repeated calls are free.
        """
        if self._report is not None:
            return self._report

        batch   = self._raw.get("batch",          {})
        imports = self._raw.get("import_cleanup",  {})
        tests   = self._raw.get("test_verify",     {})
        commit  = self._raw.get("commit",          {})

        # ── statistics ────────────────────────────────────────────────
        items_removed  = len(batch.get("items_removed", []))
        files_deleted  = len(batch.get("files_deleted",  []))
        lines_removed  = batch.get("total_lines_removed", 0)
        imports_cleaned = imports.get("imports_removed",  0)
        tests_passed   = tests.get("safe_to_commit", False)
        test_counts    = tests.get("tests", {})

        # ── git info ──────────────────────────────────────────────────
        commit_hash  = commit.get("commit_hash",  "")
        branch_name  = commit.get("branch_name",  "")
        merge_cmd    = (
            f"git checkout main && git merge {branch_name}"
            if branch_name else ""
        )

        # ── changed files list ────────────────────────────────────────
        changed_files = self._compile_changed_files(batch, imports)

        # ── overall status ────────────────────────────────────────────
        batch_status = batch.get("status", "unknown")
        if batch_status == "success" and tests_passed and commit_hash:
            overall_status = "success"
        elif batch_status == "partial":
            overall_status = "partial"
        else:
            overall_status = "failed"

        # ── next batch suggestion ─────────────────────────────────────
        next_suggestion = self.suggest_next_batch()

        self._report = {
            "batch_id":  self._raw.get("batch_id", "unknown"),
            "status":    overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "statistics": {
                "items_removed":  items_removed,
                "files_deleted":  files_deleted,
                "lines_removed":  lines_removed,
                "imports_cleaned": imports_cleaned,
                "tests_passed":   tests_passed,
                "test_total":     test_counts.get("total",  0),
                "test_pass_count": test_counts.get("passed", 0),
            },
            "git": {
                "commit_hash":   commit_hash,
                "branch_name":   branch_name,
                "merge_command": merge_cmd,
                "rollback":      f"git revert {commit_hash}" if commit_hash else "",
            },
            "changed_files":        changed_files,
            "next_batch_suggestion": next_suggestion,
        }

        if self._verbose:
            self.print_summary()

        return self._report

    def print_summary(self) -> None:
        """Print a formatted summary to stdout.

        Calls :meth:`generate_batch_report` if not already done.
        """
        report  = self.generate_batch_report()
        stats   = report["statistics"]
        git     = report["git"]
        nxt     = report["next_batch_suggestion"]
        changed = report["changed_files"]

        status_icon = "SUCCESS" if report["status"] == "success" else (
            "PARTIAL" if report["status"] == "partial" else "FAILED"
        )
        test_label = (
            f"PASS ({stats['test_pass_count']}/{stats['test_total']})"
            if stats["tests_passed"] else "FAIL"
        )

        ruler  = "=" * _WIDTH
        thin   = "-" * _WIDTH

        lines: List[str] = [
            ruler,
            "REMOVAL BATCH COMPLETE",
            f"Status: {status_icon}",
            thin,
            "",
            "STATISTICS",
            self._row("Items removed",   stats["items_removed"]),
            self._row("Files deleted",   stats["files_deleted"]),
            self._row("Lines removed",   stats["lines_removed"]),
            self._row("Imports cleaned", stats["imports_cleaned"]),
            self._row("Tests status",    test_label),
            "",
        ]

        if changed:
            lines.append("CHANGES")
            for entry in changed:
                lines.append(f"  {entry['action']:8s}  {entry['file']}")
                if entry.get("detail"):
                    lines.append(f"           {entry['detail']}")
            lines.append("")

        lines += [
            "GIT",
            f"  Commit : {git['commit_hash'] or '(not committed)'}",
            f"  Branch : {git['branch_name'] or '(unknown)'}",
            f"  Message: refactor(cleanup): remove unused code - {report['batch_id']}",
            "",
            "ROLLBACK",
            f"  {git['rollback'] or '(no commit to revert)'}",
            "",
        ]

        if nxt.get("items"):
            lines += [
                "NEXT STEPS",
                "  1. Review changes : git log -1 -p",
                f"  2. Merge to main  : {git['merge_command']}",
                "  3. Run Phase 5 again for next batch",
                f"  4. Remaining items: {nxt.get('remaining_count', '?')} (review manually)",
                "",
                "NEXT BATCH SUGGESTION",
                f"  Items    : {', '.join(nxt['items'])}",
                f"  Impact   : {nxt.get('estimated_impact', '?')}",
                f"  Safety   : {nxt.get('estimated_safety', '?')}",
            ]
        else:
            lines += [
                "NEXT STEPS",
                "  1. Review changes : git log -1 -p",
                f"  2. Merge to main  : {git['merge_command']}",
                "  3. No further safe items found -- audit complete",
            ]

        lines.append(ruler)
        print("\n".join(lines))

    def suggest_next_batch(self) -> Dict[str, Any]:
        """Pick the next :data:`_BATCH_SIZE` safe items from Phase 3.

        Selects candidates that:
        - Have ``risk_level == "LOW"``
        - Were **not** already removed in this batch
        - Are ordered by descending confidence score

        Returns
        -------
        dict
            Keys: ``items``, ``estimated_impact``, ``estimated_safety``,
            ``remaining_count``.  All empty / zero when no candidates remain.
        """
        already_removed: set = set(
            self._raw.get("batch", {}).get("items_removed", [])
        )

        all_checks: List[Dict[str, Any]] = (
            self._raw
            .get("phase3_verified", {})
            .get("all_checks", [])
        )

        candidates = [
            c for c in all_checks
            if c.get("risk_level") == "LOW"
            and c.get("id") not in already_removed
        ]

        # Sort by confidence descending (higher = safer to remove)
        candidates.sort(
            key=lambda c: c.get("confidence", 0.0),
            reverse=True,
        )

        remaining_count = len(candidates)
        next_items = candidates[:_BATCH_SIZE]

        if not next_items:
            return {
                "items":            [],
                "estimated_impact": "None",
                "estimated_safety": "N/A",
                "remaining_count":  0,
            }

        ids       = [c["id"] for c in next_items]
        avg_conf  = sum(c.get("confidence", 0.0) for c in next_items) / len(next_items)
        total_lines = sum(c.get("lines", 0) for c in next_items)

        impact = self._classify_impact(total_lines)
        safety_pct = f"{round(avg_conf * 100, 1)}%"

        return {
            "items":            ids,
            "estimated_impact": impact,
            "estimated_safety": safety_pct,
            "remaining_count":  remaining_count,
        }

    def export_to_json(self, filepath: str) -> None:
        """Write :meth:`generate_batch_report` output to *filepath* as JSON.

        Parameters
        ----------
        filepath:
            Destination path (absolute or relative to cwd).  Parent
            directories are created if they do not exist.
        """
        report = self.generate_batch_report()
        out = Path(filepath)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )
        if self._verbose:
            print(f"[Phase5BatchAnalyzer] Report saved -> {out.resolve()}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compile_changed_files(
        self,
        batch: Dict[str, Any],
        imports: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Build a unified list of every file touched by this batch."""
        entries: List[Dict[str, str]] = []
        seen: set = set()

        for fp in batch.get("files_deleted", []):
            entries.append({"file": fp, "action": "deleted", "detail": ""})
            seen.add(fp)

        for mod in imports.get("modified_files", []):
            fp = mod.get("file", "")
            if fp in seen:
                continue
            count = mod.get("lines_fixed", 0)
            imp   = mod.get("imports_removed", [])
            detail = (
                f"removed {len(imp)} import(s), fixed {count} line(s)"
                if imp else f"fixed {count} line(s)"
            )
            entries.append({"file": fp, "action": "updated", "detail": detail})
            seen.add(fp)

        return entries

    @staticmethod
    def _classify_impact(total_lines: int) -> str:
        if total_lines == 0:
            return "Minimal"
        if total_lines < 50:
            return "Low"
        if total_lines < 200:
            return "Medium"
        return "High"

    @staticmethod
    def _row(label: str, value: Any, width: int = 40) -> str:
        """Right-dot-aligned key/value row for the summary table."""
        dots = "." * max(1, width - len(label))
        return f"  {label}{dots} {value}"
