"""Tests for agents.test_generator.validator.TestValidator."""
import pytest
from pathlib import Path
from agents.test_generator.validator import TestValidator, ValidationResult


@pytest.fixture
def validator():
    return TestValidator()


def test_validate_missing_file(tmp_path, validator):
    result = validator.validate(tmp_path / "nonexistent.py")
    assert result.syntax_ok is False
    assert "not found" in result.output.lower()


def test_validate_syntax_ok_for_valid_python(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text("import pytest\ndef test_pass():\n    pass\n")
    result = validator.validate(f)
    assert result.syntax_ok is True


def test_validate_syntax_error_detected(tmp_path, validator):
    f = tmp_path / "test_bad.py"
    f.write_text("def broken(\n")
    result = validator.validate(f)
    assert result.syntax_ok is False


def test_validate_detects_missing_import(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text("import _no_such_module_xyz\ndef test_pass():\n    pass\n")
    result = validator.validate(f)
    assert "_no_such_module_xyz" in result.missing_imports


def test_validate_no_false_positives_for_stdlib(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text("import os\nimport pathlib\ndef test_pass():\n    pass\n")
    result = validator.validate(f)
    assert "os" not in result.missing_imports
    assert "pathlib" not in result.missing_imports


def test_validate_run_passes_test(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text("def test_always_passes():\n    assert 1 + 1 == 2\n")
    result = validator.validate(f)
    assert result.passed >= 1
    assert result.failed == 0


def test_validate_tdd_pending_reclassified(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text(
        "import pytest\n"
        "def test_tdd_red():\n"
        "    pytest.fail('Not implemented yet — TDD red phase')\n"
    )
    result = validator.validate(f)
    # The failed test should be reclassified as pending
    assert result.pending >= 1
    assert result.failed == 0


def test_validate_returns_validation_result_type(tmp_path, validator):
    f = tmp_path / "test_foo.py"
    f.write_text("def test_ok():\n    pass\n")
    result = validator.validate(f)
    assert isinstance(result, ValidationResult)
    assert result.path == f
