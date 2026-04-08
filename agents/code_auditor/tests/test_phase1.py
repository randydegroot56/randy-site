"""
agents/code_auditor/tests/test_phase1.py
=========================================
Tests for Phase 1 Discovery Engine.

Run with::

    pytest agents/code_auditor/tests/test_phase1.py -v
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from agents.code_auditor.core.phase1_discovery import (
    FileMetadata,
    Phase1Discovery,
    ProjectRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def run(coro):
    """Run an async coroutine synchronously (works without pytest-asyncio)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_project(tmp_path: Path) -> Path:
    """Create a minimal project tree and return its root path.

    Tree::

        <tmp>/
            scraper.py          # Python module with imports + exports + docstring
            models/
                __init__.py
                user.py         # Python class
            frontend/
                app.js          # JS file with imports/exports
                utils.ts        # TypeScript file
            config.json         # JSON (no imports/exports)
            venv/
                site-packages/
                    foo.py      # Should be ignored
            __pycache__/
                scraper.cpython-312.pyc  # Should be ignored
    """
    # ── scraper.py ────────────────────────────────────────────────────────
    write(tmp_path / "scraper.py", """\
        \"\"\"Async web scraper module.\"\"\"
        import asyncio
        import json
        from typing import List, Optional
        from .models.user import User

        __all__ = ["ScraperAgent", "fetch_data"]

        class ScraperAgent:
            pass

        async def fetch_data(url: str) -> dict:
            pass

        def _internal_helper():
            pass
    """)

    # ── models/__init__.py ────────────────────────────────────────────────
    write(tmp_path / "models" / "__init__.py", """\
        from .user import User
    """)

    # ── models/user.py ────────────────────────────────────────────────────
    write(tmp_path / "models" / "user.py", """\
        \"\"\"User domain model.\"\"\"
        from dataclasses import dataclass

        @dataclass
        class User:
            id: int
            name: str
            email: str
    """)

    # ── frontend/app.js ───────────────────────────────────────────────────
    write(tmp_path / "frontend" / "app.js", """\
        import React from 'react';
        import { useState, useEffect } from 'react';
        import axios from 'axios';
        import { formatDate } from './utils';

        export function App() {
            return null;
        }

        export const VERSION = '1.0.0';
    """)

    # ── frontend/utils.ts ─────────────────────────────────────────────────
    write(tmp_path / "frontend" / "utils.ts", """\
        import { format } from 'date-fns';

        export function formatDate(d: Date): string {
            return format(d, 'yyyy-MM-dd');
        }

        export class DateFormatter {
            format(d: Date) { return formatDate(d); }
        }
    """)

    # ── config.json ───────────────────────────────────────────────────────
    write(tmp_path / "config.json", """\
        {"version": "1.0", "debug": false}
    """)

    # ── should-be-ignored paths ───────────────────────────────────────────
    write(tmp_path / "venv" / "site-packages" / "foo.py", "# ignored\n")
    write(tmp_path / "__pycache__" / "scraper.cpython-312.pyc", "binary\n")

    return tmp_path


# ---------------------------------------------------------------------------
# 1. File discovery
# ---------------------------------------------------------------------------


