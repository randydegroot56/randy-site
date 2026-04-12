"""Unit tests for ReportGenerator — no mocking needed, just assert output."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.code_fixer.core.report_generator import ReportGenerator


@pytest.fixture
def run_data() -> dict:
    return {
        "run_id": "20260412_143022",
        "started_at": "2026-04-12T14:30:22",
        "finished_at": "2026-04-12T14:45:10",
        "report_input": "phase3_verified.json",
        "risk_filter": "LOW",
        "batch_size": 3,
        "total_candidates": 97,
        "batches_attempted": 33,
        "batches_succeeded": 32,
        "batches_failed": 1,
        "items_fixed": [f"O{i:03d}" for i in range(1, 97)],
        "items_failed": ["U055", "U056", "U057"],
        "lines_removed": 2280,
        "commits": ["abc1234", "def5678"],
        "batches": [
            {
                "batch_num": 1,
                "item_ids": ["O001", "O002", "O003"],
                "status": "success",
                "lines_removed": 45,
                "commit_hash": "abc1234",
                "branch_name": "audit/remove-O001-2026-04-12",
                "error": None,
            }
        ],
    }


class TestWriteJson:
    def test_writes_valid_json(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.json"
        gen.write_json(out)

        data = json.loads(out.read_text())
        assert data["run_id"] == "20260412_143022"
        assert data["batches_succeeded"] == 32
        assert data["lines_removed"] == 2280

    def test_creates_parent_dirs(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "subdir" / "report.json"
        gen.write_json(out)
        assert out.exists()


class TestWriteHtml:
    def test_writes_html_file(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        assert out.exists()

    def test_html_contains_key_metrics(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()

        assert "20260412_143022" in html   # run_id
        assert "2280" in html              # lines_removed
        assert "32" in html               # batches_succeeded
        assert "<!DOCTYPE html>" in html

    def test_html_contains_failed_items(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()
        assert "U055" in html

    def test_html_contains_batch_table(self, tmp_path, run_data):
        gen = ReportGenerator(run_data)
        out = tmp_path / "report.html"
        gen.write_html(out)
        html = out.read_text()
        assert "abc1234" in html
        assert "O001" in html
