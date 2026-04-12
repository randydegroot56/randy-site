"""Unit tests for FixerEngine data layer (load_report + build_batches)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.code_fixer.cli import FixerEngine


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _write_phase3(tmp_path: Path, all_checks: list) -> Path:
    data = {"all_checks": all_checks, "scenarios": {}}
    p = tmp_path / "phase3_verified.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _write_phase2(tmp_path: Path, findings: list) -> Path:
    data = {"findings": findings}
    p = tmp_path / "phase2_findings.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


FINDINGS = [
    {"id": "O001", "type": "orphan_file",   "file": "old.js", "item": "old",      "risk": "LOW",    "confidence": 0.99, "lines": 80},
    {"id": "O002", "type": "orphan_file",   "file": "dead.py","item": "dead",     "risk": "LOW",    "confidence": 0.98, "lines": 60},
    {"id": "U001", "type": "unused_export", "file": "theme.js","item": "useTheme","risk": "MEDIUM", "confidence": 0.90, "lines": 20},
    {"id": "U002", "type": "unused_import", "file": "api.py",  "item": "logging", "risk": "LOW",    "confidence": 0.95, "lines": 1},
]

ALL_CHECKS = [
    {"id": "O001", "risk_level": "LOW",    "confidence": 0.99, "file": "old.js",  "name": "old",      "type": "orphan_file"},
    {"id": "O002", "risk_level": "LOW",    "confidence": 0.98, "file": "dead.py", "name": "dead",     "type": "orphan_file"},
    {"id": "U001", "risk_level": "MEDIUM", "confidence": 0.90, "file": "theme.js","name": "useTheme", "type": "unused_export"},
    {"id": "U002", "risk_level": "LOW",    "confidence": 0.95, "file": "api.py",  "name": "logging",  "type": "unused_import"},
]


# ── load_report ───────────────────────────────────────────────────────────────

class TestLoadReport:
    def test_loads_low_risk_candidates_only_by_default(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        candidates = eng.load_report()
        ids = {c["id"] for c in candidates}
        assert "O001" in ids
        assert "O002" in ids
        assert "U002" in ids
        assert "U001" not in ids   # MEDIUM excluded from LOW filter

    def test_loads_medium_candidates_when_risk_medium(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="MEDIUM")
        ids = {c["id"] for c in eng.load_report()}
        assert "U001" in ids

    def test_filters_to_specific_items_when_items_given(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, items=["O001"])
        ids = {c["id"] for c in eng.load_report()}
        assert ids == {"O001"}

    def test_raises_when_report_file_missing(self, tmp_path):
        eng = FixerEngine(
            report_path=tmp_path / "nonexistent.json",
            project_root=tmp_path,
        )
        with pytest.raises(FileNotFoundError):
            eng.load_report()

    def test_falls_back_to_phase2_when_no_all_checks(self, tmp_path):
        """When phase3 has only scenarios, join with phase2_findings.json."""
        phase3_data = {
            "scenarios": {
                "scenario_1_safest": {"finding_ids": ["O001", "O002"]},
                "scenario_2_moderate": {"finding_ids": ["O001", "O002", "U001", "U002"]},
            }
        }
        p3 = tmp_path / "phase3_verified.json"
        p3.write_text(json.dumps(phase3_data), encoding="utf-8")
        _write_phase2(tmp_path, FINDINGS)

        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        ids = {c["id"] for c in eng.load_report()}
        assert "O001" in ids
        assert "U001" not in ids  # MEDIUM


# ── build_batches ─────────────────────────────────────────────────────────────

class TestBuildBatches:
    def _engine(self, tmp_path: Path, batch_size: int = 3) -> FixerEngine:
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="MEDIUM", batch_size=batch_size,
        )
        eng._candidates = eng.load_report()
        return eng

    def test_chunks_into_correct_batch_size(self, tmp_path):
        eng = self._engine(tmp_path, batch_size=2)
        batches = eng.build_batches()
        for b in batches[:-1]:
            assert len(b) == 2

    def test_orphan_files_sorted_first(self, tmp_path):
        eng = self._engine(tmp_path)
        batches = eng.build_batches()
        flat = [fid for batch in batches for fid in batch]
        # O001, O002 should appear before U001, U002
        assert flat.index("O001") < flat.index("U001")

    def test_higher_confidence_sorted_before_lower_within_same_risk(self, tmp_path):
        eng = self._engine(tmp_path)
        batches = eng.build_batches()
        flat = [fid for batch in batches for fid in batch]
        # O001 (confidence 0.99) before O002 (0.98) within same risk tier
        assert flat.index("O001") < flat.index("O002")

    def test_single_item_batch_when_remainder(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS[:4])
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="MEDIUM", batch_size=3,
        )
        eng._candidates = eng.load_report()
        batches = eng.build_batches()
        assert sum(len(b) for b in batches) == len(eng._candidates)
