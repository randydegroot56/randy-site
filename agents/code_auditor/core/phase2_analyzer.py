"""
agents/code_auditor/core/phase2_analyzer.py
============================================
Phase 2 post-processing: adjusts detection findings based on observed
test coverage, and generates the final Phase 2 report.

A finding with test coverage should be treated more cautiously — deleting
something that is tested may break the test suite even if no production code
imports it directly.  A finding *without* any test coverage is a stronger
deletion candidate.

Usage::

    from agents.code_auditor.core.phase2_analyzer import (
        TestCoverageVerifier,
        Phase2ReportGenerator,
    )

    verifier = TestCoverageVerifier(phase1_report, findings, verbose=True)
    adjusted = verifier.adjust_findings_for_tests()

    gen = Phase2ReportGenerator(adjusted, phase1_report)
    gen.print_summary()
    gen.export_to_json("phase2_report.json")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set


# ---------------------------------------------------------------------------
# Risk-level ordering helpers
# ---------------------------------------------------------------------------

_RISK_ORDER: Dict[str, int] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_ORDER_RISK: Dict[int, str] = {v: k for k, v in _RISK_ORDER.items()}


def _raise_risk(current: str) -> str:
    """Move risk one level higher (e.g. LOW -> MEDIUM), capped at CRITICAL."""
    idx = _RISK_ORDER.get(current, 1)
    return _ORDER_RISK.get(min(idx + 1, 3), "CRITICAL")


def _cap_confidence(value: float) -> float:
    return round(min(max(value, 0.0), 0.99), 4)


# ---------------------------------------------------------------------------
# Test coverage verifier
# ---------------------------------------------------------------------------


class TestCoverageVerifier:
    """Adjust Phase 2 findings based on observed test-file coverage.

    For each finding the verifier:

    * Detects whether any test file imports from the affected file or
      explicitly mentions the flagged symbol by name.
    * **Reduces** confidence by 0.15 when tests exist — the item may be
      exercised indirectly, so we are less certain it is safe to remove.
    * **Increases** confidence by 0.10 when no tests exist — untested *and*
      unused items are the strongest deletion candidates.
    * Raises the risk level by one step (e.g. ``"LOW"`` -> ``"MEDIUM"``) for
      findings that have test coverage, to signal that deletion *will* require
      test updates.
    * Records ``"test_coverage": True/False`` in the finding's ``evidence``
      dict regardless of whether the adjustment changed anything.

    ``"CRITICAL"`` findings (circular dependencies) are passed through
    unchanged — their risk and confidence are factual, not probabilistic.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    findings:
        The raw list of finding dicts produced by the Phase 2 detectors.
    verbose:
        When ``True``, print one line per adjusted finding to stdout.
    """

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self._report   = phase1_report
        self._findings = findings
        self.verbose   = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

        # Pre-build coverage structures once, reused for every finding.
        self._test_imports: Dict[str, Set[str]]  = {}
        self._test_mentions: Dict[str, Set[str]] = {}
        self._test_file_paths: List[str]         = []
        self._build_test_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def adjust_findings_for_tests(self) -> List[Dict[str, Any]]:
        """Return a new list of findings with confidence and risk adjusted.

        Each dict is a *shallow copy* of the original with ``confidence``,
        ``risk``, and ``evidence["test_coverage"]`` updated.  The original
        dicts in ``self._findings`` are not mutated.
        """
        adjusted: List[Dict[str, Any]] = []

        for raw in self._findings:
            finding = dict(raw)

            # CRITICAL findings are structural facts — never adjust them.
            if finding.get("risk") == "CRITICAL":
                finding.setdefault("evidence", {})["test_coverage"] = False
                adjusted.append(finding)
                continue

            # Determine the primary file and symbol for this finding.
            file_path = finding.get("file", "")
            if not file_path:
                files_list = finding.get("files", [])
                file_path  = files_list[0] if files_list else ""

            symbol = finding.get("item", "")
            has_coverage = self._is_covered(file_path, symbol)

            # Evidence
            evidence = dict(finding.get("evidence") or {})
            evidence["test_coverage"] = has_coverage
            finding["evidence"] = evidence

            # Confidence
            original_conf = float(finding.get("confidence", 0.7))
            new_conf = _cap_confidence(
                original_conf - 0.15 if has_coverage else original_conf + 0.10
            )
            finding["confidence"] = new_conf

            # Risk
            original_risk = finding.get("risk", "MEDIUM")
            new_risk = _raise_risk(original_risk) if has_coverage else original_risk
            finding["risk"] = new_risk

            if self.verbose and (new_conf != original_conf or new_risk != original_risk):
                label = "covered" if has_coverage else "uncovered"
                self._log(
                    f"  [{finding.get('id', '?')}] {label}: "
                    f"conf {original_conf:.2f} -> {new_conf:.2f}, "
                    f"risk {original_risk} -> {new_risk}"
                )

            adjusted.append(finding)

        self._log(
            f"TestCoverageVerifier: {len(adjusted)} finding(s) processed "
            f"({sum(1 for f in adjusted if f.get('evidence', {}).get('test_coverage'))} covered)."
        )
        return adjusted

    # ------------------------------------------------------------------
    # Coverage detection
    # ------------------------------------------------------------------

    def _is_covered(self, file_path: str, symbol: str) -> bool:
        """Return ``True`` if any test file references *file_path* or *symbol*."""
        file_stem   = Path(file_path).stem
        file_dotted = Path(file_path).with_suffix("").as_posix().replace("/", ".")

        for test_path in self._test_file_paths:
            imports  = self._test_imports.get(test_path, set())
            mentions = self._test_mentions.get(test_path, set())

            if file_dotted in imports or file_stem in imports:
                return True
            if symbol and symbol in mentions:
                return True

        return False

    def _build_test_index(self) -> None:
        """Pre-index all test files by their imports and mentioned symbols."""
        for f in self._files:
            path = f.get("path", "")
            if not self._is_test_file(path):
                continue

            self._test_file_paths.append(path)
            imports_list: List[str] = f.get("imports", [])
            exports_list: List[str] = f.get("exports", [])

            expanded: Set[str] = set()
            for imp in imports_list:
                clean = imp.lstrip(".")
                expanded.add(clean)
                expanded.add(clean.split(".")[-1])

            self._test_imports[path]  = expanded
            self._test_mentions[path] = set(exports_list) | expanded

    @staticmethod
    def _is_test_file(path: str) -> bool:
        name  = Path(path).name
        posix = path.replace("\\", "/")
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in posix
            or "/test/" in posix
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


class Phase2ReportGenerator:
    """Aggregate Phase 2 findings into a structured, exportable report.

    Parameters
    ----------
    findings:
        The (optionally test-adjusted) list of finding dicts from Phase 2
        detectors.
    phase1_report:
        The Phase 1 registry dict, used to pull project-level metadata.
    """

    # Finding types that are refactor targets, not deletion candidates.
    _NON_DELETION_TYPES: Set[str] = {"circular_dependency"}

    def __init__(self, findings: List[Dict[str, Any]], phase1_report: Dict[str, Any]) -> None:
        self._findings     = findings
        self._phase1       = phase1_report
        self._report: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(self) -> Dict[str, Any]:
        """Build and return the complete report dict.

        The returned dict is JSON-serialisable and has the shape::

            {
              "timestamp":       "...",
              "summary":         { ... },
              "findings":        [ ... ],
              "scenarios":       [ ... ],
              "recommendations": { ... },
            }
        """
        summary         = self._build_summary()
        scenarios       = self._build_scenarios(summary)
        recommendations = self._build_recommendations(summary)

        self._report = {
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "summary":         summary,
            "findings":        self._findings,
            "scenarios":       scenarios,
            "recommendations": recommendations,
        }
        return self._report

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout.

        Calls :meth:`generate_report` automatically when not yet called.
        """
        if not self._report:
            self.generate_report()

        s   = self._report["summary"]
        scs = self._report["scenarios"]
        width = 68

        def row(label: str, value: Any) -> None:
            dots = "." * (width - len(label) - len(str(value)) - 2)
            print(f"  {label}{dots} {value}")

        print("=" * width)
        print("PHASE 2 ANALYSIS REPORT")
        print()

        print(f"[*] Total Findings: {s['total_findings']}")
        print()

        print("[>] Findings by Type:")
        bt = s["by_type"]
        row("unused_exports",  bt.get("unused_export",       0))
        row("orphan_files",    bt.get("orphan_file",         0))
        row("unused_imports",  bt.get("unused_import",       0))
        row("circular_deps",   bt.get("circular_dependency", 0))
        print()

        print("[!] By Risk Level:")
        br = s["by_risk"]
        row("LOW    (safe to remove)",    br.get("LOW",      0))
        row("MEDIUM (review first)",      br.get("MEDIUM",   0))
        row("HIGH   (investigate)",       br.get("HIGH",     0))
        row("CRITICAL (refactor needed)", br.get("CRITICAL", 0))
        print()

        print("[~] By Confidence:")
        bc = s["by_confidence"]
        row("HIGH   (> 0.85)",    bc.get("HIGH",   0))
        row("MEDIUM (0.60-0.85)", bc.get("MEDIUM", 0))
        row("LOW    (< 0.60)",    bc.get("LOW",    0))
        print()

        rec   = s["recommended_for_removal"]
        lines = s["estimated_removable_lines"]
        safety = s["estimated_safety_pct"]
        print(f"[OK] Recommended for Removal: {rec} LOW-risk items")
        if lines:
            print(f"     ~{lines:,} lines removable  |  estimated safety: {safety}%")
        else:
            print(f"     estimated safety: {safety}%")
        print()

        print("[+] Removal Scenarios:")
        for sc in scs:
            print(
                f"  Scenario {sc['scenario']}: {sc['label']} -- "
                f"{sc['item_count']} items, {sc['estimated_safety_pct']}% safety"
            )

        print("=" * width)

    def export_to_json(self, filepath: str) -> None:
        """Write the complete report to *filepath* as formatted JSON.

        Calls :meth:`generate_report` automatically when not yet called.
        """
        if not self._report:
            self.generate_report()

        dest = Path(filepath)
        dest.write_text(
            json.dumps(self._report, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Phase 2 report exported -> {dest.resolve()}")

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    def _build_summary(self) -> Dict[str, Any]:
        total = len(self._findings)

        # By type + per-type average confidence
        by_type: Dict[str, int] = {}
        type_confs: Dict[str, List[float]] = {}
        for f in self._findings:
            t = f.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            type_confs.setdefault(t, []).append(float(f.get("confidence", 0)))

        avg_conf_by_type = {
            t: round(sum(vals) / len(vals), 3)
            for t, vals in type_confs.items()
        }

        # By risk
        by_risk: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for f in self._findings:
            r = f.get("risk", "HIGH")
            by_risk[r] = by_risk.get(r, 0) + 1

        # By confidence bucket
        by_confidence: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in self._findings:
            c = float(f.get("confidence", 0))
            if c > 0.85:
                by_confidence["HIGH"] += 1
            elif c >= 0.60:
                by_confidence["MEDIUM"] += 1
            else:
                by_confidence["LOW"] += 1

        # Removal candidates: LOW risk, not circular
        removable = [
            f for f in self._findings
            if f.get("risk") == "LOW"
            and f.get("type") not in self._NON_DELETION_TYPES
        ]
        rec_count = len(removable)

        # Estimate removable lines from orphan files only (conservative)
        removable_lines = sum(
            int(f.get("evidence", {}).get("lines", 0))
            for f in removable
            if f.get("type") == "orphan_file"
        )

        # Safety estimate: average confidence of LOW-risk items as a percentage
        safety_pct = 0
        if removable:
            avg = sum(float(f.get("confidence", 0)) for f in removable) / len(removable)
            safety_pct = round(avg * 100)

        return {
            "total_findings":            total,
            "by_type":                   by_type,
            "avg_confidence_by_type":    avg_conf_by_type,
            "by_risk":                   by_risk,
            "by_confidence":             by_confidence,
            "high_confidence":           by_confidence["HIGH"],
            "recommended_for_removal":   rec_count,
            "estimated_removable_lines": removable_lines,
            "estimated_safety_pct":      safety_pct,
        }

    # ------------------------------------------------------------------
    # Scenario builder
    # ------------------------------------------------------------------

    def _build_scenarios(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return three removal scenarios from safest to most aggressive."""
        non_circ = [
            f for f in self._findings
            if f.get("type") not in self._NON_DELETION_TYPES
        ]

        def scenario(num: int, label: str, items: List[Dict], base_safety: int) -> Dict:
            if not items:
                return {
                    "scenario": num, "label": label,
                    "item_count": 0, "items": [],
                    "estimated_safety_pct": base_safety,
                }
            avg = sum(float(f.get("confidence", 0)) for f in items) / len(items)
            return {
                "scenario":             num,
                "label":                label,
                "item_count":           len(items),
                "items":                [f.get("id") for f in items],
                "estimated_safety_pct": min(round(avg * 100), base_safety),
            }

        high_conf    = [f for f in non_circ if float(f.get("confidence", 0)) > 0.85]
        med_and_high = [f for f in non_circ if float(f.get("confidence", 0)) >= 0.60]
        all_non_circ = non_circ

        return [
            scenario(1, "Remove HIGH confidence only (safest)",        high_conf,    95),
            scenario(2, "Remove HIGH + MEDIUM confidence (aggressive)", med_and_high, 85),
            scenario(3, "Remove all except CRITICAL (very aggressive)", all_non_circ, 75),
        ]

    # ------------------------------------------------------------------
    # Recommendations builder
    # ------------------------------------------------------------------

    def _build_recommendations(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Return an action-oriented recommendations dict."""
        br  = summary["by_risk"]
        bt  = summary["by_type"]
        circ = bt.get("circular_dependency", 0)

        actions: List[str] = []
        if br.get("LOW", 0):
            actions.append(
                f"Review and remove {br['LOW']} LOW-risk item(s) "
                "(start with orphan files, then unused exports)."
            )
        if br.get("MEDIUM", 0):
            actions.append(
                f"Manually verify {br['MEDIUM']} MEDIUM-risk item(s) before deletion."
            )
        if br.get("HIGH", 0):
            actions.append(
                f"Investigate {br['HIGH']} HIGH-risk item(s) -- do NOT delete without review."
            )
        if circ:
            actions.append(
                f"Refactor {circ} circular dependency chain(s) "
                "before touching any involved file."
            )
        if not actions:
            actions.append("No actionable findings. Codebase looks clean.")

        do_not_delete = []
        for f in self._findings:
            if f.get("type") in self._NON_DELETION_TYPES:
                path = f.get("file") or (f.get("files") or [None])[0]
                if path:
                    do_not_delete.append(path)

        return {
            "priority_order": [
                "circular_dependency",
                "unused_export",
                "orphan_file",
                "unused_import",
            ],
            "actions":       actions,
            "do_not_delete": do_not_delete,
        }
