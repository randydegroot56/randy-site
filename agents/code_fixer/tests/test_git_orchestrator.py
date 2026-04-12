"""Unit tests for GitOrchestrator — all git calls are mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from agents.code_fixer.core.git_orchestrator import GitOrchestrator


@pytest.fixture
def orch(tmp_path: Path) -> GitOrchestrator:
    return GitOrchestrator(project_root=tmp_path)


def _mock_run(stdout: str = "", returncode: int = 0):
    """Helper: return a mock CompletedProcess."""
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = ""
    return m


# ── is_clean ────────────────────────────────────────────────────────────────

class TestIsClean:
    def test_returns_true_when_no_changes(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(stdout="")) as mock_run:
            assert orch.is_clean() is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:3] == ["git", "status", "--porcelain"]

    def test_returns_false_when_dirty(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(stdout=" M file.py")):
            assert orch.is_clean() is False


# ── current_branch ───────────────────────────────────────────────────────────

class TestCurrentBranch:
    def test_returns_branch_name(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="main")):
            assert orch.current_branch() == "main"

    def test_strips_whitespace(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="  feature/x  \n")):
            assert orch.current_branch() == "feature/x"


# ── commit_batch ─────────────────────────────────────────────────────────────

class TestCommitBatch:
    def test_stages_and_commits(self, orch):
        responses = [
            _mock_run(),                # git add -A
            _mock_run(),                # git commit
            _mock_run(stdout="abc1234"),# git rev-parse HEAD
        ]
        with patch("subprocess.run", side_effect=responses):
            result = orch.commit_batch("fix: remove U010, U011")
        assert result == "abc1234"

    def test_raises_on_commit_failure(self, orch):
        responses = [
            _mock_run(),                          # git add -A
            _mock_run(returncode=1, stdout=""),   # git commit fails
        ]
        with patch("subprocess.run", side_effect=responses):
            with pytest.raises(RuntimeError, match="git commit failed"):
                orch.commit_batch("fix: test")


# ── cleanup_branch ───────────────────────────────────────────────────────────

class TestCleanupBranch:
    def test_checks_out_main_and_deletes_branch(self, orch):
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return _mock_run()

        with patch("subprocess.run", side_effect=fake_run):
            orch.cleanup_branch("audit/remove-U010-2026-04-12")

        assert ["git", "checkout", "main"] in calls
        assert ["git", "branch", "-D", "audit/remove-U010-2026-04-12"] in calls


# ── merge_to_main ────────────────────────────────────────────────────────────

class TestMergeToMain:
    def test_checks_out_main_and_merges(self, orch):
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return _mock_run()

        with patch("subprocess.run", side_effect=fake_run):
            orch.merge_to_main("audit/remove-U010-2026-04-12")

        assert ["git", "checkout", "main"] in calls
        assert any("merge" in c for c in calls)


# ── list_audit_branches ──────────────────────────────────────────────────────

class TestListAuditBranches:
    def test_returns_matching_branches(self, orch):
        branch_output = "  audit/remove-U010-2026-04-12\n  main\n  audit/remove-U020-2026-04-12\n"
        with patch("subprocess.run", return_value=_mock_run(stdout=branch_output)):
            result = orch.list_audit_branches()
        assert result == ["audit/remove-U010-2026-04-12", "audit/remove-U020-2026-04-12"]

    def test_returns_empty_list_when_none(self, orch):
        with patch("subprocess.run", return_value=_mock_run(stdout="  main\n")):
            assert orch.list_audit_branches() == []


# ── run_tests ────────────────────────────────────────────────────────────────

class TestRunTests:
    def test_returns_true_when_pytest_passes(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(returncode=0, stdout="5 passed")):
            passed, output = orch.run_tests()
        assert passed is True
        assert "passed" in output

    def test_returns_false_when_pytest_fails(self, orch, tmp_path):
        with patch("subprocess.run", return_value=_mock_run(returncode=1, stdout="1 failed")):
            passed, output = orch.run_tests()
        assert passed is False

    def test_returns_true_when_pytest_not_installed(self, orch, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError("pytest not found")):
            passed, output = orch.run_tests()
        assert passed is True
        assert "skipped" in output.lower()