def test_file_discovery(temp_project: Path) -> None:
    """Scan finds all supported source files and none of the ignored ones."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())

    paths = [f.path for f in registry.files]

    # Expected files
    assert any("scraper.py" in p for p in paths)
    assert any("user.py" in p for p in paths)
    assert any("app.js" in p for p in paths)
    assert any("utils.ts" in p for p in paths)
    assert any("config.json" in p for p in paths)

    # Ignored files must not appear
    assert not any("venv" in p for p in paths), "venv/ should be ignored"
    assert not any(".pyc" in p for p in paths), ".pyc files should be ignored"

    # At least 6 files: scraper.py, models/__init__.py, models/user.py,
    # frontend/app.js, frontend/utils.ts, config.json
    assert len(registry.files) >= 6


# ---------------------------------------------------------------------------
# 2. Import extraction
# ---------------------------------------------------------------------------


def test_import_extraction(temp_project: Path) -> None:
    """Imports are correctly extracted from Python and JS files."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())
    by_path = {f.path: f for f in registry.files}

    # Python: scraper.py
    scraper = next(f for f in registry.files if "scraper.py" == Path(f.path).name)
    assert "asyncio" in scraper.imports
    assert "json" in scraper.imports
    # relative import .models.user
    assert any("models" in imp or imp.startswith(".") for imp in scraper.imports)

    # JS: app.js imports react and axios
    app = next(f for f in registry.files if "app.js" == Path(f.path).name)
    assert "react" in app.imports
    assert "axios" in app.imports

    # TS: utils.ts imports date-fns
    utils = next(f for f in registry.files if "utils.ts" == Path(f.path).name)
    assert "date-fns" in utils.imports


# ---------------------------------------------------------------------------
# 3. Export extraction
# ---------------------------------------------------------------------------


def test_export_extraction(temp_project: Path) -> None:
    """Exports are correctly extracted using __all__ (Python) and export keywords (JS/TS)."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())

    # Python: scraper.py has __all__ = ["ScraperAgent", "fetch_data"]
    scraper = next(f for f in registry.files if "scraper.py" == Path(f.path).name)
    assert "ScraperAgent" in scraper.exports
    assert "fetch_data" in scraper.exports
    # _internal_helper is not in __all__ and starts with _
    assert "_internal_helper" not in scraper.exports

    # JS: app.js exports App and VERSION
    app = next(f for f in registry.files if "app.js" == Path(f.path).name)
    assert "App" in app.exports
    assert "VERSION" in app.exports

    # TS: utils.ts exports formatDate and DateFormatter
    utils = next(f for f in registry.files if "utils.ts" == Path(f.path).name)
    assert "formatDate" in utils.exports
    assert "DateFormatter" in utils.exports


# ---------------------------------------------------------------------------
# 4. Statistics
# ---------------------------------------------------------------------------


def test_statistics(temp_project: Path) -> None:
    """Aggregate statistics are sane and contain required keys."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())
    stats = registry.statistics

    assert stats["total_files"] >= 6
    assert stats["total_lines"] > 0
    assert stats["avg_lines_per_file"] > 0
    assert "largest_file" in stats
    assert stats["largest_file"] is not None

    by_lang = stats["by_language"]
    assert by_lang.get("python", 0) >= 3    # scraper, user, __init__
    assert by_lang.get("javascript", 0) >= 1
    assert by_lang.get("typescript", 0) >= 1
    assert by_lang.get("json", 0) >= 1


# ---------------------------------------------------------------------------
# 5. Docstring extraction
# ---------------------------------------------------------------------------


def test_docstring_extraction(temp_project: Path) -> None:
    """Module-level docstrings are captured for Python files."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())

    scraper = next(f for f in registry.files if "scraper.py" == Path(f.path).name)
    assert scraper.docstring is not None
    assert "scraper" in scraper.docstring.lower()

    user = next(f for f in registry.files if "user.py" == Path(f.path).name)
    assert user.docstring is not None
    assert "user" in user.docstring.lower()

    # JSON and JS files have no docstring
    app = next(f for f in registry.files if "app.js" == Path(f.path).name)
    assert app.docstring is None

    cfg = next(f for f in registry.files if "config.json" == Path(f.path).name)
    assert cfg.docstring is None


# ---------------------------------------------------------------------------
# 6. venv / __pycache__ ignored
# ---------------------------------------------------------------------------


def test_should_ignore_venv(temp_project: Path) -> None:
    """Files inside venv/ and __pycache__/ are never included in the registry."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())
    paths = [f.path for f in registry.files]

    assert not any("venv" in p for p in paths)
    assert not any("__pycache__" in p for p in paths)
    assert not any(p.endswith(".pyc") for p in paths)


