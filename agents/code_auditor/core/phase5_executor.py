"""
agents/code_auditor/core/phase5_executor.py
===========================================
Phase 5 Executor -- dry-run preview and staged batch removal of dead code.

Contains two classes:

* :class:`DryRunExecutor` -- analyses what *would* happen if findings were
  removed.  Produces a :class:`DryRunResult`.  **No files are modified.**

* :class:`BatchRemover` -- actually executes staged deletions (up to 3 items
  per batch) on a dedicated git feature branch.  Leaves committing to STAP 5.

Usage::

    from agents.code_auditor.core.phase5_executor import DryRunExecutor, BatchRemover

    # Preview first
    executor = DryRunExecutor(phase3_verified, phase1_report, phase2_report, verbose=True)
    result = executor.run_dry_run(["U001", "U002"])
    print(result.estimated_impact)

    # Then actually remove (in a feature branch)
    remover = BatchRemover(project_root="/path/to/repo", phase2_report=phase2_report, verbose=True)
    batch = remover.remove_batch(["U001", "U002"], phase3_verified)
    print(batch["branch_created"])
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DryRunResult:
    """Full dry-run impact analysis for a set of findings.

    Attributes
    ----------
    items:
        The finding IDs that were analysed (e.g. ``["U001", "U002"]``).
    files_to_delete:
        Paths of files that would be fully removed (relative to repo root).
    imports_to_remove:
        Import statement strings that appear in other files and would need
        to be cleaned up after the deletion.
    lines_affected:
        Approximate number of source lines that would be removed or altered.
    estimated_impact:
        Human-readable one-liner summarising the overall risk level.
    tests_affected:
        Test file paths that contain references to any removed item.
    warnings:
        Ordered list of human-readable warnings about the planned changes.
    is_safe:
        ``True`` when no critical issues were detected (no API breakage, no
        broken tests that cannot be cleanly updated).
    """

    items: List[str] = field(default_factory=list)
    files_to_delete: List[str] = field(default_factory=list)
    imports_to_remove: List[str] = field(default_factory=list)
    lines_affected: int = 0
    estimated_impact: str = ""
    tests_affected: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_safe: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_file_lines(path: str) -> int:
    """Return the number of lines in *path*, or 0 if unreadable."""
    try:
        return len(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _grep_pattern_in_file(pattern: str, filepath: str) -> List[str]:
    """Return lines in *filepath* that match *pattern* (plain substring)."""
    try:
        text = Path(filepath).read_text(encoding="utf-8", errors="replace")
        return [ln.strip() for ln in text.splitlines() if pattern in ln]
    except OSError:
        return []


def _is_test_file(path: str) -> bool:
    p = Path(path)
    return p.stem.startswith("test_") or p.stem.endswith("_test") or "tests" in p.parts


def _extract_import_lines(symbol: str, filepath: str) -> List[str]:
    """Return every import line in *filepath* that references *symbol*."""
    import_re = re.compile(
        r"^(?:from\s+\S+\s+import\s+.*\b{sym}\b|import\s+.*\b{sym}\b)".format(
            sym=re.escape(symbol)
        )
    )
    try:
        lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        return [ln.strip() for ln in lines if import_re.match(ln.strip())]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DryRunExecutor:
    """Preview what would happen if *items_to_remove* were deleted.

    Parameters
    ----------
    phase3_verified:
        The output of the Phase 3 pipeline -- a dict with at least an
        ``"all_checks"`` list of finding dicts, each containing ``"id"``,
        ``"file"``, ``"name"``, ``"type"``, ``"risk_level"``, and
        ``"evidence"`` keys.
    phase1_report:
        The Phase 1 discovery output -- a dict with at least a
        ``"project_files"`` list of file-path strings and a
        ``"test_files"`` list of test-path strings.
    phase2_report:
        The Phase 2 findings output -- a dict with a ``"findings"`` list.
        Each finding must have ``"id"``, ``"file"``, and ``"name"`` keys.
        Used to resolve file paths when Phase 3 assessments have empty
        ``file`` fields (which is normal -- Phase 3 strips that data).
    verbose:
        When ``True``, progress lines are printed to stdout.
    """

    def __init__(
        self,
        phase3_verified: Dict[str, Any],
        phase1_report: Dict[str, Any],
        phase2_report: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
    ) -> None:
        self._verified = phase3_verified
        self._phase1 = phase1_report
        self._phase2 = phase2_report or {}
        self._verbose = verbose

        # Build lookup: finding_id -> finding dict
        self._findings: Dict[str, Dict[str, Any]] = {}
        for finding in phase3_verified.get("all_checks", []):
            fid = finding.get("id", "")
            if fid:
                self._findings[fid] = finding

        # Build Phase 2 lookup: finding_id -> Phase 2 finding dict
        self._p2_findings: Dict[str, Dict[str, Any]] = {
            f.get("id", ""): f
            for f in self._phase2.get("findings", [])
            if f.get("id")
        }

        # All source files and test files from Phase 1
        self._all_files: List[str] = phase1_report.get("project_files", [])
        self._test_files: List[str] = phase1_report.get("test_files", [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_dry_run(self, items_to_remove: List[str]) -> DryRunResult:
        """Analyse impact of removing *items_to_remove* without touching anything.

        Parameters
        ----------
        items_to_remove:
            List of finding IDs (e.g. ``["U001", "U002"]``).

        Returns
        -------
        DryRunResult
            Complete impact analysis.  No files are modified.
        """
        result = DryRunResult(items=list(items_to_remove))

        files_to_delete: Set[str] = set()
        imports_to_remove: List[str] = []
        tests_affected: Set[str] = set()
        warnings: List[str] = []
        total_lines = 0
        critical_issues: List[str] = []

        for fid in items_to_remove:
            finding = self._findings.get(fid)
            if finding is None:
                warnings.append(f"Finding {fid!r} not found in Phase 3 results -- skipped")
                continue

            # Resolve file path and symbol name -- Phase 3 assessments often
            # have empty file fields, so fall back to the Phase 2 finding.
            item_file = finding.get("file", "") or self._resolve_file_path(fid)
            item_name = finding.get("name", "") or self._resolve_symbol_name(fid)
            item_type = finding.get("type", "unknown").lower()
            risk_level = finding.get("risk_level", "LOW")
            evidence = finding.get("evidence", {})

            if not item_file:
                warnings.append(f"{fid}: no file path found (not in Phase 2 report) -- skipped")
                self._log(f"Skipping {fid}: no file path resolved")
                continue

            self._log(f"Analysing {fid}: {item_name!r} in {item_file}")

            # ----------------------------------------------------------------
            # 1. Determine what would physically be deleted
            # ----------------------------------------------------------------
            if item_type in ("file", "module"):
                # Entire file goes away
                if item_file:
                    files_to_delete.add(item_file)
                    total_lines += _count_file_lines(item_file)
                    self._log(f"  -> full file deletion: {item_file}")
            else:
                # A function / class / variable inside a file
                approx = self._estimate_symbol_lines(item_file, item_name, item_type)
                total_lines += approx
                self._log(f"  -> ~{approx} lines removed from {item_file}")

            # ----------------------------------------------------------------
            # 2. Find imports that other files would need cleaned up
            # ----------------------------------------------------------------
            if item_name:
                for src in self._all_files:
                    if src == item_file:
                        continue
                    imp_lines = _extract_import_lines(item_name, src)
                    for imp in imp_lines:
                        entry = f"{imp}  # in {src}"
                        if entry not in imports_to_remove:
                            imports_to_remove.append(entry)

            # ----------------------------------------------------------------
            # 3. Find affected test files
            # ----------------------------------------------------------------
            referenced_tests: List[str] = []
            for tf in self._test_files:
                if item_name and _grep_pattern_in_file(item_name, tf):
                    referenced_tests.append(tf)
                    tests_affected.add(tf)

            if referenced_tests:
                for tf in referenced_tests:
                    warnings.append(
                        f"{Path(tf).name} references {item_name!r} -- might need updates"
                    )

            # ----------------------------------------------------------------
            # 4. Check safety signals from Phase 3 evidence
            # ----------------------------------------------------------------
            if evidence.get("api_endpoint_check", {}).get("is_api_endpoint"):
                critical_issues.append(
                    f"{fid} ({item_name}) is an API endpoint -- removing would break the public API"
                )

            if evidence.get("database_check", {}).get("is_database_critical"):
                critical_issues.append(
                    f"{fid} ({item_name}) is database-critical -- schema or migration risk"
                )

            if risk_level in ("HIGH", "CRITICAL"):
                critical_issues.append(
                    f"{fid} ({item_name}) has risk level {risk_level} -- requires manual review"
                )

        # ----------------------------------------------------------------
        # 5. Build import count warning
        # ----------------------------------------------------------------
        unique_importing_files: Set[str] = set()
        for entry in imports_to_remove:
            # entry format: "<import stmt>  # in <file>"
            if "  # in " in entry:
                unique_importing_files.add(entry.split("  # in ")[-1])

        if unique_importing_files:
            warnings.append(
                f"Will remove {len(imports_to_remove)} import(s) "
                f"from {len(unique_importing_files)} file(s)"
            )

        # ----------------------------------------------------------------
        # 6. Determine overall safety & impact label
        # ----------------------------------------------------------------
        is_safe = len(critical_issues) == 0

        if not is_safe:
            for issue in critical_issues:
                warnings.append(f"CRITICAL: {issue}")
            estimated_impact = (
                f"High impact -- {len(critical_issues)} critical issue(s) detected; "
                "manual review required before removal"
            )
        elif tests_affected:
            estimated_impact = (
                f"Medium impact -- {len(tests_affected)} test file(s) affected; "
                "update tests before removing"
            )
        elif imports_to_remove:
            estimated_impact = (
                f"Low impact -- {len(imports_to_remove)} import(s) to clean up, "
                "no critical dependencies"
            )
        else:
            estimated_impact = "Minimal impact -- unused code with no known dependents"

        if not critical_issues and not tests_affected and not imports_to_remove:
            warnings.append("No critical issues detected")

        # ----------------------------------------------------------------
        # 7. Assemble result
        # ----------------------------------------------------------------
        result.files_to_delete = sorted(files_to_delete)
        result.imports_to_remove = imports_to_remove
        result.lines_affected = total_lines
        result.estimated_impact = estimated_impact
        result.tests_affected = sorted(tests_affected)
        result.warnings = warnings
        result.is_safe = is_safe

        if self._verbose:
            self._print_summary(result)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_file_path(self, finding_id: str) -> Optional[str]:
        """Look up the file path for *finding_id* in the Phase 2 report.

        Phase 3 assessments strip the ``file`` field; this restores it from
        the original Phase 2 finding.

        Returns
        -------
        str or None
            Relative file path, or ``None`` if not found.
        """
        try:
            p2 = self._p2_findings.get(finding_id, {})
            return p2.get("file") or None
        except Exception as exc:
            self._log(f"Error resolving file path for {finding_id}: {exc}")
            return None

    def _resolve_symbol_name(self, finding_id: str) -> str:
        """Look up the symbol name for *finding_id* in the Phase 2 report.

        Phase 2 findings store the symbol under the ``"item"`` key
        (e.g. ``"useTheme"``, ``"cmd_discover"``), not ``"name"``.
        """
        try:
            p2 = self._p2_findings.get(finding_id, {})
            return p2.get("item") or p2.get("name") or finding_id
        except Exception:
            return finding_id

    def _estimate_symbol_lines(self, filepath: str, symbol: str, kind: str) -> int:
        """Estimate the number of lines occupied by *symbol* in *filepath*.

        Uses a simple heuristic: find the ``def``/``class`` header line,
        then count until the next same-or-lower-indent definition or EOF.
        Falls back to 10 if the symbol cannot be located.
        """
        if not filepath or not symbol:
            return 10
        try:
            lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return 10

        keyword = "class" if kind == "class" else "def"
        header_re = re.compile(
            r"^(?P<indent>\s*)(?:async\s+)?{kw}\s+{sym}\b".format(
                kw=keyword, sym=re.escape(symbol)
            )
        )

        start_idx: Optional[int] = None
        start_indent: int = 0

        for i, line in enumerate(lines):
            m = header_re.match(line)
            if m:
                start_idx = i
                start_indent = len(m.group("indent"))
                break

        if start_idx is None:
            # Might be a variable / constant -- count lines containing the name
            count = sum(1 for ln in lines if symbol in ln)
            return max(count, 1)

        # Walk forward until we hit a new top-level (or same-level) definition
        end_idx = len(lines)
        for j in range(start_idx + 1, len(lines)):
            ln = lines[j]
            stripped = ln.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            current_indent = len(ln) - len(stripped)
            if current_indent <= start_indent and re.match(r"(def |class |async def )", stripped):
                end_idx = j
                break

        return end_idx - start_idx

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[DryRunExecutor] {message}")

    @staticmethod
    def _print_summary(result: DryRunResult) -> None:
        print("\n" + "=" * 60)
        print("DRY RUN SUMMARY")
        print("=" * 60)
        print(f"Items analysed    : {', '.join(result.items)}")
        print(f"Files to delete   : {len(result.files_to_delete)}")
        print(f"Imports to remove : {len(result.imports_to_remove)}")
        print(f"Lines affected    : {result.lines_affected}")
        print(f"Tests affected    : {len(result.tests_affected)}")
        print(f"Is safe           : {result.is_safe}")
        print(f"Impact            : {result.estimated_impact}")
        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# BatchRemover
# ---------------------------------------------------------------------------

_MAX_BATCH_SIZE = 3  # safety cap: never remove more than 3 items at once


@dataclass
class _RemovedItem:
    """Internal record of one successfully removed item."""

    finding_id: str
    filepath: str
    item_name: str
    item_type: str
    lines_removed: int
    action: str  # "file_deleted" | "definition_removed"


class BatchRemover:
    """Execute staged deletions on a dedicated git feature branch.

    One batch removes **at most** :data:`_MAX_BATCH_SIZE` items so that
    changes stay small and reviewable.  The branch is created automatically;
    committing is intentionally left to STAP 5.

    Parameters
    ----------
    project_root:
        Absolute path to the git repository root.
    phase2_report:
        The Phase 2 findings output -- a dict with a ``"findings"`` list.
        Used to resolve file paths and symbol names when the ``all_checks``
        entry for a finding has an empty ``file`` field.
    verbose:
        When ``True``, progress lines are printed to stdout.
    """

    def __init__(
        self,
        project_root: str,
        phase2_report: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
    ) -> None:
        self._root = Path(project_root).resolve()
        self._phase2 = phase2_report or {}
        self._verbose = verbose

        # Build Phase 2 lookup: finding_id -> Phase 2 finding dict
        self._p2_findings: Dict[str, Dict[str, Any]] = {
            f.get("id", ""): f
            for f in self._phase2.get("findings", [])
            if f.get("id")
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def remove_batch(
        self,
        items_to_remove: List[str],
        phase3_verified: Dict[str, Any],
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove up to :data:`_MAX_BATCH_SIZE` items on a new feature branch.

        Parameters
        ----------
        items_to_remove:
            Finding IDs to remove (e.g. ``["U001", "U002"]``).
            Truncated to :data:`_MAX_BATCH_SIZE` if longer.
        phase3_verified:
            Phase 3 output dict containing ``"all_checks"`` list.
        batch_id:
            Optional identifier used in branch naming and output.
            Defaults to ``"{date}-001"``.

        Returns
        -------
        dict
            Batch result matching the STAP 2 output schema.
        """
        today = date.today().isoformat()
        batch_id = batch_id or f"{today}-001"

        # Safety: cap batch size
        if len(items_to_remove) > _MAX_BATCH_SIZE:
            self._log(
                f"Batch capped at {_MAX_BATCH_SIZE} items "
                f"(requested {len(items_to_remove)})"
            )
            items_to_remove = items_to_remove[:_MAX_BATCH_SIZE]

        # Build finding lookup
        findings: Dict[str, Dict[str, Any]] = {
            f["id"]: f
            for f in phase3_verified.get("all_checks", [])
            if f.get("id")
        }

        # Derive branch name from first item id
        first_id = items_to_remove[0] if items_to_remove else "batch"
        branch_name = self.create_feature_branch(f"{first_id}-{today}")

        removed: List[_RemovedItem] = []
        files_deleted: List[str] = []
        errors: List[str] = []

        for fid in items_to_remove:
            finding = findings.get(fid)
            if finding is None:
                errors.append(f"{fid}: not found in Phase 3 results -- skipped")
                self._log(f"Skipping {fid}: not found")
                continue

            # Phase 3 assessments often have empty file fields -- resolve
            # from Phase 2 before giving up.
            filepath  = finding.get("file", "") or self._resolve_file_path(fid)
            item_name = finding.get("name", "") or self._resolve_symbol_name(fid)
            item_type = finding.get("type", "unknown").lower()

            if not filepath:
                errors.append(f"{fid}: no file path (not in Phase 2 report) -- skipped")
                self._log(f"Skipping {fid}: no file path resolved")
                continue

            try:
                if item_type in ("file", "module", "orphan_file"):
                    lines = _count_file_lines(
                        str(self._root / filepath)
                    )
                    self.delete_file(filepath)
                    files_deleted.append(filepath)
                    removed.append(
                        _RemovedItem(
                            finding_id=fid,
                            filepath=filepath,
                            item_name=item_name,
                            item_type=item_type,
                            lines_removed=lines,
                            action="file_deleted",
                        )
                    )
                    self._log(f"Deleted file: {filepath} ({lines} lines)")
                else:
                    # Refine the type with static detection so delete_from_file
                    # can choose the right strategy (Python vs JS/TS)
                    detected = self._detect_item_type(
                        str(self._root / filepath), item_name
                    )
                    effective_type = detected if detected != "unknown" else item_type
                    self._log(
                        f"Type for {item_name!r}: phase3={item_type!r} "
                        f"detected={detected!r} -> using {effective_type!r}"
                    )

                    lines = self.delete_from_file(filepath, item_name, effective_type)
                    removed.append(
                        _RemovedItem(
                            finding_id=fid,
                            filepath=filepath,
                            item_name=item_name,
                            item_type=effective_type,
                            lines_removed=lines,
                            action="definition_removed",
                        )
                    )
                    self._log(
                        f"Removed {effective_type} {item_name!r} from {filepath} "
                        f"({lines} lines)"
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{fid} ({item_name}): {exc}")
                self._log(f"ERROR processing {fid}: {exc}")

        total_lines = sum(r.lines_removed for r in removed)
        status = "success" if removed and not errors else (
            "partial" if removed else "failed"
        )

        result: Dict[str, Any] = {
            "batch_id": batch_id,
            "branch_created": branch_name,
            "files_deleted": files_deleted,
            "items_removed": [r.finding_id for r in removed],
            "total_lines_removed": total_lines,
            "status": status,
            "next_step": "Run import cleanup" if status != "failed" else "Review errors",
        }

        if errors:
            result["errors"] = errors

        if self._verbose:
            self._print_batch_summary(result)

        return result

    def create_feature_branch(self, batch_id: str) -> str:
        """Create and check out a new git branch for this removal batch.

        Parameters
        ----------
        batch_id:
            Descriptive suffix for the branch name
            (e.g. ``"U001-2025-04-08"``).

        Returns
        -------
        str
            The full branch name that was created.

        Raises
        ------
        RuntimeError
            If the git command fails.
        """
        branch_name = f"audit/remove-{batch_id}"
        self._git("checkout", "-b", branch_name)
        self._log(f"Created branch: {branch_name}")
        return branch_name

    def delete_file(self, filepath: str) -> None:
        """Remove *filepath* from the working tree and the git index.

        Parameters
        ----------
        filepath:
            Path relative to :attr:`project_root`.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        RuntimeError
            If ``git rm`` fails.
        """
        abs_path = self._root / filepath
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {abs_path}")
        self._git("rm", "-f", filepath)
        self._log(f"git rm: {filepath}")

    def delete_from_file(
        self,
        filepath: str,
        item_name: str,
        item_type: str = "function",
    ) -> int:
        """Remove a function, class, or JS/TS export from *filepath* in place.

        Handles:
        - Python: ``def``, ``class``, ``@dataclass`` (indentation-based extent)
        - JavaScript/TypeScript: ``export const``, ``const``, ``function``,
          arrow functions, and object literals (brace-count-based extent)

        Parameters
        ----------
        filepath:
            Path relative to :attr:`project_root`.
        item_name:
            Exact name of the symbol to remove.
        item_type:
            Hint used only when the file extension is ambiguous.

        Returns
        -------
        int
            Number of lines removed.

        Raises
        ------
        FileNotFoundError
            If *filepath* does not exist.
        ValueError
            If *item_name* cannot be located in the file.
        """
        abs_path = self._root / filepath
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {abs_path}")

        content = abs_path.read_text(encoding="utf-8", errors="replace")
        original_lines = content.split("\n")

        is_js = filepath.endswith((".js", ".jsx", ".ts", ".tsx"))
        is_py = filepath.endswith(".py")

        new_lines: List[str] = []
        i = 0
        deleted = False

        while i < len(original_lines):
            line = original_lines[i]

            # ── Python ──────────────────────────────────────────────────
            if is_py:
                func_re = re.compile(
                    rf"^(def|class)\s+{re.escape(item_name)}\s*[\(:]"
                )
                if func_re.match(line):
                    deleted = True
                    indent_level = len(line) - len(line.lstrip())

                    # Remove decorators immediately preceding this definition
                    j = len(new_lines) - 1
                    while j >= 0 and re.match(r"^\s*@", new_lines[j]):
                        new_lines.pop()
                        j -= 1

                    i += 1  # skip the header line

                    # Skip the indented body
                    while i < len(original_lines):
                        next_line = original_lines[i]
                        if not next_line.strip():
                            i += 1
                            continue
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= indent_level:
                            break
                        i += 1

                    continue  # don't append the header

            # ── JavaScript / TypeScript ──────────────────────────────────
            elif is_js:
                sym = re.escape(item_name)
                patterns = [
                    rf"^export\s+(const|function|async\s+function|type|interface)\s+{sym}\s*[=(\{{:]",
                    rf"^const\s+{sym}\s*[=:]",
                    rf"^(function|async\s+function)\s+{sym}\s*\(",
                    rf"^(export\s+)?const\s+{sym}\s*=\s*\(",
                ]
                if any(re.match(p, line) for p in patterns):
                    deleted = True

                    # Count braces/parens from the header line
                    brace_count = line.count("{") - line.count("}")
                    paren_count = line.count("(") - line.count(")")
                    i += 1

                    # Consume continuation lines until all delimiters close
                    while i < len(original_lines) and (
                        brace_count > 0 or paren_count > 0
                    ):
                        nl = original_lines[i]
                        brace_count += nl.count("{") - nl.count("}")
                        paren_count += nl.count("(") - nl.count(")")
                        i += 1

                    continue  # don't append the header or its body

            new_lines.append(line)
            i += 1

        if not deleted:
            # Fall back to the Python-only bound finder for edge cases
            # (e.g. a .py file whose item_type was passed as 'export')
            if is_py:
                lines_with_ends = [l + "\n" for l in original_lines]
                start_idx, end_idx = self._find_definition_bounds(
                    lines_with_ends, item_name, item_type
                )
                while end_idx > start_idx and not lines_with_ends[end_idx - 1].strip():
                    end_idx -= 1
                lines_removed = end_idx - start_idx
                cleaned = lines_with_ends[:start_idx] + lines_with_ends[end_idx:]
                abs_path.write_text("".join(cleaned), encoding="utf-8")
                self._log(f"Removed {lines_removed} lines ({item_name}) from {filepath}")
                return lines_removed

            raise ValueError(f"Could not locate '{item_name}' in {filepath}")

        lines_removed = len(original_lines) - len(new_lines)
        abs_path.write_text("\n".join(new_lines), encoding="utf-8")
        self._log(f"Removed {lines_removed} lines ({item_name}) from {filepath}")
        return lines_removed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_file_path(self, finding_id: str) -> Optional[str]:
        """Look up the file path for *finding_id* in the Phase 2 report.

        Returns
        -------
        str or None
            Relative file path, or ``None`` if not found.
        """
        try:
            p2 = self._p2_findings.get(finding_id, {})
            return p2.get("file") or None
        except Exception as exc:
            self._log(f"Error resolving file path for {finding_id}: {exc}")
            return None

    def _resolve_symbol_name(self, finding_id: str) -> str:
        """Look up the symbol name for *finding_id* in the Phase 2 report.

        Phase 2 findings store the symbol under the ``"item"`` key
        (e.g. ``"useTheme"``, ``"cmd_discover"``), not ``"name"``.
        """
        try:
            p2 = self._p2_findings.get(finding_id, {})
            return p2.get("item") or p2.get("name") or finding_id
        except Exception:
            return finding_id

    def _detect_item_type(self, abs_filepath: str, item_name: str) -> str:
        """Detect the kind of symbol *item_name* in *abs_filepath*.

        Returns one of ``'function'``, ``'class'``, ``'dataclass'``,
        ``'export'``, ``'arrow_function'``, or ``'unknown'``.

        Parameters
        ----------
        abs_filepath:
            Absolute path to the source file.
        item_name:
            Exact symbol name to look for.
        """
        try:
            path = Path(abs_filepath)
            if not path.exists():
                return "unknown"
            content = path.read_text(encoding="utf-8", errors="replace")
            sym = re.escape(item_name)

            if abs_filepath.endswith(".py"):
                if re.search(rf"^\s*def\s+{sym}\s*\(", content, re.MULTILINE):
                    return "function"
                if re.search(rf"^\s*class\s+{sym}\s*[\(:]", content, re.MULTILINE):
                    # Distinguish plain class from @dataclass
                    lines = content.splitlines()
                    for idx, line in enumerate(lines):
                        if re.match(rf"\s*class\s+{sym}\s*[\(:]", line):
                            if idx > 0 and "@dataclass" in lines[idx - 1]:
                                return "dataclass"
                            return "class"

            elif abs_filepath.endswith((".js", ".jsx", ".ts", ".tsx")):
                if re.search(rf"export\s+const\s+{sym}\s*=", content):
                    return "export"
                if re.search(rf"const\s+{sym}\s*=\s*\(", content):
                    return "arrow_function"
                if re.search(rf"function\s+{sym}\s*\(", content):
                    return "function"
                if re.search(rf"export\s+(?:function|async\s+function)\s+{sym}\s*\(", content):
                    return "export"

        except Exception as exc:  # noqa: BLE001
            self._log(f"Warning: could not detect type for {item_name}: {exc}")

        return "unknown"

    def _find_definition_bounds(
        self,
        lines: List[str],
        symbol: str,
        kind: str,
    ) -> Tuple[int, int]:
        """Return ``(start, end)`` line indices for *symbol*'s definition.

        *start* is inclusive, *end* is exclusive (Python slice convention).

        Raises
        ------
        ValueError
            If *symbol* is not found.
        """
        keyword = "class" if kind == "class" else "def"
        header_re = re.compile(
            r"^(?P<indent>\s*)(?:async\s+)?{kw}\s+{sym}\b".format(
                kw=keyword, sym=re.escape(symbol)
            )
        )

        start_idx: Optional[int] = None
        start_indent: int = 0

        for i, line in enumerate(lines):
            m = header_re.match(line)
            if m:
                start_idx = i
                start_indent = len(m.group("indent"))
                break

        if start_idx is None:
            raise ValueError(
                f"Cannot locate '{keyword} {symbol}' in provided source"
            )

        # Walk forward to find where the definition ends
        end_idx = len(lines)
        for j in range(start_idx + 1, len(lines)):
            raw = lines[j]
            stripped = raw.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            current_indent = len(raw) - len(raw.lstrip())
            if current_indent <= start_indent and re.match(
                r"(?:async\s+)?(?:def |class )", stripped
            ):
                end_idx = j
                break

        return start_idx, end_idx

    def _git(self, *args: str) -> str:
        """Run a git command in :attr:`project_root` and return stdout.

        Raises
        ------
        RuntimeError
            If the command exits with a non-zero code.
        """
        cmd = ["git", *args]
        self._log(f"$ {' '.join(cmd)}")
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
        return result.stdout.strip()

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[BatchRemover] {message}")

    @staticmethod
    def _print_batch_summary(result: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("BATCH REMOVAL SUMMARY")
        print("=" * 60)
        print(f"Batch ID          : {result['batch_id']}")
        print(f"Branch            : {result['branch_created']}")
        print(f"Status            : {result['status']}")
        print(f"Items removed     : {', '.join(result['items_removed']) or 'none'}")
        print(f"Files deleted     : {len(result['files_deleted'])}")
        print(f"Lines removed     : {result['total_lines_removed']}")
        print(f"Next step         : {result['next_step']}")
        if result.get("errors"):
            print("\nErrors:")
            for e in result["errors"]:
                print(f"  - {e}")
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# ImportCleaner
# ---------------------------------------------------------------------------


@dataclass
class _FileImportEdit:
    """Record of import-related changes made to one file."""

    file: str
    imports_removed: List[str] = field(default_factory=list)
    lines_fixed: int = 0


class ImportCleaner:
    """Fix broken import statements after code has been deleted.

    Scans every ``*.py`` file under *project_root*, parses each import
    statement, and removes references to any symbol in *deleted_names*.
    Handles three cases:

    1. ``import foo`` / ``import foo as bar`` -- entire line removed when
       the module itself was deleted.
    2. ``from pkg import a, b, c`` -- individual names removed; line kept
       if at least one name survives, removed if all names are deleted.
    3. Multi-line ``from pkg import (\\n    a,\\n    b,\\n)`` -- the whole
       parenthesised block is rewritten or removed.

    Only import statements are touched; call-sites and other code are left
    intact.

    Parameters
    ----------
    project_root:
        Absolute path to the repository root.  All ``*.py`` files under
        this directory are candidates for cleanup.
    verbose:
        When ``True``, progress lines are printed to stdout.
    """

    # Matches a bare "import X" or "import X as Y" (possibly comma-separated)
    _BARE_IMPORT_RE = re.compile(r"^(\s*)import\s+(.+)$")

    # Matches "from X import Y" (single line, no parentheses)
    _FROM_IMPORT_RE = re.compile(r"^(\s*)from\s+(\S+)\s+import\s+([^(#\n]+)")

    # Detects the opening of a multi-line "from X import (" block
    _FROM_IMPORT_OPEN_RE = re.compile(r"^(\s*)from\s+(\S+)\s+import\s*\(")

    def __init__(self, project_root: str, verbose: bool = False) -> None:
        self._root = Path(project_root).resolve()
        self._verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cleanup_imports(self, deleted_names: List[str]) -> Dict[str, Any]:
        """Remove every import of *deleted_names* from all Python files.

        Parameters
        ----------
        deleted_names:
            Symbol names (functions, classes, modules) that have been
            deleted and whose imports should be cleaned up.  These are the
            bare names, e.g. ``["old_func", "LegacyHelper"]``.

        Returns
        -------
        dict
            Cleanup result matching the STAP 3 output schema.
        """
        if not deleted_names:
            return self._build_result([], status="skipped")

        deleted_set: Set[str] = set(deleted_names)
        py_files = sorted(self._root.rglob("*.py"))
        edits: List[_FileImportEdit] = []

        for py_file in py_files:
            try:
                edit = self._process_file(py_file, deleted_set)
            except OSError as exc:
                self._log(f"Cannot read {py_file}: {exc}")
                continue

            if edit.imports_removed:
                edits.append(edit)

        return self._build_result(edits, status="success")

    # ------------------------------------------------------------------
    # File-level processing
    # ------------------------------------------------------------------

    def _process_file(self, path: Path, deleted: Set[str]) -> _FileImportEdit:
        """Parse and rewrite imports in *path*.  Returns the edit record."""
        edit = _FileImportEdit(file=str(path.relative_to(self._root)))
        original = path.read_text(encoding="utf-8", errors="replace")
        lines = original.splitlines(keepends=True)

        new_lines: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip("\n\r")

            # ----------------------------------------------------------
            # Case 3: multi-line "from X import (\n    a,\n    b,\n)"
            # ----------------------------------------------------------
            m_open = self._FROM_IMPORT_OPEN_RE.match(stripped)
            if m_open:
                block_lines, j = self._collect_paren_block(lines, i)
                rewritten, removed = self._rewrite_paren_block(
                    block_lines, m_open.group(1), m_open.group(2), deleted
                )
                if removed:
                    edit.imports_removed.extend(removed)
                    edit.lines_fixed += len(block_lines) - len(rewritten)
                new_lines.extend(rewritten)
                i = j
                continue

            # ----------------------------------------------------------
            # Case 2: single-line "from X import a, b, c"
            # ----------------------------------------------------------
            m_from = self._FROM_IMPORT_RE.match(stripped)
            if m_from:
                indent, module, names_raw = (
                    m_from.group(1),
                    m_from.group(2),
                    m_from.group(3),
                )
                # Preserve inline comment if present
                comment = ""
                if "#" in names_raw:
                    names_raw, comment = names_raw.split("#", 1)
                    comment = "  #" + comment

                names = self._parse_names(names_raw)
                surviving = [n for n in names if n.split(" as ")[0].strip() not in deleted]
                removed_here = [n for n in names if n.split(" as ")[0].strip() in deleted]

                if removed_here:
                    original_stmt = f"from {module} import {', '.join(names)}"
                    edit.imports_removed.append(original_stmt.strip())
                    if surviving:
                        new_line = (
                            f"{indent}from {module} import "
                            f"{', '.join(surviving)}{comment}\n"
                        )
                        new_lines.append(new_line)
                        edit.lines_fixed += 1
                        self._log(
                            f"  Trimmed: {original_stmt!r} -> kept {surviving}"
                        )
                    else:
                        # Entire import is dead -- drop the line
                        edit.lines_fixed += 1
                        self._log(f"  Dropped: {original_stmt!r}")
                    i += 1
                    continue

            # ----------------------------------------------------------
            # Case 1: bare "import foo" or "import foo as bar"
            # ----------------------------------------------------------
            m_bare = self._BARE_IMPORT_RE.match(stripped)
            if m_bare:
                indent, modules_raw = m_bare.group(1), m_bare.group(2)
                segments = [s.strip() for s in modules_raw.split(",")]
                surviving_segs: List[str] = []
                removed_segs: List[str] = []
                for seg in segments:
                    # "foo", "foo as bar", or "pkg.mod"
                    base = seg.split(" as ")[0].strip().split(".")[0]
                    if base in deleted:
                        removed_segs.append(seg)
                    else:
                        surviving_segs.append(seg)

                if removed_segs:
                    original_stmt = f"import {', '.join(segments)}"
                    edit.imports_removed.append(original_stmt.strip())
                    if surviving_segs:
                        new_line = f"{indent}import {', '.join(surviving_segs)}\n"
                        new_lines.append(new_line)
                        edit.lines_fixed += 1
                        self._log(
                            f"  Trimmed bare import: kept {surviving_segs}"
                        )
                    else:
                        edit.lines_fixed += 1
                        self._log(f"  Dropped bare import: {original_stmt!r}")
                    i += 1
                    continue

            # Default: keep line unchanged
            new_lines.append(line)
            i += 1

        # Write back only if something changed
        if edit.imports_removed:
            rewritten_text = "".join(new_lines)
            path.write_text(rewritten_text, encoding="utf-8")
            self._log(
                f"Saved {edit.file} "
                f"({len(edit.imports_removed)} import(s) cleaned)"
            )

        return edit

    # ------------------------------------------------------------------
    # Multi-line parenthesised block helpers
    # ------------------------------------------------------------------

    def _collect_paren_block(
        self, lines: List[str], start: int
    ) -> Tuple[List[str], int]:
        """Collect lines from *start* up to and including the closing ``)``.

        Returns ``(block_lines, next_index)`` where *next_index* is the
        line after the closing parenthesis.
        """
        block: List[str] = []
        i = start
        while i < len(lines):
            block.append(lines[i])
            if ")" in lines[i]:
                break
            i += 1
        return block, i + 1

    def _rewrite_paren_block(
        self,
        block_lines: List[str],
        indent: str,
        module: str,
        deleted: Set[str],
    ) -> Tuple[List[str], List[str]]:
        """Rewrite or drop a multi-line import block.

        Returns ``(new_lines, removed_stmts)`` where *removed_stmts* is a
        list of the original import statements that were stripped out.
        """
        # Extract all names from inside the parens
        raw_block = "".join(block_lines)
        # Grab everything between the first '(' and last ')'
        inner_match = re.search(r"\(([^)]*)\)", raw_block, re.DOTALL)
        if not inner_match:
            return block_lines, []  # can't parse -- leave unchanged

        inner = inner_match.group(1)
        names = self._parse_names(inner)

        surviving: List[str] = []
        removed: List[str] = []
        for name in names:
            bare = name.split(" as ")[0].strip()
            if bare in deleted:
                removed.append(f"from {module} import {name.strip()}")
            else:
                surviving.append(name.strip())

        if not removed:
            return block_lines, []  # nothing to do

        if not surviving:
            # Drop entire block
            return [], removed

        # Rebuild as single-line or multi-line depending on count
        if len(surviving) == 1:
            new_line = f"{indent}from {module} import {surviving[0]}\n"
            return [new_line], removed

        # Keep multi-line style
        inner_indent = indent + "    "
        new_lines: List[str] = [f"{indent}from {module} import (\n"]
        for name in surviving:
            new_lines.append(f"{inner_indent}{name},\n")
        new_lines.append(f"{indent})\n")
        return new_lines, removed

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_names(raw: str) -> List[str]:
        """Split a comma-separated import name list, preserving ``as`` aliases."""
        parts = [p.strip() for p in raw.replace("\n", " ").split(",")]
        return [p for p in parts if p]

    @staticmethod
    def _build_result(
        edits: List[_FileImportEdit], status: str
    ) -> Dict[str, Any]:
        total_imports = sum(len(e.imports_removed) for e in edits)
        total_lines = sum(e.lines_fixed for e in edits)
        return {
            "files_modified": [e.file for e in edits],
            "imports_removed": total_imports,
            "lines_fixed": total_lines,
            "status": status,
            "modified_files": [
                {
                    "file": e.file,
                    "imports_removed": e.imports_removed,
                    "lines_fixed": e.lines_fixed,
                }
                for e in edits
            ],
        }

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[ImportCleaner] {message}")


# ---------------------------------------------------------------------------
# TestVerifier
# ---------------------------------------------------------------------------


class TestVerifier:
    """Run the test suite and optional linter after a batch removal.

    Executes ``pytest`` (with fallback to ``python -m pytest``) against the
    project's test directory and optionally ``flake8`` against the agents
    directory.  Results are returned as a structured dict so the caller can
    decide whether to proceed to commit or revert.

    Parameters
    ----------
    project_root:
        Absolute path to the repository root.
    verbose:
        When ``True``, full subprocess output is printed in addition to the
        structured summary.
    """

    # Pytest output patterns
    _PYTEST_SUMMARY_RE = re.compile(
        r"=+\s+(.*?)\s+=+\s*$", re.MULTILINE
    )
    _PYTEST_COUNTS_RE = re.compile(
        r"(?:(\d+)\s+passed)?(?:[,\s]+(\d+)\s+failed)?(?:[,\s]+(\d+)\s+error)?",
        re.IGNORECASE,
    )
    _PYTEST_FAILED_LINE_RE = re.compile(r"^FAILED\s+(.+)$", re.MULTILINE)

    # Flake8 output: "path/file.py:10:5: E123 message"
    _FLAKE8_ERROR_RE = re.compile(r":\s*[EF]\d+\s")
    _FLAKE8_WARN_RE  = re.compile(r":\s*[WC]\d+\s")

    def __init__(self, project_root: str, verbose: bool = False) -> None:
        self._root = Path(project_root).resolve()
        self._verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tests(self) -> Dict[str, Any]:
        """Execute pytest and return a structured result dict.

        Tries ``pytest`` first; falls back to ``python -m pytest`` if the
        ``pytest`` executable is not found on PATH.

        Returns
        -------
        dict
            Keys: ``tests``, ``overall_status``, ``safe_to_commit``,
            and optionally ``revert_recommendation``.
        """
        test_dir = self._root / "tests"
        if not test_dir.exists():
            # Fall back to project root so pytest can discover tests anywhere
            test_dir = self._root

        self._log(f"Running pytest in: {test_dir}")
        raw_output, exit_code = self._run_pytest(str(test_dir))

        if self._verbose:
            print(raw_output)

        test_result = self._parse_pytest_output(raw_output, exit_code)
        overall = "PASS" if test_result["status"] == "PASS" else "FAIL"
        safe = overall == "PASS"

        result: Dict[str, Any] = {
            "tests": test_result,
            "overall_status": overall,
            "safe_to_commit": safe,
        }

        if not safe:
            result["revert_recommendation"] = (
                "Tests failed after removal. "
                "Consider reverting: git reset --hard HEAD"
            )
            self._log("FAIL -- revert recommended")
        else:
            self._log("PASS -- safe to proceed to commit")

        if self._verbose:
            self._print_test_summary(result)

        return result

    def run_linter(self) -> Dict[str, Any]:
        """Execute flake8 against the agents directory and return results.

        Falls back gracefully if flake8 is not installed (returns status
        ``"SKIPPED"``).

        Returns
        -------
        dict
            Keys: ``errors``, ``warnings``, ``status``, ``output``.
        """
        agents_dir = self._root / "agents"
        target = str(agents_dir) if agents_dir.exists() else str(self._root)

        self._log(f"Running flake8 on: {target}")
        output, exit_code, skipped = self._run_flake8(target)

        if skipped:
            self._log("flake8 not found -- linting skipped")
            return {
                "errors": 0,
                "warnings": 0,
                "status": "SKIPPED",
                "output": "flake8 not installed",
            }

        if self._verbose:
            print(output)

        error_lines   = [ln for ln in output.splitlines() if self._FLAKE8_ERROR_RE.search(ln)]
        warning_lines = [ln for ln in output.splitlines() if self._FLAKE8_WARN_RE.search(ln)]

        status = "PASS" if exit_code == 0 else "FAIL"
        result: Dict[str, Any] = {
            "errors": len(error_lines),
            "warnings": len(warning_lines),
            "status": status,
            "output": output if (error_lines or warning_lines) else "",
        }

        self._log(
            f"Linter: {len(error_lines)} error(s), "
            f"{len(warning_lines)} warning(s) -- {status}"
        )
        return result

    # ------------------------------------------------------------------
    # Subprocess runners
    # ------------------------------------------------------------------

    def _run_pytest(self, test_path: str) -> Tuple[str, int]:
        """Try ``pytest`` then ``python -m pytest``. Returns (output, exit_code)."""
        for cmd in (
            ["pytest", test_path, "-v", "--tb=short", "--no-header"],
            ["python", "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
        ):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self._root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                combined = result.stdout + result.stderr
                return combined, result.returncode
            except FileNotFoundError:
                continue  # try next variant
            except subprocess.TimeoutExpired:
                return "pytest timed out after 300 seconds", 1

        return "pytest not found on PATH", 1

    def _run_flake8(self, target: str) -> Tuple[str, int, bool]:
        """Run flake8. Returns (output, exit_code, skipped)."""
        for cmd in (
            ["flake8", target, "--max-line-length=120", "--statistics"],
            ["python", "-m", "flake8", target, "--max-line-length=120", "--statistics"],
        ):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self._root),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return result.stdout + result.stderr, result.returncode, False
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return "flake8 timed out", 1, False

        return "", 0, True  # not installed -- skipped

    # ------------------------------------------------------------------
    # Output parsers
    # ------------------------------------------------------------------

    def _parse_pytest_output(self, output: str, exit_code: int) -> Dict[str, Any]:
        """Extract pass/fail counts and failure names from pytest output."""
        passed  = 0
        failed  = 0
        errors  = 0
        failures: List[str] = []

        # Count passed/failed from the final summary line
        # e.g. "5 passed, 2 failed, 1 error in 3.14s"
        for match in self._PYTEST_COUNTS_RE.finditer(output):
            p, f, e = match.group(1), match.group(2), match.group(3)
            if p:
                passed = max(passed, int(p))
            if f:
                failed = max(failed, int(f))
            if e:
                errors = max(errors, int(e))

        # Collect individual FAILED lines
        for m in self._PYTEST_FAILED_LINE_RE.finditer(output):
            failures.append(m.group(1).strip())

        # If pytest wasn't found the output is our error string
        if "not found" in output or "timed out" in output:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failures": [],
                "status": "ERROR",
                "raw_output": output,
            }

        total = passed + failed + errors
        status = "PASS" if exit_code == 0 and failed == 0 and errors == 0 else "FAIL"

        result: Dict[str, Any] = {
            "total": total,
            "passed": passed,
            "failed": failed + errors,
            "status": status,
        }
        if failures:
            result["failures"] = failures
        return result

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[TestVerifier] {message}")

    @staticmethod
    def _print_test_summary(result: Dict[str, Any]) -> None:
        tests = result["tests"]
        print("\n" + "=" * 60)
        print("TEST VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total tests       : {tests.get('total', '?')}")
        print(f"Passed            : {tests.get('passed', '?')}")
        print(f"Failed            : {tests.get('failed', '?')}")
        print(f"Test status       : {tests.get('status', '?')}")
        print(f"Overall           : {result['overall_status']}")
        print(f"Safe to commit    : {result['safe_to_commit']}")
        if result.get("revert_recommendation"):
            print(f"\n*** {result['revert_recommendation']} ***")
        failures = tests.get("failures", [])
        if failures:
            print(f"\nFailed tests ({len(failures)}):")
            for f in failures:
                print(f"  FAILED {f}")
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# GitCommitter
# ---------------------------------------------------------------------------


class GitCommitter:
    """Stage and atomically commit a removal batch on the current branch.

    Each call to :meth:`commit_removal` produces exactly one git commit so
    that every batch can be individually reverted with ``git revert <hash>``.
    No force-pushes or branch switches are performed here -- branch creation
    is handled by :class:`BatchRemover`.

    Parameters
    ----------
    project_root:
        Absolute path to the repository root.
    verbose:
        When ``True``, git command output and a formatted summary are printed.
    """

    # Matches "git commit" short-stat output:
    # " 3 files changed, 0 insertions(+), 245 deletions(-)"
    _STAT_RE = re.compile(
        r"(\d+)\s+files?\s+changed"
        r"(?:,\s*(\d+)\s+insertions?\(\+\))?"
        r"(?:,\s*(\d+)\s+deletions?\(-\))?",
        re.IGNORECASE,
    )

    def __init__(self, project_root: str, verbose: bool = False) -> None:
        self._root = Path(project_root).resolve()
        self._verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commit_removal(
        self,
        batch_id: str,
        items_removed: List[str],
        tests_passed: bool,
        *,
        batch_result: Optional[Dict[str, Any]] = None,
        import_result: Optional[Dict[str, Any]] = None,
        phase3_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Stage all working-tree changes and create one atomic commit.

        Parameters
        ----------
        batch_id:
            Human-readable batch identifier used in the commit subject line
            (e.g. ``"2025-04-08-001"``).
        items_removed:
            Finding IDs that were deleted in this batch
            (e.g. ``["U001", "U002"]``).
        tests_passed:
            ``True`` when :class:`TestVerifier` reported ``safe_to_commit``.
            The commit is blocked when ``False``.
        batch_result:
            Optional output from :meth:`BatchRemover.remove_batch` -- used
            to fill deletion statistics in the commit body.
        import_result:
            Optional output from :meth:`ImportCleaner.cleanup_imports` --
            used to fill import cleanup stats in the commit body.
        phase3_findings:
            Optional ``all_checks`` list from Phase 3 -- used to annotate
            each removed item with its file and symbol name.

        Returns
        -------
        dict
            Commit result matching the STAP 5 output schema.

        Raises
        ------
        RuntimeError
            When ``tests_passed`` is ``False`` (commit is blocked) or when
            the git staging / commit command fails.
        """
        if not tests_passed:
            msg = (
                "Commit blocked: tests did not pass. "
                "Fix failures or revert with: git reset --hard HEAD"
            )
            self._log(f"BLOCKED -- {msg}")
            raise RuntimeError(msg)

        # Resolve current branch name
        branch_name = self._git("rev-parse", "--abbrev-ref", "HEAD")

        # Build the structured commit message
        commit_message = self._build_commit_message(
            batch_id=batch_id,
            items_removed=items_removed,
            branch_name=branch_name,
            batch_result=batch_result or {},
            import_result=import_result or {},
            phase3_findings=phase3_findings or [],
        )

        # Stage everything (deletions + in-place edits)
        self._git("add", "-A")
        self._log("Staged all changes (git add -A)")

        # Commit and capture the shortstat output
        raw_commit = self._git("commit", f"--message={commit_message}")
        self._log(f"Commit output:\n{raw_commit}")

        # Retrieve the full commit hash
        commit_hash = self._git("rev-parse", "HEAD")

        # Parse change statistics from commit output
        files_changed, insertions, deletions = self._parse_stat(raw_commit)

        timestamp = self._git("log", "-1", "--format=%cI", "HEAD")

        result: Dict[str, Any] = {
            "commit_hash": commit_hash,
            "branch_name": branch_name,
            "timestamp": timestamp,
            "status": "committed",
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "message": f"refactor(cleanup): remove unused code - {batch_id}",
            "rollback_command": f"git revert {commit_hash}",
        }

        if self._verbose:
            self._print_commit_summary(result)

        return result

    # ------------------------------------------------------------------
    # Commit message builder
    # ------------------------------------------------------------------

    def _build_commit_message(
        self,
        batch_id: str,
        items_removed: List[str],
        branch_name: str,
        batch_result: Dict[str, Any],
        import_result: Dict[str, Any],
        phase3_findings: List[Dict[str, Any]],
    ) -> str:
        """Construct the full multi-line commit message body."""

        # Subject line
        subject = f"refactor(cleanup): remove unused code - {batch_id}"

        # Build finding lookup for annotations
        finding_map: Dict[str, Dict[str, Any]] = {
            f.get("id", ""): f for f in phase3_findings if f.get("id")
        }

        # Removed items block
        item_lines: List[str] = []
        for fid in items_removed:
            finding = finding_map.get(fid)
            if finding:
                filepath = finding.get("file", "?")
                name     = finding.get("name", "?")
                kind     = finding.get("type", "unknown")
                item_lines.append(f"  {fid}: {filepath}: {name}() [{kind}]")
            else:
                item_lines.append(f"  {fid}")
        items_block = "\n".join(item_lines) if item_lines else "  (none)"

        # Verification block
        tests_line   = "  Tests:   PASSING"
        imports_line = (
            f"  Imports: {import_result.get('imports_removed', 0)} cleaned"
            if import_result else "  Imports: N/A"
        )
        verify_block = "\n".join(["  Phase 3: SAFE", tests_line, imports_line])

        # Impact block
        files_del  = len(batch_result.get("files_deleted", []))
        lines_del  = batch_result.get("total_lines_removed", 0)
        imp_count  = import_result.get("imports_removed", 0)
        impact_block = (
            f"  {files_del} file(s) deleted\n"
            f"  {lines_del} lines removed\n"
            f"  {imp_count} import(s) cleaned"
        )

        # Rollback note (placeholder -- real hash inserted after commit)
        rollback_note = "  git revert <this-commit-hash>"

        message = (
            f"{subject}\n"
            f"\n"
            f"Removed items:\n{items_block}\n"
            f"\n"
            f"Verification:\n{verify_block}\n"
            f"\n"
            f"Impact:\n{impact_block}\n"
            f"\n"
            f"Rollback:\n{rollback_note}\n"
        )

        self._log(f"Commit message:\n{message}")
        return message

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _git(self, *args: str) -> str:
        """Run a git command in project_root. Returns stripped stdout.

        Raises
        ------
        RuntimeError
            If the command exits with a non-zero code.
        """
        cmd = ["git", *args]
        self._log(f"$ {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed (exit {proc.returncode}):\n"
                f"{proc.stderr.strip()}"
            )
        return proc.stdout.strip()

    def _parse_stat(self, commit_output: str) -> Tuple[int, int, int]:
        """Extract (files_changed, insertions, deletions) from commit output."""
        m = self._STAT_RE.search(commit_output)
        if not m:
            return 0, 0, 0
        files  = int(m.group(1))
        ins    = int(m.group(2)) if m.group(2) else 0
        dels   = int(m.group(3)) if m.group(3) else 0
        return files, ins, dels

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[GitCommitter] {message}")

    @staticmethod
    def _print_commit_summary(result: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("GIT COMMIT SUMMARY")
        print("=" * 60)
        print(f"Status            : {result['status']}")
        print(f"Hash              : {result['commit_hash']}")
        print(f"Branch            : {result['branch_name']}")
        print(f"Timestamp         : {result['timestamp']}")
        print(f"Files changed     : {result['files_changed']}")
        print(f"Insertions        : {result['insertions']}")
        print(f"Deletions         : {result['deletions']}")
        print(f"Rollback          : {result['rollback_command']}")
        print(f"\nMessage: {result['message']}")
        print("=" * 60 + "\n")
