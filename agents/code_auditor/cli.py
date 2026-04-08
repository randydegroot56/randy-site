"""
agents/code_auditor/cli.py
===========================
Main CLI entry point for the Code Auditor Agent.

Usage::

    # Discover
    python -m agents.code_auditor.cli discover --project . --verbose
    python -m agents.code_auditor.cli discover --project /repo --output report.json --config ai-command-center

    # Analyze
    python -m agents.code_auditor.cli analyze report.json
    python -m agents.code_auditor.cli analyze report.json --csv files.csv
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
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-auditor",
        description="Code Auditor Agent -- discover and analyze project dependencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Scan the current directory
  python -m agents.code_auditor.cli discover --project . --verbose

  # Scan with a project-specific config
  python -m agents.code_auditor.cli discover --project /repo --config ai-command-center --output report.json

  # Analyze a saved report
  python -m agents.code_auditor.cli analyze report.json

  # Analyze and export per-file metrics to CSV
  python -m agents.code_auditor.cli analyze report.json --csv files.csv
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