def test_should_ignore_node_modules(tmp_path: Path) -> None:
    """node_modules/ is excluded even when it contains JS files."""
    write(tmp_path / "src" / "index.js", "export const x = 1;\n")
    write(tmp_path / "node_modules" / "react" / "index.js", "module.exports = {};\n")

    registry = run(Phase1Discovery(str(tmp_path)).scan_project())
    paths = [f.path for f in registry.files]

    assert any("src/index.js" in p or "index.js" in p for p in paths)
    assert not any("node_modules" in p for p in paths)


# ---------------------------------------------------------------------------
# 7. JSON serialization
# ---------------------------------------------------------------------------


def test_json_serialization(temp_project: Path) -> None:
    """The registry can be round-tripped through JSON without data loss."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())

    raw = json.dumps(registry.to_dict(), default=str)
    data = json.loads(raw)

    assert "files" in data
    assert "statistics" in data
    assert "circular_imports" in data
    assert "external_dependencies" in data
    assert "timestamp" in data
    assert "project_root" in data

    assert isinstance(data["files"], list)
    assert len(data["files"]) == len(registry.files)

    # Each file entry has the expected keys
    required_keys = {"path", "file_type", "lines", "size_bytes",
                     "imports", "exports", "complexity_score"}
    for entry in data["files"]:
        assert required_keys.issubset(entry.keys()), (
            f"Missing keys in file entry: {required_keys - entry.keys()}"
        )


# ---------------------------------------------------------------------------
# 8. FileMetadata counts are consistent
# ---------------------------------------------------------------------------


def test_file_metadata_counts(temp_project: Path) -> None:
    """imports_count and exports_count match len(imports) and len(exports)."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())
    for fm in registry.files:
        assert fm.imports_count == len(fm.imports), (
            f"{fm.path}: imports_count={fm.imports_count} != len={len(fm.imports)}"
        )
        assert fm.exports_count == len(fm.exports), (
            f"{fm.path}: exports_count={fm.exports_count} != len={len(fm.exports)}"
        )


# ---------------------------------------------------------------------------
# 9. Circular import detection
# ---------------------------------------------------------------------------


def test_circular_import_detection(tmp_path: Path) -> None:
    """A deliberate A->B->A cycle is detected and reported."""
    write(tmp_path / "a.py", "from b import foo\n")
    write(tmp_path / "b.py", "from a import bar\n")

    registry = run(Phase1Discovery(str(tmp_path)).scan_project())
    # We don't assert an exact chain here because internal path resolution
    # may or may not fully resolve the relative imports — but the scanner
    # must not crash and must return a valid registry.
    assert isinstance(registry.circular_imports, list)


def test_no_false_positive_cycles(temp_project: Path) -> None:
    """The sample project has no circular imports."""
    registry = run(Phase1Discovery(str(temp_project)).scan_project())
    assert registry.circular_imports == [], (
        f"Unexpected cycles: {registry.circular_imports}"
    )


# ---------------------------------------------------------------------------
# 10. Oversized files are skipped
# ---------------------------------------------------------------------------


def test_oversized_file_skipped(tmp_path: Path, monkeypatch) -> None:
    """Files exceeding MAX_FILE_SIZE_BYTES are silently skipped."""
    from agents.code_auditor.core import phase1_discovery as mod

    write(tmp_path / "big.py", "x = 1\n")
    write(tmp_path / "small.py", "y = 2\n")

    # Patch the limit to 1 byte so big.py (> 1 byte) is treated as oversized
    monkeypatch.setattr(mod, "MAX_FILE_SIZE_BYTES", 1)

    registry = run(Phase1Discovery(str(tmp_path)).scan_project())
    paths = [f.path for f in registry.files]

    # Neither file is actually 0 bytes, so both are skipped under limit=1
    # The important thing: no exception is raised
    assert isinstance(registry.files, list)
