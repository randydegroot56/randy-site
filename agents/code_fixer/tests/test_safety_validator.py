"""Unit tests for SafetyValidator — all external calls are mocked."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.code_fixer.core.safety_validator import SafetyValidator, ValidationResult


# ── Fixtures ─────────────────────────────────────────────────────────────────

PHASE3_DATA = {
    "scenarios": {
        "scenario_1_safest": {"finding_ids": ["O001", "O002"]},
        "scenario_2_moderate": {"finding_ids": ["O001", "O002", "U001"]},
    },
    "all_checks": [
        {"id": "O001", "risk_level": "LOW", "confidence": 0.99, "file": "old.js", "name": "old", "type": "orphan_file"},
        {"id": "O002", "risk_level": "LOW", "confidence": 0.98, "file": "dead.py", "name": "dead", "type": "orphan_file"},
        {"id": "U001", "risk_level": "MEDIUM", "confidence": 0.90, "file": "theme.js", "name": "useTheme", "type": "unused_export"},
    ],
}


@pytest.fixture
def validator(tmp_path: Path) -> SafetyValidator:
    return SafetyValidator(report_data=PHASE3_DATA, project_root=tmp_path)


# ── Layer 1: validate_report ─────────────────────────────────────────────────

class TestValidateReport:
    def test_passes_when_report_has_all_checks(self, validator):
        result = validator.validate_report()
        assert result.passed is True
        assert result.layer == 1

    def test_fails_when_report_is_empty_dict(self, tmp_path):
        v = SafetyValidator(report_data={}, project_root=tmp_path)
        result = v.validate_report()
        assert result.passed is False
        assert "no findings" in result.message.lower()


# ── Layer 2: validate_git_clean ──────────────────────────────────────────────

class TestValidateGitClean:
    def test_passes_when_tree_is_clean(self, validator):
        with patch.object(validator._git, "is_clean", return_value=True):
            result = validator.validate_git_clean()
        assert result.passed is True
        assert result.layer == 2

    def test_fails_when_tree_is_dirty(self, validator):
        with patch.object(validator._git, "is_clean", return_value=False):
            result = validator.validate_git_clean()
        assert result.passed is False
        assert "dirty" in result.message.lower()


# ── Layer 3: validate_items_exist ────────────────────────────────────────────

class TestValidateItemsExist:
    def test_passes_when_all_ids_present(self, validator):
        result = validator.validate_items_exist(["O001", "O002"])
        assert result.passed is True
        assert result.layer == 3

    def test_fails_with_unknown_id(self, validator):
        result = validator.validate_items_exist(["O001", "U999"])
        assert result.passed is False
        assert "U999" in result.message

    def test_fails_with_empty_list(self, validator):
        result = validator.validate_items_exist([])
        assert result.passed is False


# ── Layer 4: validate_risk_filter ────────────────────────────────────────────

class TestValidateRiskFilter:
    def test_passes_low_items_against_low_threshold(self, validator):
        result = validator.validate_risk_filter(["O001", "O002"], max_risk="LOW")
        assert result.passed is True
        assert result.layer == 4

    def test_fails_medium_item_against_low_threshold(self, validator):
        result = validator.validate_risk_filter(["U001"], max_risk="LOW")
        assert result.passed is False
        assert "U001" in result.message

    def test_passes_medium_item_against_medium_threshold(self, validator):
        result = validator.validate_risk_filter(["U001"], max_risk="MEDIUM")
        assert result.passed is True


# ── Layer 5: validate_batch_dry_run ─────────────────────────────────────────

class TestValidateBatchDryRun:
    def test_passes_when_dry_run_is_safe(self, validator):
        mock_result = MagicMock()
        mock_result.is_safe = True
        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_result

        with patch(
            "agents.code_fixer.core.safety_validator.DryRunExecutor",
            return_value=mock_executor,
        ):
            result = validator.validate_batch_dry_run(["O001"], {}, {})

        assert result.passed is True
        assert result.layer == 5

    def test_fails_when_dry_run_is_not_safe(self, validator):
        mock_result = MagicMock()
        mock_result.is_safe = False
        mock_result.warnings = ["Breaking change detected"]
        mock_executor = MagicMock()
        mock_executor.run_dry_run.return_value = mock_result

        with patch(
            "agents.code_fixer.core.safety_validator.DryRunExecutor",
            return_value=mock_executor,
        ):
            result = validator.validate_batch_dry_run(["O001"], {}, {})

        assert result.passed is False
        assert result.layer == 5


# ── Layer 6: run_baseline_tests ──────────────────────────────────────────────

class TestRunBaselineTests:
    def test_passes_when_tests_pass(self, validator):
        with patch.object(validator._git, "run_tests", return_value=(True, "5 passed")):
            result = validator.run_baseline_tests()
        assert result.passed is True
        assert result.layer == 6

    def test_passes_when_pytest_not_installed(self, validator):
        with patch.object(
            validator._git, "run_tests",
            return_value=(True, "tests skipped — pytest not installed"),
        ):
            result = validator.run_baseline_tests()
        assert result.passed is True

    def test_fails_when_baseline_tests_fail(self, validator):
        with patch.object(
            validator._git, "run_tests", return_value=(False, "3 failed, 2 passed")
        ):
            result = validator.run_baseline_tests()
        assert result.passed is False
        assert result.layer == 6
