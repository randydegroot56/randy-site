"""
agents/code_auditor/cli.py
===========================
Main CLI entry point for the Code Auditor Agent.

Usage::

    # Discover
    python -m agents.code_auditor.cli discover --project . --verbose
    python -m agents.code_auditor.cli discover --project /repo --output report.json --config ai-command-center

    # Analyze (Phase 1 insights)
    python -m agents.code_auditor.cli analyze report.json
    python -m agents.code_auditor.cli analyze report.json --csv files.csv

    # Detect (Phase 2 unused code)
    python -m agents.code_auditor.cli detect --report audit_report.json
    python -m agents.code_auditor.cli detect --report audit_report.json --output phase2.json --verbose

    # Verify (Phase 3 safety verification)
    python -m agents.code_auditor.cli verify --report phase2_findings.json
    python -m agents.code_auditor.cli verify --report phase2_findings.json --phase1 audit_report.json --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Support both `python cli.py` (direct) and `python -m agents.code_auditor.cli` (package).
if __name__ == "__main__" and __package__ is None:
    # Running as a plain script: add the repo root to sys.path so that
    # `agents.code_auditor.*` imports resolve correctly.
    _repo_root = Path(__file__).resolve().parent.parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from agents.code_auditor.core.config import get_config
from agents.code_auditor.core.phase1_analyzer import ReportAnalyzer
from agents.code_auditor.core.phase1_discovery import Phase1Discovery


# ---------------------------------------------------------------------------
# discover subcommand
# ---------------------------------------------------------------------------


def cmd_discover(args: argparse.Namespace) -> int:
    """Run Phase 1 discovery on a project directory."""
    project = Path(args.project).resolve()
    output  = Path(args.output)

    if not project.exists():
        print(f"Error: project path does not exist: {project}", file=sys.stderr)
        return 1
    if not project.is_dir():
        print(f"Error: project path is not a directory: {project}", file=sys.stderr)
        return 1

    # Load config (warns and falls back to default on unknown names)
    config = get_config(args.config)
    if args.verbose:
        print(f"Config profile : {config!r}")

    width = 72
    print("=" * width)
    print(f"[*] Scanning project: {project}")
    print(f"    Config          : {args.config}")
    print(f"    Output          : {output}")
    print("=" * width)

    t0 = time.perf_counter()

    print("-> Phase 1a: File Tree Scan")
    print("-> Phase 1b: Dependency Graph")
    print("-> Phase 1c: Circular Import Detection")
    print("-> Compiling statistics...")

    try:
        registry = asyncio.run(
            Phase1Discovery(str(project), verbose=args.verbose).scan_project()
        )
    except Exception as exc:
        print(f"Error: scan failed: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - t0

    # ── Persist report ────────────────────────────────────────────────────
    try:
        output.write_text(
            json.dumps(registry.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"Error: could not write report to {output}: {exc}", file=sys.stderr)
        return 1

    # ── Summary ───────────────────────────────────────────────────────────
    stats = registry.statistics
    total = stats.get("total_files", 0)

    print(f"[OK] Scan complete: {total:,} files scanned in {elapsed:.1f}s")
    print(f"[>] Report saved to: {output.resolve()}")
    print()

    _print_stats_table(stats, registry, width)

    if registry.circular_imports:
        print()
        print(f"[!] {len(registry.circular_imports)} circular import chain(s) found:")
        for chain in registry.circular_imports:
            print(f"    {' -> '.join(chain)}")

    if registry.external_dependencies:
        deps_preview = ", ".join(sorted(registry.external_dependencies)[:8])
        remainder = len(registry.external_dependencies) - 8
        suffix = f" ... and {remainder} more" if remainder > 0 else ""
        print()
        print(f"[i] External dependencies ({len(registry.external_dependencies)}): {deps_preview}{suffix}")

    print("=" * width)
    return 0


def _print_stats_table(stats: dict, registry, width: int) -> None:
    """Print the dot-padded statistics table."""
    print("=" * width)
    print("SUMMARY")

    def row(label: str, value) -> None:
        dots = "." * (width - len(label) - len(str(value)) - 2)
        print(f"  {label}{dots} {value}")

    row("total_files",        f"{stats.get('total_files', 0):,}")

    by_lang: dict = stats.get("by_language", {})
    for lang in ("python", "javascript", "typescript", "json"):
        count = by_lang.get(lang, 0)
        if count:
            row(f"{lang}_files", f"{count:,}")

    row("total_lines",        f"{stats.get('total_lines', 0):,}")
    row("avg_lines_per_file", f"{stats.get('avg_lines_per_file', 0):,}")

    largest = stats.get("largest_file")
    if largest:
        row("largest_file", largest)

    row("circular_imports",   str(len(registry.circular_imports)))
    row("ext_dependencies",   str(len(registry.external_dependencies)))
    row("scan_errors",        str(stats.get("scan_errors", 0)))


# ---------------------------------------------------------------------------
# analyze subcommand
# ---------------------------------------------------------------------------


def cmd_analyze(args: argparse.Namespace) -> int:
    """Load a Phase 1 JSON report and surface actionable insights."""
    report_path = Path(args.report)

    if not report_path.exists():
        print(f"Error: report file not found: {report_path}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()

    try:
        analyzer = ReportAnalyzer(str(report_path))
        insights = analyzer.analyze()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - t0

    analyzer.print_summary()
    print(f"[i] Analysis completed in {elapsed:.2f}s -- {len(insights)} insight(s) found.")

    if args.csv:
        try:
            analyzer.export_csv(args.csv)
        except OSError as exc:
            print(f"Error: could not write CSV to {args.csv}: {exc}", file=sys.stderr)
            return 1

    return 0


# ---------------------------------------------------------------------------
# detect subcommand (Phase 2)
# ---------------------------------------------------------------------------


def cmd_detect(args: argparse.Namespace) -> int:
    """Run all Phase 2 unused-code detectors against a Phase 1 JSON report."""
    # ── Import Phase 2 modules ────────────────────────────────────────────
    try:
        from agents.code_auditor.core.phase2_detection import (
            CircularDependencyAnalyzer,
            OrphanFileFinder,
            UnusedExportFinder,
            UnusedImportFinder,
        )
        from agents.code_auditor.core.phase2_analyzer import (
            Phase2ReportGenerator,
            TestCoverageVerifier,
        )
    except ImportError as exc:
        print("Error: Phase 2 modules not found.", file=sys.stderr)
        print(file=sys.stderr)
        print("Phase 2 has not been built yet. To set it up:", file=sys.stderr)
        print("  1. Create: agents/code_auditor/core/phase2_detection.py", file=sys.stderr)
        print("  2. Create: agents/code_auditor/core/phase2_analyzer.py", file=sys.stderr)
        print(f"\nImport error: {exc}", file=sys.stderr)
        return 1

    report_path = Path(args.report)
    output_path = Path(args.output)

    # ── Validate input ────────────────────────────────────────────────────
    if not report_path.exists():
        print(f"Error: Phase 1 report not found: {report_path}", file=sys.stderr)
        print(file=sys.stderr)
        print("Run Phase 1 discovery first:", file=sys.stderr)
        print(f"  python cli.py discover --project . --output {report_path}", file=sys.stderr)
        return 1

    # ── Load Phase 1 report ───────────────────────────────────────────────
    print(f"Loading Phase 1 report: {report_path}")
    try:
        phase1_report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {report_path}: {exc}", file=sys.stderr)
        return 1

    file_count = len(phase1_report.get("files", []))
    print(f"  {file_count} files loaded from report.")
    print()

    width = 68
    print("=" * width)
    print("Running Phase 2 Detection Analysis...")
    print("=" * width)

    t0 = time.perf_counter()
    all_findings: list = []

    try:
        # ── Phase 2A: Unused exports ──────────────────────────────────────
        _step("Phase 2A: Unused export detection", args.verbose)
        f1 = UnusedExportFinder(phase1_report, verbose=args.verbose).find_unused_exports()
        all_findings.extend(f1)
        _step_result(len(f1), "unused export(s)", args.verbose)

        # ── Phase 2B: Orphan files ────────────────────────────────────────
        _step("Phase 2B: Orphan file detection", args.verbose)
        f2 = OrphanFileFinder(phase1_report, verbose=args.verbose).find_orphan_files()
        all_findings.extend(f2)
        _step_result(len(f2), "orphan file(s)", args.verbose)

        # ── Phase 2C: Unused imports ──────────────────────────────────────
        _step("Phase 2C: Unused import detection", args.verbose)
        f3 = UnusedImportFinder(phase1_report, verbose=args.verbose).find_unused_imports()
        all_findings.extend(f3)
        _step_result(len(f3), "unused import(s)", args.verbose)

        # ── Phase 2D: Circular dependencies ──────────────────────────────
        _step("Phase 2D: Circular dependency analysis", args.verbose)
        f4 = CircularDependencyAnalyzer(phase1_report, verbose=args.verbose).analyze_circular_deps()
        all_findings.extend(f4)
        _step_result(len(f4), "circular dependency chain(s)", args.verbose)

        # ── Phase 2E: Test coverage adjustment ───────────────────────────
        _step("Phase 2E: Test coverage adjustment", args.verbose)
        all_findings = TestCoverageVerifier(
            phase1_report, all_findings, verbose=args.verbose
        ).adjust_findings_for_tests()
        covered = sum(
            1 for f in all_findings
            if f.get("evidence", {}).get("test_coverage")
        )
        _step_result(covered, "finding(s) adjusted for test coverage", args.verbose)

        # ── Phase 2F: Report generation ───────────────────────────────────
        _step("Phase 2F: Generating final report", args.verbose)
        generator = Phase2ReportGenerator(all_findings, phase1_report)
        generator.generate_report()
        _step_result(len(all_findings), "total finding(s)", args.verbose)

    except Exception as exc:
        print(f"\nError during Phase 2 detection: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    elapsed = time.perf_counter() - t0
    print()
    print(f"[OK] Detection complete in {elapsed:.1f}s")
    print()

    # ── Console summary ───────────────────────────────────────────────────
    generator.print_summary()

    # ── Export JSON ───────────────────────────────────────────────────────
    try:
        generator.export_to_json(str(output_path))
    except OSError as exc:
        print(f"Error: could not write output to {output_path}: {exc}", file=sys.stderr)
        return 1

    print()
    print("Next steps:")
    print("  1. Review findings in the JSON report.")
    print("  2. Run Phase 3 verification when ready.")
    print("  3. Run Phase 5 to execute safe removals with git rollback.")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Execute Phase 3 safety verification."""
    # ── Import Phase 3 modules ────────────────────────────────────────────
    try:
        from agents.code_auditor.core.phase3_verification import (
            TestDependencyChecker,
            APIEndpointChecker,
            ConfigurationChecker,
            DatabaseMigrationChecker,
            DynamicImportDetector,
        )
        from agents.code_auditor.core.phase3_analyzer import Phase3SafetyAnalyzer
    except ImportError as exc:
        print("❌ Phase 3 modules not found")
        print()
        print("Phase 3 is not yet implemented.")
        print("To build Phase 3, follow these steps:")
        print()
        print("1. Read: PHASE_3_COMPLETE_GUIDE.md")
        print("2. Create: agents/code_auditor/core/phase3_verification.py")
        print("3. Create: agents/code_auditor/core/phase3_analyzer.py")
        print("4. Copy prompts from PHASE_3_COMPLETE_GUIDE.md and paste in Claude Code")
        print("5. Try again: python cli.py verify --report phase2_findings.json")
        print()
        print(f"Error details: {exc}")
        return 1

    phase2_path = Path(args.report)
    phase1_path = Path(args.phase1)
    output_path = Path(args.output)

    # ── Validate input files ──────────────────────────────────────────────
    if not phase2_path.exists():
        print(f"❌ Phase 2 report not found: {phase2_path}", file=sys.stderr)
        print(file=sys.stderr)
        print("Run Phase 2 first:", file=sys.stderr)
        print(f"  python agents/code_auditor/cli.py detect --report audit_report.json", file=sys.stderr)
        return 1

    if not phase1_path.exists():
        print(f"❌ Phase 1 report not found: {phase1_path}", file=sys.stderr)
        print(file=sys.stderr)
        print("Run Phase 1 first:", file=sys.stderr)
        print(f"  python agents/code_auditor/cli.py discover --project . --verbose", file=sys.stderr)
        return 1

    # ── Load reports ──────────────────────────────────────────────────────
    print(f"📖 Loading Phase 1 report: {phase1_path}")
    print(f"📖 Loading Phase 2 report: {phase2_path}")

    try:
        phase1_report = json.loads(phase1_path.read_text(encoding="utf-8"))
        phase2_report = json.loads(phase2_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ Invalid JSON in report file: {exc}", file=sys.stderr)
        return 1

    print("🛡️  Running Phase 3 Safety Verification...")
    print()

    t0 = time.perf_counter()

    try:
        phase2_findings = phase2_report.get("findings", [])

        # Each checker is chained: it receives the adjusted findings from the
        # previous step so that risk/confidence adjustments accumulate and each
        # finding's ``evidence`` dict grows one key per checker.

        # ── Phase 3A: Test dependency check ───────────────────────────────
        _step("Phase 3A: Checking test dependencies", args.verbose)
        checker1  = TestDependencyChecker(phase1_report, phase2_findings, verbose=args.verbose)
        adjusted1 = checker1.get_adjusted_findings()
        _step_result(
            sum(1 for f in adjusted1 if f.get("evidence", {}).get("test_dependency_check", {}).get("has_tests")),
            "finding(s) with test coverage",
            args.verbose,
        )

        # ── Phase 3B: API endpoint safety ─────────────────────────────────
        _step("Phase 3B: Checking API endpoint safety", args.verbose)
        checker2  = APIEndpointChecker(phase1_report, adjusted1, verbose=args.verbose)
        adjusted2 = checker2.get_adjusted_findings()
        _step_result(
            sum(1 for f in adjusted2 if f.get("evidence", {}).get("api_endpoint_check", {}).get("is_api_endpoint")),
            "API endpoint(s) found",
            args.verbose,
        )

        # ── Phase 3C: Configuration usage ─────────────────────────────────
        _step("Phase 3C: Checking configuration usage", args.verbose)
        checker3  = ConfigurationChecker(phase1_report, adjusted2, verbose=args.verbose)
        adjusted3 = checker3.get_adjusted_findings()
        _step_result(
            sum(1 for f in adjusted3 if f.get("evidence", {}).get("configuration_check", {}).get("is_configuration")),
            "configuration item(s) found",
            args.verbose,
        )

        # ── Phase 3D: Database migration safety ───────────────────────────
        _step("Phase 3D: Checking database safety", args.verbose)
        checker4  = DatabaseMigrationChecker(phase1_report, adjusted3, verbose=args.verbose)
        adjusted4 = checker4.check_database_safety()
        _step_result(
            sum(1 for f in adjusted4 if f.get("evidence", {}).get("database_check", {}).get("is_database_critical")),
            "database-related item(s) found (CRITICAL)",
            args.verbose,
        )

        # ── Phase 3E: Dynamic import detection ────────────────────────────
        _step("Phase 3E: Detecting dynamic imports", args.verbose)
        checker5  = DynamicImportDetector(phase1_report, adjusted4, verbose=args.verbose)
        adjusted5 = checker5.detect_dynamic_imports()
        _step_result(
            sum(1 for f in adjusted5 if f.get("evidence", {}).get("dynamic_check", {}).get("is_dynamically_loaded")),
            "potentially dynamic import(s) found",
            args.verbose,
        )

        # ── Phase 3F: Final safety assessment ─────────────────────────────
        # Pass the fully-chained adjusted findings (not the raw checker results)
        _step("Phase 3F: Calculating final safety assessment", args.verbose)
        analyzer = Phase3SafetyAnalyzer(phase2_findings, adjusted5, verbose=args.verbose)
        analyzer.analyze_safety()
        _step_result(len(adjusted5), "finding(s) assessed", args.verbose)

    except Exception as exc:
        print(f"\n❌ Error during Phase 3 verification: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    elapsed = time.perf_counter() - t0
    print()
    print(f"[OK] Verification complete in {elapsed:.1f}s")
    print()

    analyzer.print_summary()

    # ── Export JSON ───────────────────────────────────────────────────────
    try:
        analyzer.export_to_json(str(output_path))
    except OSError as exc:
        print(f"Error: could not write output to {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"\n📄 Verified findings exported to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Review the safety assessment in the JSON report")
    print("  2. Understand why items are CRITICAL/HIGH/MEDIUM/LOW risk")
    print("  3. Plan removals based on scenarios")
    print("  4. Run Phase 5 when ready to execute safe removals")
    return 0


def _step(label: str, verbose: bool) -> None:
    """Print a detection-step progress line."""
    if verbose:
        print(f"-> {label}...")


def _step_result(count: int, label: str, verbose: bool) -> None:
    """Print the result count for a detection step."""
    if verbose:
        print(f"   Found {count} {label}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-auditor",
        description="Code Auditor Agent -- discover and analyze project dependencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Phase 1: scan the current directory
  python -m agents.code_auditor.cli discover --project . --verbose

  # Phase 1: scan with a project-specific config
  python -m agents.code_auditor.cli discover --project /repo --config ai-command-center --output report.json

  # Phase 1: analyze a saved report (insights + CSV)
  python -m agents.code_auditor.cli analyze report.json --csv files.csv

  # Phase 2: detect unused code
  python -m agents.code_auditor.cli detect --report audit_report.json
  python -m agents.code_auditor.cli detect --report audit_report.json --output phase2.json --verbose

  # Phase 3: verify safety of findings
  python -m agents.code_auditor.cli verify --report phase2_findings.json
  python -m agents.code_auditor.cli verify --report phase2_findings.json --phase1 audit_report.json --verbose
""",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
        metavar="SUBCOMMAND",
    )
    subparsers.required = True

    # ── discover ──────────────────────────────────────────────────────────
    discover_parser = subparsers.add_parser(
        "discover",
        help="Scan a project and produce a Phase 1 JSON report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example: python -m agents.code_auditor.cli discover --project . --verbose",
    )
    discover_parser.add_argument(
        "--project",
        metavar="PATH",
        default=".",
        help="Root directory of the project to scan (default: current directory).",
    )
    discover_parser.add_argument(
        "--output",
        metavar="PATH",
        default="audit_report.json",
        help="Destination JSON report file (default: audit_report.json).",
    )
    discover_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-file progress during the scan.",
    )
    discover_parser.add_argument(
        "--config",
        metavar="PROFILE",
        default="default",
        help=(
            "Config profile to use. Built-in: default, ai-command-center, nextjs, python "
            "(default: default)."
        ),
    )
    discover_parser.set_defaults(func=cmd_discover)

    # ── analyze ───────────────────────────────────────────────────────────
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a Phase 1 JSON report and surface insights.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example: python -m agents.code_auditor.cli analyze report.json --csv files.csv",
    )
    analyze_parser.add_argument(
        "report",
        metavar="REPORT",
        help="Path to the phase1 JSON report produced by the 'discover' subcommand.",
    )
    analyze_parser.add_argument(
        "--csv",
        metavar="PATH",
        default=None,
        help="Optional: export per-file metrics to this CSV file.",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    # ── detect (Phase 2) ──────────────────────────────────────────────────
    detect_parser = subparsers.add_parser(
        "detect",
        help="Detect unused exports, orphan files, and circular deps (Phase 2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example: python -m agents.code_auditor.cli detect "
            "--report audit_report.json --verbose"
        ),
    )
    detect_parser.add_argument(
        "--report",
        metavar="PATH",
        required=True,
        help="Path to the Phase 1 JSON report produced by 'discover'.",
    )
    detect_parser.add_argument(
        "--output",
        metavar="PATH",
        default="phase2_findings.json",
        help="Destination JSON file for Phase 2 findings (default: phase2_findings.json).",
    )
    detect_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-step progress during detection.",
    )
    detect_parser.set_defaults(func=cmd_detect)

    # ── verify (Phase 3) ──────────────────────────────────────────────────
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify safety of findings (Phase 3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example: python -m agents.code_auditor.cli verify "
            "--report phase2_findings.json --verbose"
        ),
    )
    verify_parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Path to Phase 2 findings JSON (e.g., phase2_findings.json).",
    )
    verify_parser.add_argument(
        "--phase1",
        type=str,
        default="audit_report.json",
        help="Path to Phase 1 report JSON (default: audit_report.json).",
    )
    verify_parser.add_argument(
        "--output",
        type=str,
        default="phase3_verified.json",
        help="Output file for Phase 3 verification (default: phase3_verified.json).",
    )
    verify_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output.",
    )
    verify_parser.set_defaults(func=cmd_verify)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
