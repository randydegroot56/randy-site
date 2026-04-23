"""Tests for ScaffoldValidator."""
import json
import pytest
from pathlib import Path
from agents.scaffolder.validator import ScaffoldValidator, ValidationResult


def _write_manifest(tmp_path: Path, files: list[dict]) -> None:
    manifest = {"spec_id": "spec_001", "files": files}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_all_present_returns_ok(tmp_path):
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "main.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is True
    assert result.missing == []
    assert result.empty == []


def test_missing_file_detected(tmp_path):
    _write_manifest(tmp_path, [{"relative_path": "missing.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert "missing.py" in result.missing


def test_empty_file_with_header_true_flagged(tmp_path):
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "main.py", "header": True}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert "main.py" in result.empty


def test_empty_file_with_header_false_not_flagged(tmp_path):
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    _write_manifest(tmp_path, [{"relative_path": "README.md", "header": False}])
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is True


def test_missing_manifest_returns_not_ok(tmp_path):
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert any("manifest.json" in w for w in result.warnings)


def test_corrupt_manifest_returns_not_ok(tmp_path):
    (tmp_path / "manifest.json").write_text("not {{ valid json", encoding="utf-8")
    result = ScaffoldValidator().validate(tmp_path)
    assert result.ok is False
    assert any("could not be parsed" in w for w in result.warnings)


def test_never_raises_for_nonexistent_dir(tmp_path):
    result = ScaffoldValidator().validate(tmp_path / "does_not_exist")
    assert isinstance(result, ValidationResult)
    assert result.ok is False
