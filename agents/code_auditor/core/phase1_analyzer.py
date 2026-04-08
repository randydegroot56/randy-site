"""
agents/code_auditor/core/phase1_analyzer.py
============================================
Analyzes the JSON report produced by Phase 1 Discovery and surfaces
actionable insights: oversized files, circular imports, isolated/orphaned
files, and overly complex modules.

Usage::

    from agents.code_auditor.core.phase1_analyzer import ReportAnalyzer

    analyzer = ReportAnalyzer("phase1_report.json")
    insights = analyzer.analyze()
    analyzer.print_summary()
    analyzer.export_csv("phase1_report.csv")

CLI::

    python -m agents.code_auditor.core.phase1_analyzer phase1_report.json
    python -m agents.code_auditor.core.phase1_analyzer phase1_report.json --csv out.csv

Expected JSON report structure (produced by Phase1Discovery)::

    {
      "metadata": {
        "total_files": 84,
        "total_lines": 12840,
        "scan_duration_seconds": 2.1,
        "root_path": "/projects/myapp"
      },
      "files": [
        {
          "path": "src/app/page.js",
          "file_type": "javascript",
          "lines": 210,
          "size_bytes": 6800,
          "imports_count": 5,
          "exports_count": 3,
          "complexity_score": 12.0,
          "imports": ["react", "./components/Foo"],
          "exports": ["default", "helper"]
        },
        ...
      ],
      "circular_imports": [
        ["agents/scraper.py", "backends/redis.py", "agents/scraper.py"]
      ]
    }
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class AnalysisInsight:
    """A single finding produced by one of the analysis passes.

    Attributes
    ----------
    title:
        Short, human-readable heading for the finding.
    description:
        One- or two-sentence explanation of what was found and why it matters.
    severity:
        ``"info"`` -- worth noting but not urgent.
        ``"warning"`` -- should be addressed before the next refactor.
        ``"critical"`` -- likely causes runtime errors or data loss.
    affected_files:
        Relative paths of every file implicated by this finding.
    """

    title: str
    description: str
    severity: str  # "info" | "warning" | "critical"
    affected_files: List[str] = field(default_factory=list)

    # ASCII prefix used in printed output
    _SEVERITY_ICON: Dict[str, str] = field(default_factory=lambda: {
        "info":     "[i]",
        "warning":  "[!]",
        "critical": "[X]",
    }, init=False, repr=False, compare=False)

    def icon(self) -> str:
        """Return the emoji icon for this insight's severity."""
        return self._SEVERITY_ICON.get(self.severity, "  ")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class ReportAnalyzer:
    """Read a Phase 1 JSON report and derive actionable insights.

    Parameters
    ----------
    report_path:
        Path to the ``phase1_report.json`` file written by ``Phase1Discovery``.
    """

    # Multiplier above average size that marks a file as "large"
    LARGE_FILE_MULTIPLIER: float = 2.5
    # Minimum imports + exports below which a file is considered "isolated"
    ISOLATION_THRESHOLD: int = 2
    # Complexity score above which a file is flagged
    COMPLEXITY_THRESHOLD: float = 30.0

    def __init__(self, report_path: str) -> None:
        self.report_path = Path(report_path)
        self._report: Dict[str, Any] = {}
        self._insights: List[AnalysisInsight] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_report(self) -> Dict[str, Any]:
        """Load and return the JSON report as a plain dict.

        Raises
        ------
        FileNotFoundError
            If *report_path* does not exist.
        ValueError
            If the file cannot be parsed as JSON or is missing required keys.
        """
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Report not found: {self.report_path}"
            )
        try:
            with self.report_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse JSON from {self.report_path}: {exc}"
            ) from exc

        if "files" not in data:
            raise ValueError(
                f"Report is missing the required 'files' key: {self.report_path}"
            )
        return data

    @staticmethod
    def _file_entry_lines(entry: Dict[str, Any]) -> int:
        """Return the line count for a file entry, defaulting to 0."""
        return int(entry.get("lines", 0))

    @staticmethod
    def _is_test_or_init(path: str) -> bool:
        """Return ``True`` for test files and ``__init__.py`` files."""
        p = Path(path)
        name = p.name
        return name == "__init__.py" or name.startswith("test_") or name.endswith("_test.py")

    # ------------------------------------------------------------------
    # Analysis passes
    # ------------------------------------------------------------------

    def _analyze_large_files(self) -> Optional[AnalysisInsight]:
        """Flag files whose line count is > 2.5× the project average.

        These are refactoring candidates -- they tend to accumulate too many
        responsibilities over time.
        """
        files = self._report.get("files", [])
        if not files:
            return None

        line_counts = [self._file_entry_lines(f) for f in files]
        avg = sum(line_counts) / len(line_counts)
        threshold = avg * self.LARGE_FILE_MULTIPLIER

        large = [
            f["path"]
            for f in files
            if self._file_entry_lines(f) > threshold
        ]

        if not large:
            return None

        return AnalysisInsight(
            title="Large files detected",
            description=(
                f"{len(large)} file(s) are significantly larger than the project average "
                f"({avg:.0f} lines). Consider splitting them into smaller modules."
            ),
            severity="info",
            affected_files=large,
        )

    def _analyze_circular_imports(self) -> Optional[AnalysisInsight]:
        """Report all circular dependency chains found during discovery.

        Circular imports are *not* safe to delete automatically -- they are
        reported so the developer can resolve them manually.
        """
        chains: List[List[str]] = self._report.get("circular_imports", [])
        if not chains:
            return None

        # Flatten each chain to a representative "root" file for the list
        affected: List[str] = []
        for chain in chains:
            for node in chain:
                if node not in affected:
                    affected.append(node)

        return AnalysisInsight(
            title="Circular imports found",
            description=(
                f"{len(chains)} circular dependency chain(s) detected. "
                "These must be resolved manually -- do not delete files to fix them."
            ),
            severity="warning",
            affected_files=affected,
        )

    def _analyze_isolated_files(self) -> Optional[AnalysisInsight]:
        """Find files with fewer than 2 imports *and* fewer than 2 exports.

        Such files may be orphaned utilities or dead code.  Phase 2 will
        perform a deeper reachability check before recommending deletion.
        ``__init__.py`` and test files are excluded from this check.
        """
        files = self._report.get("files", [])
        isolated = [
            f["path"]
            for f in files
            if (
                not self._is_test_or_init(f.get("path", ""))
                and int(f.get("imports_count", 0)) < self.ISOLATION_THRESHOLD
                and int(f.get("exports_count", 0)) < self.ISOLATION_THRESHOLD
            )
        ]

        if not isolated:
            return None

        return AnalysisInsight(
            title="Potentially isolated files",
            description=(
                f"{len(isolated)} file(s) have fewer than {self.ISOLATION_THRESHOLD} imports "
                f"and fewer than {self.ISOLATION_THRESHOLD} exports. "
                "They may be orphaned -- Phase 2 will verify reachability."
            ),
            severity="info",
            affected_files=isolated,
        )

    def _analyze_complexity(self) -> Optional[AnalysisInsight]:
        """Flag files whose complexity score exceeds the threshold (default 30).

        High complexity scores indicate files that are doing too much and are
        prime candidates for decomposition.
        """
        files = self._report.get("files", [])
        complex_files = [
            f["path"]
            for f in files
            if float(f.get("complexity_score", 0)) > self.COMPLEXITY_THRESHOLD
        ]

        if not complex_files:
            return None

        return AnalysisInsight(
            title="High-complexity files",
            description=(
                f"{len(complex_files)} file(s) exceed a complexity score of "
                f"{self.COMPLEXITY_THRESHOLD:.0f}. Consider breaking them into "
                "smaller, focused modules."
            ),
            severity="info",
            affected_files=complex_files,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> List[AnalysisInsight]:
        """Run all analysis passes and return the list of insights.

        Loads the report on first call; subsequent calls re-use the cached
        report but re-run all passes (useful if you mutate thresholds between
        calls).

        Returns
        -------
        List[AnalysisInsight]
            Every non-``None`` insight produced by the analysis passes,
            ordered: large files -> circular imports -> isolated files ->
            complexity.
        """
        if not self._report:
            self._report = self._load_report()

        passes = [
            self._analyze_large_files,
            self._analyze_circular_imports,
            self._analyze_isolated_files,
            self._analyze_complexity,
        ]

        self._insights = [result for fn in passes if (result := fn()) is not None]
        return self._insights

    def print_summary(self) -> None:
        """Print a formatted summary to stdout.

        Calls :meth:`analyze` automatically if it has not been called yet.
        """
        if not self._report:
            self._report = self._load_report()
        if not self._insights:
            self.analyze()

        meta: Dict[str, Any] = self._report.get("metadata", {})
        files: List[Dict[str, Any]] = self._report.get("files", [])

        # ── Derived statistics ──────────────────────────────────────────────
        total_files = meta.get("total_files", len(files))
        total_lines = meta.get("total_lines") or sum(
            self._file_entry_lines(f) for f in files
        )
        avg_lines = int(total_lines / total_files) if total_files else 0

        # Count by language
        type_counts: Dict[str, int] = {}
        for f in files:
            t = f.get("file_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        # Largest file
        largest = max(files, key=self._file_entry_lines, default=None)
        largest_label = (
            f"{largest['path']} ({self._file_entry_lines(largest):,} lines)"
            if largest
            else "N/A"
        )

        width = 70
        sep = "=" * width

        print(sep)
        print("PHASE 1 DISCOVERY - SUMMARY")
        print()
        print("[*] Project Statistics:")

        def _row(label: str, value: Any) -> None:
            dots = "." * (width - len(label) - len(str(value)) - 2)
            print(f"  {label}{dots} {value}")

        _row("total_files", f"{total_files:,}")
        for lang in ("python", "javascript", "typescript", "json"):
            count = type_counts.get(lang, 0)
            if count:
                _row(f"{lang}_files", f"{count:,}")
        _row("total_lines", f"{total_lines:,}")
        _row("avg_lines_per_file", f"{avg_lines:,}")
        _row("largest_file", largest_label)

        print()
        print("[?] Key Findings:")

        if not self._insights:
            print("  [OK] No issues found.")
        else:
            for insight in self._insights:
                print(f"  {insight.icon()} {insight.title}")
                print(f"     {insight.description}")
                preview = insight.affected_files[:5]
                remainder = len(insight.affected_files) - len(preview)
                files_str = ", ".join(preview)
                if remainder > 0:
                    files_str += f" … and {remainder} more"
                print(f"     Files: {files_str}")
                print()

        print(sep)

    def export_csv(self, output_path: str) -> None:
        """Write per-file metrics to a CSV file.

        Columns: ``path``, ``file_type``, ``lines``, ``imports_count``,
        ``exports_count``, ``size_bytes``, ``complexity``.

        Parameters
        ----------
        output_path:
            Destination CSV file path.  Parent directories must exist.
        """
        if not self._report:
            self._report = self._load_report()

        dest = Path(output_path)
        files: List[Dict[str, Any]] = self._report.get("files", [])

        fieldnames = [
            "path",
            "file_type",
            "lines",
            "imports_count",
            "exports_count",
            "size_bytes",
            "complexity",
        ]

        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for entry in files:
                writer.writerow({
                    "path":          entry.get("path", ""),
                    "file_type":     entry.get("file_type", "unknown"),
                    "lines":         entry.get("lines", 0),
                    "imports_count": entry.get("imports_count", 0),
                    "exports_count": entry.get("exports_count", 0),
                    "size_bytes":    entry.get("size_bytes", 0),
                    "complexity":    entry.get("complexity_score", 0),
                })

        print(f"CSV exported -> {dest} ({len(files)} rows)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase1_analyzer",
        description="Analyze a Phase 1 Discovery JSON report.",
    )
    parser.add_argument(
        "report",
        metavar="REPORT",
        help="Path to the phase1_report.json file.",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        default=None,
        help="Optional: export per-file metrics to this CSV path.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        analyzer = ReportAnalyzer(args.report)
        analyzer.analyze()
        analyzer.print_summary()
        if args.csv:
            analyzer.export_csv(args.csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
