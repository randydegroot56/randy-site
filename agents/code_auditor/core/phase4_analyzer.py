"""
agents/code_auditor/core/phase4_analyzer.py
==========================================
Phase 4 Recommendation Generator -- produce prioritised, actionable
recommendations from a completed audit report.

The generator is read-only: it never touches files or git.  It consumes
the dict produced by ``ReportGenerator.generate_json_report()`` (phase4_reporting.py)
and returns a structured recommendation dict plus helper accessors.

Usage::

    from agents.code_auditor.core.phase4_analyzer import RecommendationGenerator

    gen  = RecommendationGenerator(report_data)
    recs = gen.generate_recommendations()

``report_data`` expected top-level keys (all optional -- missing keys are
treated as empty / zero):

    summary           dict   -- overall counts + line estimates
    by_type           dict   -- per-type breakdown
    by_risk           dict   -- CRITICAL / HIGH / MEDIUM / LOW counts
    execution_history list   -- completed removal batches
    recommendations   list   -- pre-ranked LOW-risk candidates
    _findings_raw     list   -- raw Phase 2 / 3 finding dicts (for patterns)
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BATCH_SIZE       = 3    # items processed per execution batch
_WORKING_DAYS     = 5    # working days per week
_MINUTES_PER_ITEM = 3    # rough estimate: 3 min per item (test + commit)

_RISK_REASONS: Dict[str, str] = {
    "CRITICAL": (
        "Database schemas, migrations, core infrastructure, or items with "
        "broad transitive imports that could break unrelated parts of the system."
    ),
    "HIGH": (
        "Publicly exported symbols, items referenced across multiple packages, "
        "or items whose usage could not be fully verified statically."
    ),
}

_RISK_ACTIONS: Dict[str, str] = {
    "CRITICAL": (
        "Refactor instead of deleting: extract to a smaller, well-named unit, "
        "add deprecation notices, and migrate callers before removal."
    ),
    "HIGH": (
        "Manual review recommended: confirm no dynamic references (getattr, "
        "importlib, plugin loaders) before scheduling for removal."
    ),
}

_PATTERN_LABELS: Dict[str, str] = {
    "dense_import_file":  "File with many unused imports",
    "orphan_folder":      "Folder where most files are orphaned",
    "type_concentration": "Single type dominates findings",
    "high_confidence":    "Large cluster of high-confidence removals",
}


# ---------------------------------------------------------------------------
# RecommendationGenerator
# ---------------------------------------------------------------------------


class RecommendationGenerator:
    """Generate prioritised recommendations from an audit report dict.

    Parameters
    ----------
    report_data:
        The dict returned by ``ReportGenerator.generate_json_report()``.
    batch_size:
        Number of items per execution batch (default 3).
    """

    def __init__(self, report_data: dict, batch_size: int = _BATCH_SIZE) -> None:
        self.data        = report_data
        self.batch_size  = batch_size
        self._findings   = (
            report_data.get("_findings_raw", [])
            or report_data.get("findings", [])
        )
        self._removed_ids: set = {
            fid
            for batch in report_data.get("execution_history", [])
            for fid    in batch.get("items", [])
        }

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def generate_recommendations(self) -> dict:
        """Return the full recommendation dict.

        Structure
        ---------
        recommendations:
            immediate       -- LOW-risk items, safe to batch now
            review_first    -- MEDIUM-risk items, needs human eye
            do_not_remove   -- CRITICAL items, refactor instead
            patterns        -- codebase-level patterns & opportunities
            progress        -- removal progress metrics + trend
            next_batch      -- concrete next execution command
        """
        return {
            "recommendations": {
                "immediate":    self._build_immediate(),
                "review_first": self._build_review_first(),
                "do_not_remove": self._build_do_not_remove(),
                "patterns":     self._build_patterns(),
                "progress":     self._build_progress(),
                "next_batch":   self._build_next_batch(),
            }
        }

    # ------------------------------------------------------------------ #
    # Section builders                                                      #
    # ------------------------------------------------------------------ #

    def _build_immediate(self) -> dict:
        low_items     = self._remaining_by_risk("LOW")
        count         = len(low_items)
        est_lines     = sum(f.get("lines", f.get("estimated_lines", 0)) for f in low_items)
        confidences   = [
            f.get("confidence", f.get("estimated_safety", 0) / 100)
            for f in low_items
        ]
        avg_safety    = (
            round(sum(confidences) / len(confidences) * 100) if confidences else 0
        )
        batches_needed   = math.ceil(count / self.batch_size) if count else 0
        timeline_weeks   = max(1, math.ceil(batches_needed / _WORKING_DAYS)) if batches_needed else 0

        return {
            "description":     "Safe & Low Risk items — batch and remove now",
            "count":           count,
            "estimated_lines": est_lines,
            "estimated_safety": avg_safety,
            "batches_needed":  batches_needed,
            "timeline_weeks":  timeline_weeks,
        }

    def _build_review_first(self) -> dict:
        medium_items    = self._remaining_by_risk("MEDIUM")
        count           = len(medium_items)
        est_lines       = sum(f.get("lines", f.get("estimated_lines", 0)) for f in medium_items)
        # Top 3 by lines descending (highest impact candidates)
        top_sorted      = sorted(medium_items, key=lambda f: f.get("lines", 0), reverse=True)
        top_candidates  = [f.get("id", "") for f in top_sorted[:3]]

        return {
            "description":    "Medium Risk items — review before removing",
            "count":          count,
            "estimated_lines": est_lines,
            "timeline_weeks": 2,
            "top_candidates": top_candidates,
            "caution_reasons": [
                "Item may have dynamic references (getattr / importlib).",
                "Item is exported but callers could not be fully resolved.",
                "Confidence < 80 % — static analysis may have missed a usage.",
            ],
        }

    def _build_do_not_remove(self) -> dict:
        critical_items = self._remaining_by_risk("CRITICAL")
        count          = len(critical_items)
        names          = [
            f.get("name", f.get("item", f.get("id", ""))) for f in critical_items
        ]

        return {
            "description":   "Critical items — do NOT delete, refactor instead",
            "count":         count,
            "items":         names[:10],
            "reason":        _RISK_REASONS.get("CRITICAL", ""),
            "action":        _RISK_ACTIONS.get("CRITICAL", ""),
            "timeline_weeks": 12,
        }

    def _build_patterns(self) -> dict:
        return {
            "identified": self._identify_patterns(),
            "opportunities": self._identify_opportunities(),
        }

    def _build_progress(self) -> dict:
        summary        = self.data.get("summary", {})
        total          = summary.get("total_findings", 0)
        removed        = summary.get("removed", len(self._removed_ids))
        pct_complete   = round(removed / total * 100) if total else 0
        lines_removed  = sum(
            b.get("lines_removed", 0) for b in self.data.get("execution_history", [])
        )
        trend          = self._compute_trend()

        return {
            "items_removed":   removed,
            "items_total":     total,
            "percent_complete": pct_complete,
            "lines_removed":   lines_removed,
            "trend":           trend,
        }

    def _build_next_batch(self) -> dict:
        batch    = self._rank_next_batch()
        ids      = [item["id"] for item in batch]
        est_lines  = sum(item.get("estimated_lines", 0) for item in batch)
        confidences = [item.get("estimated_safety", 0) for item in batch]
        avg_safety  = round(sum(confidences) / len(confidences)) if confidences else 0
        est_minutes = len(batch) * _MINUTES_PER_ITEM
        ids_str    = " ".join(ids)
        command    = (
            f"python cli.py execute --report phase3_verified.json --items {ids_str}"
            if ids_str else "# No candidates available"
        )

        return {
            "items":                  ids,
            "item_details":           batch,
            "estimated_lines":        est_lines,
            "estimated_safety":       avg_safety,
            "estimated_time_minutes": est_minutes,
            "command":                command,
        }

    # ------------------------------------------------------------------ #
    # Core helpers                                                          #
    # ------------------------------------------------------------------ #

    def _rank_next_batch(self) -> List[dict]:
        """Return top ``batch_size`` LOW-risk candidates, ranked for safety.

        Ranking criteria (descending priority):
        1. Confidence / safety  (higher = safer)
        2. Lines removed        (higher = more impact)
        """
        # Prefer the pre-ranked recommendations list from the report
        recs = self.data.get("recommendations", [])
        if recs:
            return [
                {
                    "id":               r.get("id", ""),
                    "name":             r.get("name", ""),
                    "type":             r.get("type", ""),
                    "estimated_lines":  r.get("estimated_lines", 0),
                    "estimated_safety": r.get("estimated_safety", 0),
                }
                for r in recs[: self.batch_size]
            ]

        # Fall back to raw findings when recommendations are absent
        low_remaining = self._remaining_by_risk("LOW")
        ranked = sorted(
            low_remaining,
            key=lambda f: (
                f.get("confidence", f.get("estimated_safety", 0) / 100),
                f.get("lines", 0),
            ),
            reverse=True,
        )
        return [
            {
                "id":               f.get("id", ""),
                "name":             f.get("name", f.get("item", "")),
                "type":             f.get("type", ""),
                "estimated_lines":  f.get("lines", 0),
                "estimated_safety": round(
                    f.get("confidence", f.get("estimated_safety", 0) / 100) * 100
                ),
            }
            for f in ranked[: self.batch_size]
        ]

    def _identify_patterns(self) -> List[str]:
        """Scan findings for codebase-level anti-patterns worth calling out."""
        patterns: List[str] = []

        if not self._findings:
            return patterns

        # --- Dense import files ----------------------------------------
        import_findings = [
            f for f in self._findings if f.get("type") == "unused_import"
        ]
        imports_by_file: Counter = Counter(
            f.get("file", f.get("path", "")) for f in import_findings
        )
        for fpath, cnt in imports_by_file.most_common(3):
            if cnt >= 3:
                patterns.append(
                    f"Dense unused imports: '{fpath}' has {cnt} unused imports — "
                    "consider a full import audit of this file."
                )

        # --- Orphan folder clusters ------------------------------------
        orphan_findings = [
            f for f in self._findings if f.get("type") == "orphan_file"
        ]
        folder_counter: Counter = Counter()
        for f in orphan_findings:
            path = f.get("file", f.get("path", ""))
            folder = "/".join(path.replace("\\", "/").split("/")[:-1]) or "."
            folder_counter[folder] += 1
        for folder, cnt in folder_counter.most_common(3):
            if cnt >= 2:
                patterns.append(
                    f"Orphan cluster: '{folder}/' contains {cnt} orphan files — "
                    "the entire folder may be obsolete."
                )

        # --- Type concentration ----------------------------------------
        type_counter: Counter = Counter(
            f.get("type", "") for f in self._findings
        )
        dominant_type, dominant_count = type_counter.most_common(1)[0] if type_counter else ("", 0)
        total = len(self._findings) or 1
        if dominant_count / total > 0.5:
            patterns.append(
                f"Type concentration: '{dominant_type}' accounts for "
                f"{round(dominant_count / total * 100)}% of all findings — "
                "a targeted cleanup pass for this type would be highly effective."
            )

        # --- High-confidence cluster -----------------------------------
        high_conf = [
            f for f in self._findings
            if f.get("confidence", 0) >= 0.9 and f.get("id") not in self._removed_ids
        ]
        if len(high_conf) >= 5:
            patterns.append(
                f"High-confidence cluster: {len(high_conf)} items have >=90% confidence -- "
                "these can be batched aggressively with minimal risk."
            )

        return patterns

    def _identify_opportunities(self) -> List[str]:
        """Return short opportunity strings for the dashboard."""
        opps: List[str] = []
        by_risk  = self.data.get("by_risk", {})
        low_rem  = by_risk.get("LOW", {}).get("remaining", 0)
        med_rem  = by_risk.get("MEDIUM", {}).get("remaining", 0)

        if low_rem:
            opps.append(
                f"Quick wins: {low_rem} LOW-risk items can be removed safely right now."
            )
        if med_rem:
            opps.append(
                f"Review queue: {med_rem} MEDIUM-risk items are ready for manual review."
            )

        # Lines savings
        summary   = self.data.get("summary", {})
        rem_lines = summary.get("estimated_lines_remaining", 0)
        if rem_lines:
            opps.append(
                f"Codebase shrink: removing remaining verified items saves ~{rem_lines} lines."
            )

        return opps

    def _estimate_timelines(self) -> dict:
        """Return per-risk timeline estimates in weeks."""
        by_risk = self.data.get("by_risk", {})

        def _weeks(risk: str, days_per_item: float) -> int:
            remaining = by_risk.get(risk, {}).get("remaining", 0)
            total_days = remaining * days_per_item
            return max(1, math.ceil(total_days / _WORKING_DAYS)) if remaining else 0

        return {
            "LOW":      _weeks("LOW",      1 / _BATCH_SIZE),   # 3 items/day
            "MEDIUM":   _weeks("MEDIUM",   0.5),               # 2 items/day (manual review)
            "HIGH":     _weeks("HIGH",     1.0),               # 1 item/day
            "CRITICAL": _weeks("CRITICAL", 5.0),               # 1 item per week (refactor)
        }

    # ------------------------------------------------------------------ #
    # Internal utilities                                                    #
    # ------------------------------------------------------------------ #

    def _remaining_by_risk(self, risk: str) -> List[dict]:
        """Return raw findings at ``risk`` level that have not been removed."""
        return [
            f for f in self._findings
            if f.get("risk") == risk and f.get("id") not in self._removed_ids
        ]

    def _compute_trend(self) -> List[dict]:
        """Summarise execution history as a simple trend list (newest last)."""
        history = self.data.get("execution_history", [])
        trend: List[dict] = []
        cumulative = 0
        for batch in history:
            cumulative += len(batch.get("items", []))
            trend.append({
                "batch_id":    batch.get("batch_id", ""),
                "timestamp":   batch.get("timestamp", "")[:16].replace("T", " "),
                "items_batch": len(batch.get("items", [])),
                "items_total": cumulative,
                "lines":       batch.get("lines_removed", 0),
            })
        return trend
