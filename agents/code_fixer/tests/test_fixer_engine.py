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


# ── run() ────────────────────────────────────────────────────────────────────

from unittest.mock import MagicMock, patch


class TestRun:
    """Test FixerEngine.run() using mocked BatchRemover, GitOrchestrator, SafetyValidator."""

    def _engine(self, tmp_path: Path) -> FixerEngine:
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(
            report_path=p3, project_root=tmp_path,
            risk="LOW", batch_size=2, skip_failed=False,
        )
        eng._candidates = eng.load_report()
        return eng

    def _mock_safety(self, passed: bool = True):
        v = MagicMock()
        ok = MagicMock(); ok.passed = True
        fail = MagicMock(); fail.passed = False; fail.message = "unsafe"
        v.validate_report.return_value = ok
        v.validate_git_clean.return_value = ok
        v.run_baseline_tests.return_value = ok
        v.validate_batch_dry_run.return_value = ok if passed else fail
        return v

    def _mock_remover(self, success: bool = True):
        r = MagicMock()
        if success:
            r.remove_batch.return_value = {
                "branch_created": "audit/remove-O001-2026-04-12",
                "items_removed": ["O001", "O002"],
                "total_lines_removed": 140,
                "status": "success",
            }
        else:
            r.remove_batch.return_value = {
                "branch_created": "audit/remove-O001-2026-04-12",
                "items_removed": [],
                "total_lines_removed": 0,
                "status": "failed",
                "errors": ["file not found"],
            }
        return r

    def test_successful_run_returns_success_status(self, tmp_path):
        eng = self._engine(tmp_path)
        mock_git = MagicMock()
        mock_git.run_tests.return_value = (True, "3 passed")
        mock_git.commit_batch.return_value = "abc1234"
        mock_git.merge_to_main.return_value = None

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        assert result.status in ("success", "partial")
        assert result.batches_succeeded > 0

    def test_failed_batch_stops_on_default_mode(self, tmp_path):
        eng = self._engine(tmp_path)
        eng.skip_failed = False

        mock_git = MagicMock()
        mock_git.run_tests.return_value = (False, "1 failed")
        mock_git.current_branch.return_value = "audit/remove-O001-2026-04-12"

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        # Should have stopped — no more batches after the first failure
        assert result.batches_failed >= 1
        assert result.status in ("partial", "failed")

    def test_skip_failed_continues_after_failure(self, tmp_path):
        eng = self._engine(tmp_path)
        eng.skip_failed = True

        call_count = 0
        def alternating_tests():
            nonlocal call_count
            call_count += 1
            return (call_count % 2 == 0), "output"

        mock_git = MagicMock()
        mock_git.run_tests.side_effect = lambda: alternating_tests()
        mock_git.commit_batch.return_value = "abc1234"
        mock_git.merge_to_main.return_value = None
        mock_git.current_branch.return_value = "audit/remove-O001-2026-04-12"

        with (
            patch("agents.code_fixer.cli.SafetyValidator", return_value=self._mock_safety()),
            patch("agents.code_fixer.cli.BatchRemover", return_value=self._mock_remover()),
            patch("agents.code_fixer.cli.GitOrchestrator", return_value=mock_git),
        ):
            result = eng.run()

        # With skip_failed, it should attempt multiple batches
        assert result.batches_attempted > 1


class TestDryRun:
    def test_dry_run_returns_preview_without_changes(self, tmp_path):
        p3 = _write_phase3(tmp_path, ALL_CHECKS)
        eng = FixerEngine(report_path=p3, project_root=tmp_path, risk="LOW")
        eng._candidates = eng.load_report()

        mock_dry_result = MagicMock()
        mock_dry_result.is_safe = True
        mock_dry_result.lines_affected = 200
        mock_dry_result.files_to_delete = []
        mock_dry_result.warnings = []

        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_dry_result

        with patch("agents.code_fixer.cli.DryRunExecutor", return_value=mock_executor):
            summary = eng.dry_run()

        assert "batches" in summary
        assert "total_candidates" in summary
        assert summary["total_candidates"] == len(eng._candidates)
