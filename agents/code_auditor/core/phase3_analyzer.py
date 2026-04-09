"""
agents/code_auditor/core/phase3_analyzer.py
==========================================
Phase 3 Safety Analyzer -- compiles STAP 1-5 verification results into a
final risk assessment and human-readable safety report.

The analyzer is the last step before any removal decision is made.  It
reads the Phase 2 findings (original) and the Phase 3 all_checks findings
(which have been piped through all five Phase 3 checkers) and produces:

* A per-finding safety verdict with removal guidance.
* Aggregate statistics comparing Phase 2 vs Phase 3 confidence levels.
* Three removal scenarios ordered from safest to most aggressive.
* A flat recommendations dict split into four action buckets.

Usage::

    from agents.code_auditor.core.phase3_analyzer import Phase3SafetyAnalyzer

    # all_checks = findings after chaining all Phase 3 checkers
    analyzer = Phase3SafetyAnalyzer(phase2_findings, all_checks, verbose=True)
    analyzer.print_summary()
    analyzer.export_to_json("phase3_report.json")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RISK_ORDER: Tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# Confidence threshold used for "high-confidence" item counts
_HIGH_CONF_THRESHOLD: float = 0.85

# Minimum confidence for a LOW-risk item to enter the "safe to remove" bucket
_SAFE_CONF_THRESHOLD: float = 0.70

# Human-readable removal-safety labels keyed by final risk level
_REMOVAL_SAFETY: Dict[str, str] = {
    "LOW":      "SAFE -- good candidate for removal",
    "MEDIUM":   "CAUTION -- plan changes carefully",
    "HIGH":     "RISKY -- requires careful review",
    "CRITICAL": "DO NOT REMOVE -- needs refactoring or is database-related",
}

# Evidence key → concern label for the major-concerns summary
_CONCERN_EVIDENCE_MAP: List[Tuple[str, str, str]] = [
    # (evidence_key, flag_field, concern_label)
    ("database_check",    "is_database_critical", "database"),
    ("api_endpoint_check","is_api_endpoint",       "api_endpoints"),
    ("configuration_check","is_configuration",     "configuration"),
    ("test_dependency_check","has_tests",           "with_tests"),
    ("dynamic_check",     "is_dynamically_loaded", "dynamic_imports"),
]

_WIDTH = 68


# ---------------------------------------------------------------------------
# SafetyAssessment helper dataclass
# ---------------------------------------------------------------------------


class SafetyAssessment:
    """Per-finding output from :meth:`Phase3SafetyAnalyzer.analyze_safety`."""

    __slots__ = (
        "finding_id", "file_path", "finding_type",
        "phase2_risk", "phase2_confidence",
        "final_risk", "final_confidence",
        "removal_safety", "concerns",
        "lines", "recommendation", "original_finding",
    )

    def __init__(
        self,
        finding_id: str,
        file_path: str,
        finding_type: str,
        phase2_risk: str,
        phase2_confidence: float,
        final_risk: str,
        final_confidence: float,
        removal_safety: str,
        concerns: List[str],
        lines: int,
        recommendation: str,
        original_finding: Dict[str, Any],
    ) -> None:
        self.finding_id       = finding_id
        self.file_path        = file_path
        self.finding_type     = finding_type
        self.phase2_risk      = phase2_risk
        self.phase2_confidence = phase2_confidence
        self.final_risk       = final_risk
        self.final_confidence = final_confidence
        self.removal_safety   = removal_safety
        self.concerns         = concerns
        self.lines            = lines
        self.recommendation   = recommendation
        self.original_finding = original_finding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id":        self.finding_id,
            "file_path":         self.file_path,
            "type":              self.finding_type,
            "phase2_risk":       self.phase2_risk,
            "phase2_confidence": round(self.phase2_confidence, 4),
            "final_risk":        self.final_risk,
            "final_confidence":  round(self.final_confidence, 4),
            "removal_safety":    self.removal_safety,
            "concerns":          self.concerns,
            "lines":             self.lines,
            "recommendation":    self.recommendation,
        }


# ---------------------------------------------------------------------------
# Phase3SafetyAnalyzer
# ---------------------------------------------------------------------------


class Phase3SafetyAnalyzer:
    """Compile Phase 3 STAP 1-5 verification results into a safety report.

    Parameters
    ----------
    phase2_findings:
        Original list of Phase 2 finding dicts (before any Phase 3
        adjustment).  Used to compute Phase 2 baseline statistics.
    all_checks:
        Phase 2 findings after being piped through all five Phase 3
        checkers.  Each finding's ``risk`` and ``confidence`` fields
        reflect the most restrictive values applied by the checkers, and
        each finding's ``evidence`` dict contains per-checker results.
    verbose:
        Print one progress line per finding when ``True``.
    """

    def __init__(
        self,
        phase2_findings: List[Dict[str, Any]],
        all_checks: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self.phase2_findings = phase2_findings
        self.all_checks      = all_checks
        self.verbose         = verbose

        # Lazily populated by analyze_safety()
        self._assessments: Optional[List[SafetyAssessment]] = None
        self._report: Optional[Dict[str, Any]] = None

        # Build a quick lookup: finding_id -> phase2 finding
        self._phase2_by_id: Dict[str, Dict[str, Any]] = {
            f.get("id", ""): f for f in phase2_findings
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_safety(self) -> List[Dict[str, Any]]:
        """Return a per-finding safety assessment list.

        Returns
        -------
        List[dict]
            One dict per finding (via :meth:`SafetyAssessment.to_dict`).
            Results are cached after the first call.
        """
        if self._assessments is None:
            self._assessments = [
                self._assess_one(chk) for chk in self.all_checks
            ]
        return [a.to_dict() for a in self._assessments]

    def generate_safety_report(self) -> Dict[str, Any]:
        """Build and return the full Phase 3 safety report dict.

        The report is cached after the first call.
        """
        if self._report is None:
            self._report = self._build_report()
        return self._report

    def print_summary(self) -> None:
        """Print an ASCII dot-padded summary to stdout."""
        report = self.generate_safety_report()
        sa     = report["safety_adjusted"]
        mc     = report["major_concerns"]
        p2_vs  = report["phase2_vs_phase3"]
        sc     = report["scenarios"]

        def row(label: str, value, width: int = _WIDTH) -> None:
            dots = "." * (width - len(label) - len(str(value)) - 2)
            print(f"  {label}{dots} {value}")

        print("=" * _WIDTH)
        print("PHASE 3 SAFETY VERIFICATION REPORT")
        print("=" * _WIDTH)
        print()

        print("[*] Safety Assessment:")
        row("CRITICAL (do not remove)", sa["critical"])
        row("HIGH (risky)",             sa["high"])
        row("MEDIUM (caution)",         sa["medium"])
        row("LOW (safe)",               sa["low"])
        print()

        print("[i] Safety-Adjusted Confidence:")
        row("Phase 2 items > 0.85 confidence", p2_vs["phase2_high_confidence"])
        row("Phase 3 items > 0.85 confidence", p2_vs["phase3_high_confidence"])
        reduced = p2_vs["reduced_by"]
        if reduced > 0:
            print(f"  -> Reduced by {reduced} item(s) due to safety concerns")
        print()

        print("[!] Major Concerns:")
        if mc["database"]:
            print(f"    {mc['database']} DATABASE item(s) (NEVER DELETE)")
        if mc["api_endpoints"]:
            print(f"    {mc['api_endpoints']} API endpoint(s) (suggest deprecation)")
        if mc["configuration"]:
            print(f"    {mc['configuration']} CONFIG-related (review before removing)")
        if mc["with_tests"]:
            print(f"    {mc['with_tests']} WITH TESTS (need test updates first)")
        if mc["dynamic_imports"]:
            print(f"    {mc['dynamic_imports']} DYNAMIC IMPORT(S) (cannot statically verify)")
        if not any(mc.values()):
            print("    None detected")
        print()

        print("[>] Recommended for Removal (after Phase 3 review):")
        safe_count = report["safe_to_remove"]
        safe_lines = report["removable_lines"]
        safety_pct = report["safety_percentage"]
        p2_safety  = report.get("phase2_safety_percentage", 0)
        print(f"    {safe_count} SAFE item(s) with high confidence")
        print(f"    ~{safe_lines:,} lines removable")
        if p2_safety:
            print(f"    Estimated safety: {safety_pct:.0f}% (vs {p2_safety:.0f}% from Phase 2)")
        else:
            print(f"    Estimated safety: {safety_pct:.0f}%")
        print()

        print("[>] Scenarios:")
        s1 = sc["scenario_1_safest"]
        s2 = sc["scenario_2_moderate"]
        s3 = sc["scenario_3_aggressive"]
        print(f"    Scenario 1 (safest)     : {s1['count']:>4} items, "
              f"~{s1['estimated_lines']:,} lines, {s1['estimated_safety_pct']:.0f}% safe")
        print(f"    Scenario 2 (moderate)   : {s2['count']:>4} items, "
              f"~{s2['estimated_lines']:,} lines, {s2['estimated_safety_pct']:.0f}% safe")
        print(f"    Scenario 3 (aggressive) : {s3['count']:>4} items, "
              f"~{s3['estimated_lines']:,} lines, {s3['estimated_safety_pct']:.0f}% safe")
        print()

        print("=" * _WIDTH)

    def export_to_json(self, filepath: str) -> None:
        """Write the full safety report to *filepath* as JSON."""
        report = self.generate_safety_report()
        Path(filepath).write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )
        if self.verbose:
            print(f"[>] Phase 3 report saved to: {Path(filepath).resolve()}")

    # ------------------------------------------------------------------
    # Internal: per-finding assessment
    # ------------------------------------------------------------------

    def _assess_one(self, checked: Dict[str, Any]) -> SafetyAssessment:
        finding_id   = checked.get("id", "UNKNOWN")
        file_path    = checked.get("file_path", "")
        finding_type = checked.get("type", "")

        # Phase 2 baseline (before any Phase 3 adjustment)
        p2_finding   = self._phase2_by_id.get(finding_id, checked)
        p2_risk      = p2_finding.get("risk", "LOW")
        p2_conf      = float(p2_finding.get("confidence", 0.5))

        # Phase 3 final values (already set by checkers)
        final_risk = checked.get("risk", p2_risk)
        final_conf = max(0.0, min(1.0, float(checked.get("confidence", p2_conf))))

        # Collect which concerns fired
        concerns = self._extract_concerns(checked)

        # Lines estimate
        lines = checked.get("lines", 0) or 0

        # Removal safety label
        removal_safety = _REMOVAL_SAFETY.get(final_risk, _REMOVAL_SAFETY["LOW"])

        # Best recommendation from the highest-severity checker
        recommendation = self._best_recommendation(checked, final_risk)

        if self.verbose:
            print(
                f"  [{final_risk:8s}] {finding_id}: conf={final_conf:.2f} "
                f"concerns={concerns or ['none']}"
            )

        return SafetyAssessment(
            finding_id=finding_id,
            file_path=file_path,
            finding_type=finding_type,
            phase2_risk=p2_risk,
            phase2_confidence=p2_conf,
            final_risk=final_risk,
            final_confidence=final_conf,
            removal_safety=removal_safety,
            concerns=concerns,
            lines=lines,
            recommendation=recommendation,
            original_finding=checked,
        )

    @staticmethod
    def _extract_concerns(finding: Dict[str, Any]) -> List[str]:
        evidence = finding.get("evidence") or {}
        concerns: List[str] = []
        for ev_key, flag_field, label in _CONCERN_EVIDENCE_MAP:
            ev = evidence.get(ev_key)
            if isinstance(ev, dict) and ev.get(flag_field):
                concerns.append(label)
        return concerns

    @staticmethod
    def _best_recommendation(finding: Dict[str, Any], final_risk: str) -> str:
        """Return the most relevant recommendation from available evidence."""
        evidence = finding.get("evidence") or {}

        # Priority order: database > api > config > dynamic > test
        priority_keys = [
            "database_check",
            "api_endpoint_check",
            "configuration_check",
            "dynamic_check",
            "test_dependency_check",
        ]
        for key in priority_keys:
            ev = evidence.get(key)
            if isinstance(ev, dict):
                rec = ev.get("recommendation") or ev.get("action")
                if rec:
                    return rec

        # Fallback: generic label based on final risk
        return _REMOVAL_SAFETY.get(final_risk, "")

    # ------------------------------------------------------------------
    # Internal: report building
    # ------------------------------------------------------------------

    def _build_report(self) -> Dict[str, Any]:
        assessments = self._get_assessments()

        # ── Risk distribution ─────────────────────────────────────────
        by_risk: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for a in assessments:
            by_risk[a.final_risk] = by_risk.get(a.final_risk, 0) + 1

        # ── Concern counts ────────────────────────────────────────────
        concern_counts: Dict[str, int] = {
            "database": 0, "api_endpoints": 0, "configuration": 0,
            "with_tests": 0, "dynamic_imports": 0,
        }
        for a in assessments:
            for c in a.concerns:
                if c in concern_counts:
                    concern_counts[c] += 1

        # ── Phase 2 vs Phase 3 confidence ────────────────────────────
        p2_high = sum(
            1 for f in self.phase2_findings
            if float(f.get("confidence", 0)) >= _HIGH_CONF_THRESHOLD
        )
        p3_high = sum(
            1 for a in assessments
            if a.final_confidence >= _HIGH_CONF_THRESHOLD
        )

        # ── Safe-to-remove items ──────────────────────────────────────
        safe_items = [
            a for a in assessments
            if a.final_risk == "LOW" and a.final_confidence >= _SAFE_CONF_THRESHOLD
        ]
        safe_lines = sum(a.lines for a in safe_items)

        total = len(assessments)
        safety_pct = (len(safe_items) / total * 100) if total else 0.0

        # Phase 2 safety % (from Phase2ReportGenerator if embedded)
        p2_safety = self._extract_phase2_safety()

        # ── Scenarios ─────────────────────────────────────────────────
        scenarios = self._build_scenarios(assessments, total)

        # ── Recommendation buckets ────────────────────────────────────
        recommendations = self._build_recommendation_buckets(assessments)

        return {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "total_findings": total,
            "safety_adjusted": {
                "critical": by_risk.get("CRITICAL", 0),
                "high":     by_risk.get("HIGH",     0),
                "medium":   by_risk.get("MEDIUM",   0),
                "low":      by_risk.get("LOW",      0),
            },
            "safe_to_remove":        len(safe_items),
            "removable_lines":       safe_lines,
            "safety_percentage":     round(safety_pct, 1),
            "phase2_safety_percentage": p2_safety,
            "major_concerns": concern_counts,
            "phase2_vs_phase3": {
                "phase2_high_confidence": p2_high,
                "phase3_high_confidence": p3_high,
                "reduced_by":             max(0, p2_high - p3_high),
            },
            "scenarios":        scenarios,
            "recommendations":  recommendations,
            "assessments":      [a.to_dict() for a in assessments],
        }

    def _get_assessments(self) -> List[SafetyAssessment]:
        if self._assessments is None:
            self._assessments = [
                self._assess_one(chk) for chk in self.all_checks
            ]
        return self._assessments

    def _build_scenarios(
        self, assessments: List[SafetyAssessment], total: int
    ) -> Dict[str, Any]:
        """Three removal scenarios from safest to most aggressive."""

        def _scenario(items: List[SafetyAssessment], base_safety: float) -> Dict[str, Any]:
            count = len(items)
            lines = sum(a.lines for a in items)
            # Safety degrades slightly as we include riskier items
            est_safety = base_safety if count else 0.0
            return {
                "count":                count,
                "estimated_lines":      lines,
                "estimated_safety_pct": round(est_safety, 1),
                "finding_ids":          [a.finding_id for a in items],
            }

        # Scenario 1: LOW risk AND high confidence (>= 0.85)
        s1_items = [
            a for a in assessments
            if a.final_risk == "LOW" and a.final_confidence >= _HIGH_CONF_THRESHOLD
        ]

        # Scenario 2: LOW or MEDIUM risk, any confidence
        s2_items = [
            a for a in assessments
            if a.final_risk in ("LOW", "MEDIUM")
        ]

        # Scenario 3: everything except CRITICAL
        s3_items = [
            a for a in assessments
            if a.final_risk != "CRITICAL"
        ]

        return {
            "scenario_1_safest":     _scenario(s1_items, 95.0),
            "scenario_2_moderate":   _scenario(s2_items, 85.0),
            "scenario_3_aggressive": _scenario(s3_items, 75.0),
        }

    def _build_recommendation_buckets(
        self, assessments: List[SafetyAssessment]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Sort findings into four actionable buckets."""

        must_refactor:    List[Dict[str, Any]] = []
        deprecate:        List[Dict[str, Any]] = []
        review_first:     List[Dict[str, Any]] = []
        safe_to_remove:   List[Dict[str, Any]] = []

        for a in assessments:
            entry = {
                "finding_id":       a.finding_id,
                "file_path":        a.file_path,
                "type":             a.finding_type,
                "final_risk":       a.final_risk,
                "final_confidence": round(a.final_confidence, 4),
                "concerns":         a.concerns,
                "recommendation":   a.recommendation,
            }

            if a.final_risk == "CRITICAL":
                must_refactor.append(entry)
            elif "api_endpoints" in a.concerns:
                deprecate.append(entry)
            elif a.final_risk in ("HIGH", "MEDIUM"):
                review_first.append(entry)
            else:
                # LOW risk
                safe_to_remove.append(entry)

        # Sort safe_to_remove by confidence descending (best candidates first)
        safe_to_remove.sort(key=lambda e: e["final_confidence"], reverse=True)

        return {
            "must_refactor_first": must_refactor,
            "deprecate_instead":   deprecate,
            "review_before_remove": review_first,
            "safe_to_remove":      safe_to_remove,
        }

    def _extract_phase2_safety(self) -> float:
        """Best-effort: read Phase 2 safety % if the report is embedded."""
        # Phase2ReportGenerator embeds estimated_safety_pct in its JSON output.
        # If the caller passes phase2_findings that contain that metadata key
        # at the top level, we surface it here.
        for f in self.phase2_findings:
            pct = f.get("estimated_safety_pct") or f.get("phase2_safety_pct")
            if pct is not None:
                try:
                    return float(pct)
                except (TypeError, ValueError):
                    pass
        return 0.0
