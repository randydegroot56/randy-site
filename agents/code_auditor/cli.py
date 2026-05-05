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

# Force UTF-8 on Windows consoles that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# discover subcommand (Phase 1)
# ---------------------------------------------------------------------------


def cmd_discover(args: argparse.Namespace) -> int:
    """Run Phase 1 discovery: scan files, build dependency map, write JSON report."""
    discovery = Phase1Discovery(args.project, verbose=args.verbose)
    try:
        registry = asyncio.run(discovery.scan_project())
    except Exception as exc:
        print(f"Error during scan: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.write_text(
        json.dumps(registry.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Report written -> {output.resolve()} ({len(registry.files)} files)")

    stats = registry.statistics
    _print_stats_table(stats, registry, width=60)
    return 0


# ---------------------------------------------------------------------------
# report subcommand (Phase 4)
# ---------------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    """Generate an audit report: JSON summary, terminal dashboard, HTML, CSV."""
    try:
        from agents.code_auditor.core.phase4_reporting import (
            ReportGenerator, DashboardGenerator, HTMLExporter, CSVExporter,
        )
        from agents.code_auditor.core.phase4_analyzer import RecommendationGenerator
    except ImportError as exc:
        print(f"Error: Phase 4 modules not found: {exc}", file=sys.stderr)
        return 1

    phase3_path = Path(args.phase3)
    phase2_path = Path(args.phase2)

    if not phase3_path.exists():
        print(f"Error: Phase 3 file not found: {phase3_path}", file=sys.stderr)
        print("Run Phase 3 first:", file=sys.stderr)
        print("  python agents/code_auditor/cli.py verify --report phase2_findings.json",
              file=sys.stderr)
        return 1

    if not phase2_path.exists():
        print(f"Error: Phase 2 file not found: {phase2_path}", file=sys.stderr)
        print("Run Phase 2 first:", file=sys.stderr)
        print("  python agents/code_auditor/cli.py detect --report audit_report.json",
              file=sys.stderr)
        return 1

    # ── Load inputs ───────────────────────────────────────────────────────
    try:
        phase3_data = json.loads(phase3_path.read_text(encoding="utf-8"))
        phase2_data = json.loads(phase2_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    phase1_data: dict = {}
    phase1_path = Path(args.phase1)
    if phase1_path.exists():
        try:
            phase1_data = json.loads(phase1_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: could not parse {phase1_path} — metadata will be limited.",
                  file=sys.stderr)

    history: list = []
    if args.history:
        history_path = Path(args.history)
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
                if not isinstance(history, list):
                    history = []
            except json.JSONDecodeError:
                pass

    # ── Build report data ─────────────────────────────────────────────────
    # Merge raw findings into report_data for pattern analysis
    raw_findings = phase2_data.get("findings", [])

    gen         = ReportGenerator(phase1_data, phase2_data, phase3_data, history)
    report_data = gen.generate_json_report()
    report_data["_findings_raw"] = raw_findings

    # ── JSON output ───────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Report saved -> {output_path}")

    # ── HTML export ───────────────────────────────────────────────────────
    if args.html:
        html_path = Path(args.html)
        html_path.write_text(
            HTMLExporter(report_data).generate_html(), encoding="utf-8"
        )
        print(f"HTML  saved -> {html_path}")

    # ── CSV export ────────────────────────────────────────────────────────
    if args.csv:
        csv_path = Path(args.csv)
        csv_path.write_text(
            CSVExporter(report_data).generate_csv(), encoding="utf-8", newline=""
        )
        print(f"CSV   saved -> {csv_path}")

    # ── Terminal dashboard ────────────────────────────────────────────────
    if not args.no_dashboard:
        dash = DashboardGenerator(report_data).generate_dashboard()
        # Force UTF-8 on Windows consoles that default to cp1252
        try:
            print(dash)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((dash + "\n").encode("utf-8", errors="replace"))

    # ── Recommendations ───────────────────────────────────────────────────
    if not args.no_recommendations:
        recs = RecommendationGenerator(report_data).generate_recommendations()
        recs_str = "\n" + json.dumps(recs, indent=2, ensure_ascii=True)
        try:
            print(recs_str)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((recs_str + "\n").encode("utf-8", errors="replace"))

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


def cmd_execute(args: argparse.Namespace) -> int:
    """Execute Phase 5 safe code removal."""
    # ── Import Phase 5 modules ────────────────────────────────────────────
    try:
        from agents.code_auditor.core.phase5_executor import (
            DryRunExecutor,
            BatchRemover,
            ImportCleaner,
            TestVerifier,
            GitCommitter,
        )
        from agents.code_auditor.core.phase5_analyzer import Phase5BatchAnalyzer
    except ImportError as exc:
        print("Error: Phase 5 modules not found.", file=sys.stderr)
        print(f"\nImport error: {exc}", file=sys.stderr)
        return 1

    report_path  = Path(args.report)
    phase1_path  = Path(args.phase1)
    phase2_path  = Path(args.phase2)
    output_path  = Path(args.output)
    project_root = Path(args.project).resolve()

    # ── Validate inputs ───────────────────────────────────────────────────
    if not report_path.exists():
        print(f"Error: Phase 3 report not found: {report_path}", file=sys.stderr)
        print("Run Phase 3 verification first:", file=sys.stderr)
        print(f"  python agents/code_auditor/cli.py verify --report phase2_findings.json",
              file=sys.stderr)
        return 1

    if not phase2_path.exists():
        print(f"Error: Phase 2 report not found: {phase2_path}", file=sys.stderr)
        print("Phase 5 needs Phase 2 to resolve item names and file paths.", file=sys.stderr)
        print("Run Phase 2 first:", file=sys.stderr)
        print(f"  python agents/code_auditor/cli.py detect --report audit_report.json",
              file=sys.stderr)
        return 1

    if not project_root.is_dir():
        print(f"Error: project root is not a directory: {project_root}", file=sys.stderr)
        return 1

    # ── Load reports ──────────────────────────────────────────────────────
    try:
        phase3_raw   = json.loads(report_path.read_text(encoding="utf-8"))
        phase2_report = json.loads(phase2_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in report: {exc}", file=sys.stderr)
        return 1

    phase1_report: dict = {}
    if phase1_path.exists():
        try:
            phase1_report = json.loads(phase1_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: could not parse {phase1_path} -- impact analysis will be limited.")

    p2_count = len(phase2_report.get("findings", []))
    print(f"  Phase 3 : {report_path}")
    print(f"  Phase 2 : {phase2_path} ({p2_count} findings loaded)")

    # ── Normalise Phase 3 -> all_checks ───────────────────────────────────
    p2_map      = {f.get("id", ""): f for f in phase2_report.get("findings", []) if f.get("id")}
    all_checks  = _normalise_phase3(phase3_raw, p2_map)
    phase3_verified = {**phase3_raw, "all_checks": all_checks}

    # ── Resolve items to process ──────────────────────────────────────────
    if args.items:
        items_to_remove = list(args.items)
    else:
        # Auto-select top 3 LOW-risk findings by confidence
        candidates = sorted(
            [c for c in all_checks if c.get("risk_level") == "LOW"],
            key=lambda c: c.get("confidence", 0.0),
            reverse=True,
        )[:3]
        items_to_remove = [c["id"] for c in candidates]

    if not items_to_remove:
        print("No LOW-risk items found. All done, or review MEDIUM/HIGH items manually.")
        return 0

    width = 68
    print("=" * width)
    print("[Phase 5] Removal Pipeline")
    print(f"  Project  : {project_root}")
    print(f"  Report   : {report_path}")
    print(f"  Items    : {', '.join(items_to_remove)}")
    print(f"  Dry run  : {args.dry_run}")
    print("=" * width)

    t0 = time.perf_counter()

    # ── STAP 1: Dry Run ───────────────────────────────────────────────────
    print("-> STAP 1: Dry run impact analysis...")
    try:
        # verbose=False here: the CLI prints its own formatted summary below
        dry_executor = DryRunExecutor(
            phase3_verified, phase1_report, phase2_report,
            verbose=False,
        )
        dry_result = dry_executor.run_dry_run(items_to_remove)
    except Exception as exc:
        print(f"Error during dry run: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback; traceback.print_exc()
        return 1

    # Always print the dry-run summary table
    w60 = "=" * 60
    print(w60)
    print("DRY RUN SUMMARY")
    print(w60)
    print(f"Items analysed    : {', '.join(dry_result.items)}")
    print(f"Files to delete   : {len(dry_result.files_to_delete)}")
    print(f"Imports to remove : {len(dry_result.imports_to_remove)}")
    print(f"Lines affected    : {dry_result.lines_affected}")
    print(f"Tests affected    : {len(dry_result.tests_affected)}")
    print(f"Is safe           : {dry_result.is_safe}")
    print(f"Impact            : {dry_result.estimated_impact}")
    if dry_result.warnings:
        print("Warnings:")
        for w in dry_result.warnings:
            print(f"  - {w}")
    print(w60)
    print(f"   Found {dry_result.lines_affected} line(s) would be affected")

    if not dry_result.is_safe:
        print("\nDry run flagged safety issues -- aborting.", file=sys.stderr)
        return 1

    # Stop here in preview mode
    if args.dry_run:
        print()
        print("Dry run complete (no changes made).")
        print(f"\nRe-run without --dry-run to execute:")
        items_str = " ".join(items_to_remove)
        print(f"  python agents/code_auditor/cli.py execute "
              f"--report {args.report} --items {items_str}")
        return 0

    # ── STAP 2: Batch removal ─────────────────────────────────────────────
    print("-> STAP 2: Staged batch removal...")
    from datetime import date as _date
    batch_id = args.batch_id or f"{_date.today().isoformat()}-001"
    try:
        remover     = BatchRemover(str(project_root), phase2_report=phase2_report,
                                   verbose=args.verbose)
        batch_result = remover.remove_batch(items_to_remove, phase3_verified,
                                            batch_id=batch_id)
    except Exception as exc:
        print(f"Error during batch removal: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback; traceback.print_exc()
        return 1

    print(w60)
    print("BATCH REMOVAL SUMMARY")
    print(w60)
    print(f"Batch ID          : {batch_result['batch_id']}")
    print(f"Branch            : {batch_result['branch_created']}")
    print(f"Status            : {batch_result['status']}")
    items_done = batch_result.get("items_removed", [])
    print(f"Items removed     : {', '.join(items_done) or 'none'}")
    print(f"Files deleted     : {len(batch_result.get('files_deleted', []))}")
    print(f"Lines removed     : {batch_result.get('total_lines_removed', 0)}")
    next_step = "Review errors" if batch_result.get("errors") else "Run import cleanup"
    print(f"Next step         : {next_step}")
    if batch_result.get("errors"):
        print("Errors:")
        for e in batch_result["errors"]:
            print(f"  - {e}")
    print(w60)
    print(f"   Found {batch_result.get('total_lines_removed', 0)} line(s) removed")

    if batch_result["status"] == "failed":
        print("Error: batch removal failed entirely.", file=sys.stderr)
        return 1

    # ── STAP 3: Import cleanup ────────────────────────────────────────────
    print("-> STAP 3: Import cleanup...")
    finding_map  = {c["id"]: c for c in all_checks}
    deleted_names = [
        finding_map[fid]["name"]
        for fid in items_done
        if fid in finding_map and finding_map[fid].get("name")
    ]
    try:
        cleaner      = ImportCleaner(str(project_root), verbose=args.verbose)
        import_result = cleaner.cleanup_imports(deleted_names)
    except Exception as exc:
        print(f"Warning: import cleanup failed: {exc}", file=sys.stderr)
        import_result = {"imports_removed": 0, "lines_fixed": 0,
                         "status": "error", "modified_files": []}

    print(f"   Found {import_result.get('imports_removed', 0)} import(s) cleaned")

    # ── STAP 4: Test verification ─────────────────────────────────────────
    print("-> STAP 4: Running tests...")
    try:
        verifier    = TestVerifier(str(project_root), verbose=args.verbose)
        test_result = verifier.run_tests()
        linter_result = verifier.run_linter() if args.linter else {
            "errors": 0, "warnings": 0, "status": "SKIPPED"
        }
    except Exception as exc:
        print(f"Error during test verification: {exc}", file=sys.stderr)
        return 1

    tests_ok    = test_result.get("safe_to_commit", False)
    test_counts = test_result.get("tests", {})

    print(w60)
    print("TEST VERIFICATION SUMMARY")
    print(w60)
    print(f"Total tests       : {test_counts.get('total', 0)}")
    print(f"Passed            : {test_counts.get('passed', 0)}")
    print(f"Failed            : {test_counts.get('failed', 0)}")
    print(f"Test status       : {test_counts.get('status', '?')}")
    print(f"Overall           : {test_result.get('overall_status', '?')}")
    print(f"Safe to commit    : {tests_ok}")
    if test_result.get("revert_recommendation"):
        print(f"\n*** {test_result['revert_recommendation']} ***")
    failures = test_counts.get("failures", [])
    if failures:
        print(f"\nFailed tests ({len(failures)}):")
        for f in failures:
            print(f"  FAILED {f}")
    print(w60)

    if not tests_ok:
        print("\nTests FAILED -- commit blocked.", file=sys.stderr)
        print(test_result.get("revert_recommendation", ""), file=sys.stderr)
        return 1

    # ── STAP 5: Git commit ────────────────────────────────────────────────
    print("-> STAP 5: Creating atomic git commit...")
    try:
        committer    = GitCommitter(str(project_root), verbose=args.verbose)
        commit_result = committer.commit_removal(
            batch_id=batch_id,
            items_removed=items_done,
            tests_passed=tests_ok,
            batch_result=batch_result,
            import_result=import_result,
            phase3_findings=all_checks,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"   Found {commit_result.get('deletions', 0)} line(s) committed")

    elapsed = time.perf_counter() - t0
    print()
    print(f"[OK] Pipeline complete in {elapsed:.1f}s")
    print()

    # ── STAP 6: Batch report ──────────────────────────────────────────────
    combined = {
        "batch_id":       batch_id,
        "dry_run":        dry_result.to_dict(),
        "batch":          batch_result,
        "import_cleanup": import_result,
        "test_verify":    {**test_result, "linter": linter_result},
        "commit":         commit_result,
        "phase3_verified": phase3_verified,
    }
    analyzer = Phase5BatchAnalyzer(combined, verbose=True)
    analyzer.print_summary()

    try:
        analyzer.export_to_json(str(output_path))
        print(f"[>] Report saved to: {output_path.resolve()}")
    except OSError as exc:
        print(f"Warning: could not write report: {exc}", file=sys.stderr)

    print()
    print("Next steps:")
    print(f"  1. Review commit : git log -1 -p")
    print(f"  2. Rollback      : {commit_result.get('rollback_command', 'git revert <hash>')}")
    nxt = analyzer.generate_batch_report().get("next_batch_suggestion", {})
    if nxt.get("items"):
        nxt_ids = " ".join(nxt["items"])
        print(f"  3. Next batch    : python agents/code_auditor/cli.py execute "
              f"--report {args.report} --items {nxt_ids}")
    else:
        print("  3. No further safe items -- audit complete")

    return 0


def _normalise_phase3(phase3_raw: dict, p2_map: dict) -> list:
    """Convert Phase 3 ``assessments`` to the ``all_checks`` shape.

    Phase 3 exports use ``finding_id``, ``file_path``, ``final_risk``,
    ``final_confidence``; Phase 5 expects ``id``, ``file``, ``name``,
    ``risk_level``, ``confidence``.  Phase 2 map fills the gaps.
    """
    result = []
    for a in phase3_raw.get("assessments", []):
        fid = a.get("finding_id", "")
        p2  = p2_map.get(fid, {})
        result.append({
            "id":         fid,
            "file":       p2.get("file",  a.get("file_path", "")),
            # Phase 2 stores symbol name under "item" (e.g. "useTheme")
            "name":       p2.get("item")  or p2.get("name") or fid,
            "type":       a.get("type",   p2.get("type", "unknown")),
            "risk_level": a.get("final_risk",       "LOW"),
            "confidence": a.get("final_confidence", 0.0),
            "lines":      a.get("lines",  p2.get("lines", 0)),
            "evidence":   p2.get("evidence", {}),
        })
    return result


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

  # Phase 5: execute safe removals
  python -m agents.code_auditor.cli execute --report phase3_verified.json --dry-run
  python -m agents.code_auditor.cli execute --report phase3_verified.json --items U001 U002 U003
  python -m agents.code_auditor.cli execute --report phase3_verified.json --items U001 U002 --verbose
""",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="subcommand",
        metavar="SUBCOMMAND",
    )
    subparsers.required = True

    # ── discover (Phase 1) ────────────────────────────────────────────────
    discover_parser = subparsers.add_parser(
        "discover",
        help="Phase 1: scan project files and build a dependency map.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example: python -m agents.code_auditor.cli discover --project . --verbose",
    )
    discover_parser.add_argument(
        "--project",
        metavar="PATH",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    discover_parser.add_argument(
        "--output",
        metavar="PATH",
        default="audit_report.json",
        help="Path for the JSON report output (default: audit_report.json).",
    )
    discover_parser.add_argument(
        "--config",
        metavar="NAME",
        default=None,
        help="Named config profile to apply (e.g. ai-command-center).",
    )
    discover_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress messages during the scan.",
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

    # ── execute (Phase 5) ─────────────────────────────────────────────────
    execute_parser = subparsers.add_parser(
        "execute",
        help="Execute safe code removal via the Phase 5 pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # Preview without making changes\n"
            "  python -m agents.code_auditor.cli execute "
            "--report phase3_verified.json --dry-run\n\n"
            "  # Remove specific items\n"
            "  python -m agents.code_auditor.cli execute "
            "--report phase3_verified.json --items U001 U002 U003\n\n"
            "  # Auto-select top 3 LOW-risk items and remove them\n"
            "  python -m agents.code_auditor.cli execute "
            "--report phase3_verified.json\n"
        ),
    )
    execute_parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Path to Phase 3 verified findings JSON (e.g. phase3_verified.json).",
    )
    execute_parser.add_argument(
        "--items",
        type=str,
        nargs="+",
        default=None,
        help=(
            "Finding IDs to remove (e.g. U001 U002 U003). "
            "When omitted the top 3 LOW-risk items are auto-selected."
        ),
    )
    execute_parser.add_argument(
        "--phase1",
        type=str,
        default="audit_report.json",
        help="Path to Phase 1 report (default: audit_report.json).",
    )
    execute_parser.add_argument(
        "--phase2",
        type=str,
        default="phase2_findings.json",
        help="Path to Phase 2 findings (default: phase2_findings.json).",
    )
    execute_parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Root of the git repository to modify (default: current directory).",
    )
    execute_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without making any changes.",
    )
    execute_parser.add_argument(
        "--batch-id",
        type=str,
        default=None,
        help="Optional batch identifier used in branch name and commit message.",
    )
    execute_parser.add_argument(
        "--output",
        type=str,
        default="phase5_report.json",
        help="Destination JSON file for the batch report (default: phase5_report.json).",
    )
    execute_parser.add_argument(
        "--linter",
        action="store_true",
        help="Also run flake8 after tests (requires flake8 to be installed).",
    )
    execute_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed per-step output.",
    )
    execute_parser.set_defaults(func=cmd_execute)

    # ── report (Phase 4) ──────────────────────────────────────────────────
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a Phase 4 audit report (JSON, HTML, CSV, dashboard).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m agents.code_auditor.cli report "
            "--phase3 phase3_verified.json --phase2 phase2_findings.json\n\n"
            "  python -m agents.code_auditor.cli report "
            "--phase3 phase3_verified.json --phase2 phase2_findings.json "
            "--html report.html --csv report.csv\n"
        ),
    )
    report_parser.add_argument(
        "--phase3",
        type=str,
        required=True,
        help="Path to Phase 3 verified findings JSON (e.g. phase3_verified.json).",
    )
    report_parser.add_argument(
        "--phase2",
        type=str,
        required=True,
        help="Path to Phase 2 findings JSON (e.g. phase2_findings.json).",
    )
    report_parser.add_argument(
        "--phase1",
        type=str,
        default="audit_report.json",
        help="Path to Phase 1 report JSON for metadata (default: audit_report.json).",
    )
    report_parser.add_argument(
        "--history",
        type=str,
        default=None,
        metavar="PATH",
        help="Optional JSON file with execution history (list of batch dicts).",
    )
    report_parser.add_argument(
        "--output",
        type=str,
        default="phase4_report.json",
        help="Destination JSON report file (default: phase4_report.json).",
    )
    report_parser.add_argument(
        "--html",
        type=str,
        default=None,
        metavar="PATH",
        help="Also export an HTML report to this path.",
    )
    report_parser.add_argument(
        "--csv",
        type=str,
        default=None,
        metavar="PATH",
        help="Also export a CSV findings table to this path.",
    )
    report_parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip printing the terminal dashboard.",
    )
    report_parser.add_argument(
        "--no-recommendations",
        action="store_true",
        help="Skip printing the recommendations JSON.",
    )
    report_parser.set_defaults(func=cmd_report)

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
