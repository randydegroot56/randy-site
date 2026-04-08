"""
agents/code_auditor/utils/file_helpers.py
==========================================
Helper functions used across all phases of the Code Auditor.

Usage::

    from agents.code_auditor.utils.file_helpers import (
        should_scan_file, get_file_type, read_file_safe,
        get_relative_path, format_file_size, get_complexity_score,
        extract_first_docstring,
    )

    if should_scan_file(path, config):
        content = read_file_safe(path)
        rel_path = get_relative_path(path, root)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from agents.code_auditor.core.config import Phase1Config


# ---------------------------------------------------------------------------
# File filtering
# ---------------------------------------------------------------------------


def should_scan_file(path: Path, config: Phase1Config) -> bool:
    """Return ``True`` if the file should be scanned based on config rules.

    Checks the file name against ``config.IGNORE_FILES`` patterns and verifies
    the extension is in ``config.SUPPORTED_EXTENSIONS``.  Never raises — any
    exception (e.g. on a path that cannot be normalised) causes the function to
    return ``False`` so callers can always iterate safely.

    Parameters
    ----------
    path:
        Absolute or relative path to the candidate file.
    config:
        A ``Phase1Config`` (or subclass) instance that provides the ignore
        patterns and the supported-extension set.
    """
    try:
        if config.is_ignored_file(path.name):
            return False
        if not config.is_supported(path.name):
            return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

_EXT_TO_TYPE: dict[str, str] = {
    ".py":   "python",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".json": "json",
}


def get_file_type(path: Path) -> str:
    """Return a normalised language label for a file based on its extension.

    Returns one of ``"python"``, ``"javascript"``, ``"typescript"``,
    ``"json"``, or ``"unknown"``.

    Parameters
    ----------
    path:
        Path whose suffix is inspected.
    """
    return _EXT_TO_TYPE.get(path.suffix.lower(), "unknown")


# ---------------------------------------------------------------------------
# Safe file I/O
# ---------------------------------------------------------------------------


def read_file_safe(
    path: Path,
    max_size_bytes: int = 50 * 1024 * 1024,
) -> Optional[str]:
    """Read a text file and return its content, or ``None`` if it should be skipped.

    Skips the file (returns ``None``) when:

    * The file does not exist or is not a regular file.
    * Its size exceeds *max_size_bytes* (default: 50 MB).

    Encoding errors are silently ignored (``errors='ignore'``), so the returned
    string may contain replacement characters for invalid byte sequences.

    Parameters
    ----------
    path:
        Path to the file to read.
    max_size_bytes:
        Maximum allowed file size in bytes.  Files larger than this are
        skipped to prevent memory spikes.
    """
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > max_size_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------


def get_relative_path(path: Path, root: Path) -> str:
    """Return the path of *path* relative to *root* using forward slashes.

    Always produces a POSIX-style string (``src/app/page.js``) regardless of
    the host platform, making paths safe to embed in reports and JSON output.

    If *path* is not under *root* the absolute path is returned as-is (with
    forward slashes normalised).

    Parameters
    ----------
    path:
        The target file path.
    root:
        The project root to compute the relative path from.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def format_file_size(bytes_: int) -> str:
    """Return a human-readable file-size string.

    Converts an integer byte count to the most appropriate unit.

    Examples
    --------
    >>> format_file_size(500)
    '500 B'
    >>> format_file_size(2048)
    '2 KB'
    >>> format_file_size(1_048_576)
    '1 MB'
    >>> format_file_size(1_572_864)
    '1.5 MB'
    """
    if bytes_ < 1024:
        return f"{bytes_} B"
    kb = bytes_ / 1024
    if kb < 1024:
        return f"{kb:.0f} KB" if kb == int(kb) else f"{kb:.1f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.0f} MB" if mb == int(mb) else f"{mb:.1f} MB"
    gb = mb / 1024
    return f"{gb:.0f} GB" if gb == int(gb) else f"{gb:.1f} GB"


# ---------------------------------------------------------------------------
# Complexity scoring
# ---------------------------------------------------------------------------


def get_complexity_score(num_functions: int, num_classes: int) -> float:
    """Return a simple complexity score for a file.

    Classes are weighted more heavily than standalone functions because they
    typically represent more structural complexity.  The score is intentionally
    unit-free — use it for relative comparisons within a codebase.

    Score = num_functions + num_classes * 2

    Parameters
    ----------
    num_functions:
        Number of top-level (or nested) function definitions detected.
    num_classes:
        Number of class definitions detected.
    """
    return float(num_functions + num_classes * 2)


# ---------------------------------------------------------------------------
# Docstring extraction
# ---------------------------------------------------------------------------

_DOCSTRING_RE = re.compile(
    r'''(?:^|\n)\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')''',
    re.DOTALL,
)


def extract_first_docstring(lines: List[str]) -> Optional[str]:
    """Return the first module-level docstring found within the first 20 lines.

    Handles both ``\"\"\"triple-double-quote\"\"\"`` and
    ``'''triple-single-quote'''`` styles.  The returned string is stripped of
    leading/trailing whitespace.  Returns ``None`` if no docstring is found.

    Parameters
    ----------
    lines:
        The file content split into individual lines (e.g. from
        ``content.splitlines()``).  Only the first 20 lines are inspected.
    """
    snippet = "\n".join(lines[:20])
    match = _DOCSTRING_RE.search(snippet)
    if match:
        content = match.group(1) if match.group(1) is not None else match.group(2)
        return content.strip() or None
    return None
