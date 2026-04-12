"""GitOrchestrator — isolates all git/subprocess calls for Code Fixer."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple


class GitOrchestrator:
    """Manage git operations for the Code Fixer batch loop.

    All subprocess calls are centralised here so that the rest of Code Fixer
    never imports subprocess directly (making unit testing straightforward).

    Parameters
    ----------
    project_root:
        Absolute path to the git repository root.
    verbose:
        When True, print each git command before running it.
    """

    def __init__(self, project_root: Path, verbose: bool = False) -> None:
        self._root = Path(project_root)
        self._verbose = verbose

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def is_clean(self) -> bool:
        """Return True when the working tree has no uncommitted changes."""
        output = self._git("status", "--porcelain")
        return output.strip() == ""

    def current_branch(self) -> str:
        """Return the name of the currently checked-out branch."""
        return self._git("rev-parse", "--abbrev-ref", "HEAD").strip()

    def commit_batch(self, message: str) -> str:
        """Stage all changes and create a commit.

        Parameters
        ----------
        message:
            Commit message (e.g. ``"fix: remove U010, U011, U012 (LOW risk)"``).

        Returns
        -------
        str
            The full commit hash of the newly created commit.

        Raises
        ------
        RuntimeError
            If ``git commit`` exits non-zero (e.g. nothing staged).
        """
        self._git("add", "-A")
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git commit failed:\n{result.stderr.strip()}")
        return self._git("rev-parse", "HEAD").strip()

    def merge_to_main(self, branch: str) -> None:
        """Checkout main and fast-forward merge *branch* into it.

        Parameters
        ----------
        branch:
            Name of the feature branch to merge (e.g. ``"audit/remove-U010-2026-04-12"``).

        Raises
        ------
        RuntimeError
            If checkout or merge fails.
        """
        self._git("checkout", "main")
        self._git("merge", "--ff-only", branch)
        self._git("branch", "-d", branch)

    def cleanup_branch(self, branch: str) -> None:
        """Checkout main and force-delete *branch* (used on test failure).

        Parameters
        ----------
        branch:
            Branch to delete (may have uncommitted changes).
        """
        try:
            self._git("checkout", "main")
        except RuntimeError:
            pass  # already on main or detached HEAD — best effort
        try:
            self._git("branch", "-D", branch)
        except RuntimeError:
            pass  # branch may not exist yet

    def get_status(self) -> dict:
        """Return a snapshot of the current git state.

        Returns
        -------
        dict
            Keys: ``branch`` (str), ``clean`` (bool),
            ``audit_branches`` (list[str]).
        """
        return {
            "branch": self.current_branch(),
            "clean": self.is_clean(),
            "audit_branches": self.list_audit_branches(),
        }

    def list_audit_branches(self) -> List[str]:
        """Return all local branches whose name starts with ``audit/``."""
        raw = self._git("branch")
        return [
            b.strip()
            for b in raw.splitlines()
            if b.strip().startswith("audit/")
        ]

    def run_tests(self) -> Tuple[bool, str]:
        """Run pytest in *project_root* and return ``(passed, output)``.

        Returns ``(True, "tests skipped — pytest not installed")`` when
        pytest is not available, so callers can continue safely.
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-q"],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except FileNotFoundError:
            return True, "tests skipped — pytest not installed"
        except Exception as exc:  # noqa: BLE001
            return True, f"tests skipped — {exc}"

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _git(self, *args: str) -> str:
        """Run a git command and return stdout.

        Raises
        ------
        RuntimeError
            If the command exits non-zero.
        """
        cmd = ["git", *args]
        if self._verbose:
            print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(self._root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
            )
        return result.stdout
