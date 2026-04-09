"""
agents/code_auditor/core/phase2_detection.py
=============================================
Phase 2 Detection Engine -- finds unused exports, dead code, and other
code-quality issues from a Phase 1 JSON report.

Usage::

    from agents.code_auditor.core.phase2_detection import UnusedExportFinder

    with open("audit_report.json") as f:
        report = json.load(f)

    finder = UnusedExportFinder(report, verbose=True)
    findings = finder.find_unused_exports()
    for f in findings:
        print(f["id"], f["file"], f["item"], f["confidence"])
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class UnusedExportFinding:
    """A single unused-export finding.

    Attributes
    ----------
    id:
        Sequential identifier, e.g. ``"U001"``.
    type:
        Always ``"unused_export"``.
    file:
        Project-relative path of the file that declares the export.
    item:
        Name of the exported symbol (function, class, or variable).
    reason:
        Human-readable explanation of why the item is flagged.
    confidence:
        Probability estimate (0.0-1.0) that the item is genuinely unused.
        Higher = more confident the item can be removed safely.
    risk:
        Removal risk level derived from confidence:
        ``"LOW"`` (confident it's unused) → ``"MEDIUM"`` → ``"HIGH"``
        (less certain; verify before deleting).
    evidence:
        Supporting data used to compute confidence.
    """

    id: str
    type: str
    file: str
    item: str
    reason: str
    confidence: float
    risk: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Finder
# ---------------------------------------------------------------------------


class UnusedExportFinder:
    """Scan a Phase 1 report for exports that are never imported anywhere.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    verbose:
        When ``True``, print progress messages to stdout.
    """

    def __init__(self, phase1_report: Dict[str, Any], verbose: bool = False) -> None:
        self._report = phase1_report
        self.verbose = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_unused_exports(self) -> List[Dict[str, Any]]:
        """Return a list of unused-export findings as plain dicts.

        Each dict matches the :class:`UnusedExportFinding` structure and is
        safe to serialise directly to JSON.

        The method is deterministic: findings are ordered by file path then
        by export name, and IDs are assigned sequentially starting at
        ``"U001"``.
        """
        # Pre-build a cross-reference of every symbol imported across the
        # project so we can answer "who imports X?" in O(1).
        usage_map  = self._build_usage_map()
        test_files = self._collect_test_files()

        findings: List[UnusedExportFinding] = []
        counter = 1

        for file_entry in sorted(self._files, key=lambda f: f.get("path", "")):
            path      = file_entry.get("path", "")
            exports   = file_entry.get("exports", [])
            file_type = file_entry.get("file_type", "unknown")

            if not exports:
                continue

            # Test files themselves are never flagged
            if self._is_test_file(path):
                continue

            complexity  = float(file_entry.get("complexity_score", 0))
            last_mod    = file_entry.get("last_modified", "")
            days_old    = self._days_old(last_mod)
            is_init     = Path(path).name == "__init__.py"
            init_export_count = len(exports)

            for export_name in exports:
                # ── Safety gates ──────────────────────────────────────────
                if self._should_skip(
                    export_name,
                    path,
                    is_init,
                    init_export_count,
                    usage_map,
                ):
                    continue

                # ── Evidence ──────────────────────────────────────────────
                usage_count   = usage_map.get(export_name, {}).get("count", 0)
                test_coverage = usage_map.get(export_name, {}).get("tested", False)

                evidence: Dict[str, Any] = {
                    "usage_count":   usage_count,
                    "test_coverage": test_coverage,
                    "last_modified": last_mod,
                    "days_old":      days_old,
                    "is_dunder":     self._is_dunder(export_name),
                    "is_private":    export_name.startswith("_"),
                }

                # ── Confidence ────────────────────────────────────────────
                confidence = self._compute_confidence(
                    days_old, test_coverage, complexity
                )

                # ── Risk ──────────────────────────────────────────────────
                risk = self._assign_risk(confidence)

                # ── Reason ────────────────────────────────────────────────
                reason = self._build_reason(
                    usage_count, days_old, test_coverage, path
                )

                finding = UnusedExportFinding(
                    id=f"U{counter:03d}",
                    type="unused_export",
                    file=path,
                    item=export_name,
                    reason=reason,
                    confidence=round(confidence, 4),
                    risk=risk,
                    evidence=evidence,
                )
                findings.append(finding)
                counter += 1

                self._log(
                    f"  [{finding.risk:6s}] {path}::{export_name} "
                    f"(conf={finding.confidence:.2f})"
                )

        self._log(f"UnusedExportFinder: {len(findings)} finding(s).")
        return [f.to_dict() for f in findings]

    # ------------------------------------------------------------------
    # Cross-reference builder
    # ------------------------------------------------------------------

    def _build_usage_map(self) -> Dict[str, Dict[str, Any]]:
        """Return a mapping ``symbol_name -> {count, tested}`` across all files.

        ``count`` is the number of distinct files that name the symbol in
        their import list.  ``tested`` is ``True`` if at least one test file
        imports it.

        Note: Phase 1 import lists contain module paths, not individual
        symbol names, so we resolve at the symbol level by scanning every
        file's ``imports`` list for the bare name of each exported symbol
        from every other file.
        """
        # Collect all export name -> declaring-file pairs
        all_exports: Dict[str, str] = {}
        for f in self._files:
            for exp in f.get("exports", []):
                # If a name is exported by multiple files, last one wins for
                # usage counting purposes (conservative).
                all_exports[exp] = f.get("path", "")

        usage: Dict[str, Dict[str, Any]] = {
            name: {"count": 0, "tested": False}
            for name in all_exports
        }

        for file_entry in self._files:
            importer  = file_entry.get("path", "")
            is_test   = self._is_test_file(importer)
            imports   = file_entry.get("imports", [])

            for imp in imports:
                # An import string might be a bare name ("utils"), a dotted
                # path ("agents.scraper"), or a relative path; we check
                # whether any exported name appears as the last segment.
                last_seg = imp.split(".")[-1].split("/")[-1].lstrip("_")

                for export_name in list(usage.keys()):
                    if export_name == imp or export_name == last_seg:
                        declaring_file = all_exports.get(export_name, "")
                        if importer != declaring_file:
                            usage[export_name]["count"] += 1
                            if is_test:
                                usage[export_name]["tested"] = True

        return usage

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_test_files(self) -> Set[str]:
        """Return the set of paths that are test files."""
        return {
            f["path"]
            for f in self._files
            if self._is_test_file(f.get("path", ""))
        }

    @staticmethod
    def _is_test_file(path: str) -> bool:
        name = Path(path).name
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in path.replace("\\", "/")
            or "/test/" in path.replace("\\", "/")
        )

    @staticmethod
    def _is_dunder(name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    @staticmethod
    def _days_old(last_modified: str) -> int:
        """Return the number of days since *last_modified* (ISO-8601 string).

        Returns 0 on any parse error rather than crashing.
        """
        if not last_modified:
            return 0
        try:
            # Handle both offset-aware and naive timestamps
            ts = datetime.fromisoformat(last_modified)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - ts
            return max(0, delta.days)
        except (ValueError, OverflowError):
            return 0

    def _should_skip(
        self,
        name: str,
        path: str,
        is_init: bool,
        init_export_count: int,
        usage_map: Dict[str, Dict[str, Any]],
    ) -> bool:
        """Return ``True`` if this export should be excluded from findings."""

        # Used somewhere
        if usage_map.get(name, {}).get("count", 0) > 0:
            return True

        # Dunder names (__all__, __version__, __author__, ...)
        if self._is_dunder(name):
            return True

        # Private symbols (single underscore prefix)
        if name.startswith("_"):
            return True

        # __init__.py files with few exports often act as re-export hubs;
        # skip them to avoid noise (Phase 2 reachability will catch real orphans).
        if is_init and init_export_count <= 5:
            return True

        # Legacy / deprecated items should be removed by a human, not flagged
        # as "unused" -- they are intentionally kept for compat.
        lower = name.lower()
        if "legacy" in lower or "deprecated" in lower:
            return True

        # Test files never flag their own exports
        if self._is_test_file(path):
            return True

        return False

    @staticmethod
    def _compute_confidence(
        days_old: int,
        test_coverage: bool,
        complexity: float,
    ) -> float:
        """Return a confidence score in [0.0, 0.99] that the export is unused.

        Scoring
        -------
        Base score                        0.70
        + 0.15  if days_old > 180         (stale code = more likely dead)
        + 0.10  if no test coverage       (untested = riskier to delete, but
                                           also more likely nobody uses it)
        + 0.05  if complexity_score > 10  (large files accumulate dead code)
        Cap at 0.99 (never 100% certain)
        """
        score = 0.70
        if days_old > 180:
            score += 0.15
        if not test_coverage:
            score += 0.10
        if complexity > 10:
            score += 0.05
        return min(score, 0.99)

    @staticmethod
    def _assign_risk(confidence: float) -> str:
        """Map a confidence score to a removal-risk label.

        Higher confidence that the export is unused -> lower removal risk.

        Thresholds
        ----------
        confidence > 0.85  -> "LOW"    (safe to investigate for removal)
        0.60 < conf <= 0.85 -> "MEDIUM" (verify before removing)
        conf <= 0.60        -> "HIGH"   (do not remove without manual review)
        """
        if confidence > 0.85:
            return "LOW"
        if confidence > 0.60:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _build_reason(
        usage_count: int,
        days_old: int,
        test_coverage: bool,
        file_path: str,
    ) -> str:
        """Compose a concise human-readable reason string."""
        parts: List[str] = []

        if usage_count == 0:
            parts.append("0 imports")

        if days_old > 0:
            if days_old >= 365:
                years = days_old // 365
                parts.append(f"{years} year{'s' if years > 1 else ''} old")
            elif days_old >= 30:
                months = days_old // 30
                parts.append(f"{months} month{'s' if months > 1 else ''} old")
            else:
                parts.append(f"{days_old} days old")

        if not test_coverage:
            parts.append("no tests")

        return ", ".join(parts) if parts else "Exported but no internal usage"

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Orphan file data model
# ---------------------------------------------------------------------------


@dataclass
class OrphanFileFinding:
    """A single orphan-file finding.

    Attributes
    ----------
    id:
        Sequential identifier, e.g. ``"O001"``.
    type:
        Always ``"orphan_file"``.
    file:
        Project-relative path of the candidate orphan.
    reason:
        Human-readable explanation of why the file is flagged.
    confidence:
        Probability estimate (0.0-1.0) that the file is genuinely orphaned.
    risk:
        Removal risk level:
        ``"LOW"`` (confident it's orphaned) -> ``"MEDIUM"`` -> ``"HIGH"``.
    evidence:
        Supporting data used to compute confidence.
    """

    id: str
    type: str
    file: str
    reason: str
    confidence: float
    risk: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Orphan file finder
# ---------------------------------------------------------------------------

# Entry-point filenames that are never imported but are valid roots.
_ENTRY_POINT_NAMES: Set[str] = {
    "main.py", "app.py", "wsgi.py", "asgi.py", "manage.py",
    "server.py", "run.py", "start.py", "index.py",
}

# Config-like path fragments that make a file exempt from orphan detection.
_CONFIG_FRAGMENTS: Set[str] = {
    "config", "settings", "constants", "env", "setup",
}


class OrphanFileFinder:
    """Scan a Phase 1 report for files that nothing else imports.

    A file is an orphan candidate when its ``incoming_imports`` count is zero
    AND it passes a set of safety gates that exclude well-known entry points,
    test/config files, and trivially small placeholders.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    verbose:
        When ``True``, print progress messages to stdout.
    """

    def __init__(self, phase1_report: Dict[str, Any], verbose: bool = False) -> None:
        self._report = phase1_report
        self.verbose = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_orphan_files(self) -> List[Dict[str, Any]]:
        """Return a list of orphan-file findings as plain dicts.

        Findings are ordered by file path and IDs are assigned sequentially
        starting at ``"O001"``.
        """
        incoming = self._build_incoming_map()
        findings: List[OrphanFileFinding] = []
        counter = 1

        for file_entry in sorted(self._files, key=lambda f: f.get("path", "")):
            path      = file_entry.get("path", "")
            size      = int(file_entry.get("size_bytes", 0))
            lines     = int(file_entry.get("lines", 0))
            exports   = file_entry.get("exports", [])

            # ── Derive boolean flags ──────────────────────────────────────
            has_main     = self._has_main_block(file_entry)
            is_test      = self._is_test_file(path)
            is_config    = self._is_config_file(path)
            in_count     = incoming.get(path, 0)

            # ── Safety gates ──────────────────────────────────────────────
            if self._should_skip(path, size, has_main):
                continue

            # Core orphan criterion: nothing imports this file
            if in_count > 0:
                continue

            # ── Evidence ──────────────────────────────────────────────────
            evidence: Dict[str, Any] = {
                "incoming_imports": in_count,
                "file_size":        size,
                "lines":            lines,
                "exports":          list(exports),
                "has_main":         has_main,
                "is_test_file":     is_test,
                "is_config_file":   is_config,
            }

            # ── Confidence ────────────────────────────────────────────────
            last_mod   = file_entry.get("last_modified", "")
            days_old   = self._days_old(last_mod)
            confidence = self._compute_confidence(
                in_count, lines, len(exports), days_old, has_main
            )

            # ── Risk ──────────────────────────────────────────────────────
            risk = self._assign_risk(confidence)

            # ── Reason ────────────────────────────────────────────────────
            reason = self._build_reason(in_count, lines, exports)

            finding = OrphanFileFinding(
                id=f"O{counter:03d}",
                type="orphan_file",
                file=path,
                reason=reason,
                confidence=round(confidence, 4),
                risk=risk,
                evidence=evidence,
            )
            findings.append(finding)
            counter += 1

            self._log(
                f"  [{finding.risk:6s}] {path} "
                f"(incoming={in_count}, conf={finding.confidence:.2f})"
            )

        self._log(f"OrphanFileFinder: {len(findings)} finding(s).")
        return [f.to_dict() for f in findings]

    # ------------------------------------------------------------------
    # Incoming-import map
    # ------------------------------------------------------------------

    def _build_incoming_map(self) -> Dict[str, int]:
        """Return ``{file_path: number_of_files_that_import_it}``.

        Uses the ``dep_graph`` key when present in the report (produced by
        Phase1Discovery).  Falls back to a best-effort heuristic that checks
        each file's import strings against known file stems.
        """
        dep_graph: Optional[Dict[str, List[str]]] = self._report.get("dep_graph")

        if dep_graph:
            # dep_graph maps importer -> [importee, ...]
            incoming: Dict[str, int] = {f["path"]: 0 for f in self._files}
            for importees in dep_graph.values():
                for importee in importees:
                    if importee in incoming:
                        incoming[importee] += 1
            return incoming

        # Fallback: resolve raw import strings against known file paths.
        # Build two lookups: full dotted path (preferred) and bare stem
        # (fallback).  Prefer the full key so "utils.helpers" resolves to
        # "utils/helpers.py" rather than matching any file named helpers.py.
        dotted_to_path: Dict[str, str] = {}
        stem_to_path: Dict[str, str] = {}
        for f in self._files:
            p = Path(f["path"])
            dotted = p.with_suffix("").as_posix().replace("/", ".")
            dotted_to_path[dotted] = f["path"]
            # Only register the bare stem when unambiguous (no collision)
            stem = p.stem
            if stem not in stem_to_path:
                stem_to_path[stem] = f["path"]
            else:
                # Ambiguous stem: remove it so we never misresolve
                stem_to_path.pop(stem, None)

        incoming: Dict[str, int] = {f["path"]: 0 for f in self._files}
        for file_entry in self._files:
            importer = file_entry.get("path", "")
            for imp in file_entry.get("imports", []):
                clean = imp.lstrip(".")
                # Try full dotted path first, then bare stem
                target = dotted_to_path.get(clean) or stem_to_path.get(
                    clean.split(".")[-1].split("/")[-1]
                )
                if target and target != importer:
                    incoming[target] += 1

        return incoming

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_main_block(file_entry: Dict[str, Any]) -> bool:
        """Return ``True`` if the file entry indicates a ``__main__`` block.

        Phase1Discovery doesn't store raw content, so we rely on the
        ``has_main`` flag if present, then fall back to checking the export
        list for ``"__main__"`` as a heuristic.
        """
        if "has_main" in file_entry:
            return bool(file_entry["has_main"])
        # Heuristic: CLI entry-point files often export a ``main`` symbol
        exports = file_entry.get("exports", [])
        return "main" in exports or "__main__" in exports

    @staticmethod
    def _is_test_file(path: str) -> bool:
        posix = path.replace("\\", "/")
        name  = Path(path).name
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in posix
            or "/test/" in posix
            or "/spec/" in posix
        )

    @staticmethod
    def _is_config_file(path: str) -> bool:
        posix = path.replace("\\", "/").lower()
        name  = Path(path).stem.lower()
        return any(frag in name or frag in posix for frag in _CONFIG_FRAGMENTS)

    @staticmethod
    def _days_old(last_modified: str) -> int:
        if not last_modified:
            return 0
        try:
            ts = datetime.fromisoformat(last_modified)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return max(0, (datetime.now(timezone.utc) - ts).days)
        except (ValueError, OverflowError):
            return 0

    def _should_skip(self, path: str, size_bytes: int, has_main: bool) -> bool:
        """Return ``True`` if this file should be excluded from findings."""
        name  = Path(path).name
        posix = path.replace("\\", "/").lower()

        # __init__.py files are intentionally not imported by name
        if name == "__init__.py":
            return True

        # Known entry-point filenames
        if name in _ENTRY_POINT_NAMES:
            return True

        # Test / spec files
        if self._is_test_file(path):
            return True

        # Config / settings files
        if self._is_config_file(path):
            return True

        # conftest.py (pytest fixtures)
        if name == "conftest.py":
            return True

        # .config.py suffix
        if name.endswith(".config.py"):
            return True

        # Dunder modules (__version__.py, __about__.py, ...)
        if name.startswith("__") and name.endswith("__.py"):
            return True

        # Very small files are likely placeholders or stubs
        if size_bytes < 100:
            return True

        # Files with a __main__ block are entry points, not orphans
        if has_main:
            return True

        return False

    @staticmethod
    def _compute_confidence(
        incoming: int,
        lines: int,
        export_count: int,
        days_old: int,
        has_main: bool,
    ) -> float:
        """Return a confidence score in [0.0, 0.95].

        Scoring
        -------
        Base                          0.50
        + 0.30  incoming == 0         (core indicator)
        + 0.10  lines < 500           (small files are more likely throwaway)
        + 0.10  export_count < 2      (little public surface)
        + 0.05  days_old > 365        (stale)
        - 0.20  has_main              (entry-point evidence)
        Cap at 0.95
        """
        score = 0.50
        if incoming == 0:
            score += 0.30
        if lines < 500:
            score += 0.10
        if export_count < 2:
            score += 0.10
        if days_old > 365:
            score += 0.05
        if has_main:
            score -= 0.20
        return min(max(score, 0.0), 0.95)

    @staticmethod
    def _assign_risk(confidence: float) -> str:
        """Map confidence to removal-risk label.

        confidence > 0.80  -> "LOW"
        0.50 < conf <= 0.80 -> "MEDIUM"
        conf <= 0.50        -> "HIGH"
        """
        if confidence > 0.80:
            return "LOW"
        if confidence > 0.50:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _build_reason(
        incoming: int,
        lines: int,
        exports: List[str],
    ) -> str:
        parts: List[str] = []

        if incoming == 0:
            parts.append("no incoming imports")
        else:
            parts.append(f"only {incoming} import(s)")

        if lines < 100:
            parts.append("very small file")
        elif lines < 500:
            parts.append("small utility")

        if not exports:
            parts.append("nothing exported")
        elif len(exports) == 1:
            parts.append(f"single export ({exports[0]})")

        return ", ".join(parts) if parts else "Isolated module with no incoming imports"

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Unused import data model
# ---------------------------------------------------------------------------


@dataclass
class UnusedImportFinding:
    """A single unused-import finding.

    Attributes
    ----------
    id:
        Sequential identifier, e.g. ``"I001"``.
    type:
        Always ``"unused_import"``.
    file:
        Project-relative path of the file that contains the import.
    item:
        The imported module / symbol name as it appears in the source.
    reason:
        Human-readable explanation.
    confidence:
        Probability estimate (0.0-1.0) that the import is genuinely unused.
        Capped at 0.85 — import analysis without full AST is inherently
        uncertain.
    risk:
        Always ``"LOW"`` for imports: removing a redundant import is safe
        and easy to revert.
    evidence:
        Supporting data used to compute confidence.
    """

    id: str
    type: str
    file: str
    item: str
    reason: str
    confidence: float
    risk: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Known safe-to-skip sets
# ---------------------------------------------------------------------------

# Standard-library modules that are almost never "unused" in the way linters
# mean — they are frequently imported for side-effects, re-exports, or are
# hard to detect without real AST usage analysis.  We skip ALL stdlib modules
# to stay conservative.
_STDLIB_MODULES: Set[str] = {
    # Built-ins used for side-effects or typing
    "__future__", "abc", "ast", "asyncio", "builtins", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal",
    "enum", "fnmatch", "functools", "glob", "hashlib", "http", "inspect",
    "io", "itertools", "json", "logging", "math", "operator", "os",
    "pathlib", "pickle", "platform", "pprint", "queue", "random", "re",
    "shutil", "signal", "socket", "sqlite3", "ssl", "stat", "string",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading",
    "time", "traceback", "typing", "types", "unicodedata", "unittest",
    "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
    # Common sub-modules
    "os.path", "typing_extensions", "collections.abc",
}

# Well-known third-party packages that are imported for side-effects or whose
# usage is genuinely hard to detect without real parsing (e.g. `pytest` marks,
# `__all__` re-exports from framework code).
_SKIP_THIRD_PARTY: Set[str] = {
    # Test / dev frameworks (often imported for side-effects or decorators)
    "pytest", "hypothesis", "factory_boy",
    # Web frameworks (decorators, app factories, middleware)
    "click", "flask", "django", "fastapi", "starlette",
    "uvicorn", "gunicorn",
    # ORM / data (imported for model registration side-effects)
    "pydantic", "sqlalchemy", "alembic",
    # Cloud / infra (imported for configuration)
    "boto3", "botocore",
    # HTTP clients (often at module level for connection pooling)
    "requests", "httpx", "aiohttp", "anyio", "trio",
    # Scientific / ML (large APIs, submodule imports everywhere)
    "numpy", "pandas", "scipy", "sklearn", "torch", "tensorflow",
    "PIL", "cv2",
    # Task queues
    "celery",
}


def _classify_import(name: str, internal_stems: Set[str]) -> str:
    """Return ``"stdlib"``, ``"third_party"``, or ``"internal"``."""
    top = name.lstrip(".").split(".")[0]
    if top in _STDLIB_MODULES or name in _STDLIB_MODULES:
        return "stdlib"
    if top in internal_stems:
        return "internal"
    return "third_party"


# ---------------------------------------------------------------------------
# Unused import finder
# ---------------------------------------------------------------------------


class UnusedImportFinder:
    """Scan a Phase 1 report for imports that appear unused.

    Because Phase 1 stores import *names* but not usage sites, this
    detector operates conservatively:

    * Standard-library imports are **always skipped** (too risky to flag
      without full usage analysis).
    * Third-party imports from a known-safe list are also skipped.
    * Internal imports are checked against the cross-reference: if no other
      file lists the imported module's exports among its own imports, it is
      a candidate.
    * Third-party imports not on the safe list get a low-confidence flag
      because they may be imported for type hints, decorators, or
      side-effects that are invisible at the Phase 1 level.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    verbose:
        When ``True``, print progress messages to stdout.
    """

    def __init__(self, phase1_report: Dict[str, Any], verbose: bool = False) -> None:
        self._report  = phase1_report
        self.verbose  = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_unused_imports(self) -> List[Dict[str, Any]]:
        """Return a list of unused-import findings as plain dicts.

        Findings are ordered by file path, then by import name.
        IDs are sequential starting at ``"I001"``.
        """
        internal_stems  = self._collect_internal_stems()
        export_registry = self._build_export_registry()

        findings: List[UnusedImportFinding] = []
        counter = 1

        for file_entry in sorted(self._files, key=lambda f: f.get("path", "")):
            path    = file_entry.get("path", "")
            imports = file_entry.get("imports", [])
            file_type = file_entry.get("file_type", "unknown")
            complexity = float(file_entry.get("complexity_score", 0))

            if self._is_test_file(path):
                continue

            seen_in_file: Set[str] = set()  # deduplicate within a file

            for raw_import in imports:
                if raw_import in seen_in_file:
                    continue

                import_type = _classify_import(raw_import, internal_stems)

                # ── Safety gates ──────────────────────────────────────────
                if self._should_skip(raw_import, import_type):
                    continue

                # ── Detect potential unused-ness ──────────────────────────
                is_unused, extra_confidence, reason = self._assess_import(
                    raw_import, import_type, path, export_registry, internal_stems
                )

                if not is_unused:
                    continue

                # ── Confidence ────────────────────────────────────────────
                confidence = self._compute_confidence(
                    import_type, extra_confidence, complexity
                )

                evidence: Dict[str, Any] = {
                    "usage_count":           0,
                    "import_type":           import_type,
                    "is_exception_handling": False,
                }

                finding = UnusedImportFinding(
                    id=f"I{counter:03d}",
                    type="unused_import",
                    file=path,
                    item=raw_import,
                    reason=reason,
                    confidence=round(confidence, 4),
                    risk="LOW",
                    evidence=evidence,
                )
                findings.append(finding)
                seen_in_file.add(raw_import)
                counter += 1

                self._log(
                    f"  [LOW   ] {path}::{raw_import} "
                    f"({import_type}, conf={finding.confidence:.2f})"
                )

        self._log(f"UnusedImportFinder: {len(findings)} finding(s).")
        return [f.to_dict() for f in findings]

    # ------------------------------------------------------------------
    # Supporting structures
    # ------------------------------------------------------------------

    def _collect_internal_stems(self) -> Set[str]:
        """Return the set of top-level package/module names in the project."""
        stems: Set[str] = set()
        for f in self._files:
            parts = Path(f["path"]).parts
            if parts:
                stems.add(parts[0].split(".")[0])   # top-level directory
            stems.add(Path(f["path"]).stem)          # bare filename stem
        return stems

    def _build_export_registry(self) -> Dict[str, str]:
        """Return ``{export_name: declaring_file_path}`` for every export."""
        registry: Dict[str, str] = {}
        for f in self._files:
            for exp in f.get("exports", []):
                registry[exp] = f["path"]
        return registry

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def _assess_import(
        self,
        raw: str,
        import_type: str,
        importer_path: str,
        export_registry: Dict[str, str],
        internal_stems: Set[str],
    ) -> tuple[bool, float, str]:
        """Decide whether an import looks unused.

        Returns ``(is_suspicious, extra_confidence, reason)``.
        """
        clean = raw.lstrip(".")
        top   = clean.split(".")[0]
        last  = clean.split(".")[-1]

        if import_type == "internal":
            # Check if the imported module / symbol appears as an export
            # in *any* file other than the importer.
            if last in export_registry and export_registry[last] != importer_path:
                # The symbol exists — but does anyone else (besides importer)
                # list it among their imports?  If the importer is the only
                # file with this import, it may be a stale pull.
                importers_of_last = sum(
                    1 for f in self._files
                    if importer_path != f.get("path", "")
                    and last in f.get("imports", [])
                )
                if importers_of_last == 0:
                    return True, 0.20, "Unused internal import"
            # Internal import with no matching export: possibly a namespace
            # import — flag conservatively
            if not any(
                f["path"] != importer_path and (
                    top in Path(f["path"]).parts
                    or Path(f["path"]).stem == last
                )
                for f in self._files
            ):
                return True, 0.10, "Internal import with no matching module found"

        elif import_type == "third_party":
            # We can't see usage sites — flag with low extra confidence
            return True, 0.0, "Third-party import (verify usage manually)"

        return False, 0.0, ""

    # ------------------------------------------------------------------
    # Scoring and classification
    # ------------------------------------------------------------------

    @staticmethod
    def _should_skip(raw: str, import_type: str) -> bool:
        """Return ``True`` if this import should be excluded from findings."""
        # Always skip stdlib: removing these without AST analysis is too risky
        if import_type == "stdlib":
            return True

        # Skip known safe third-party packages (side-effect / decorator imports)
        top = raw.lstrip(".").split(".")[0]
        if top in _SKIP_THIRD_PARTY:
            return True

        # Very short names are likely important (re, io, os...)
        if len(raw.lstrip(".")) < 3:
            return True

        # Relative-only imports (bare dots) are namespace anchors
        if not raw.lstrip("."):
            return True

        # Type-hint-only imports often appear as bare names; skip __future__
        if raw == "__future__" or raw.startswith("__future__"):
            return True

        return False

    @staticmethod
    def _compute_confidence(
        import_type: str,
        extra: float,
        complexity: float,
    ) -> float:
        """Return a confidence score in [0.0, 0.85].

        Scoring
        -------
        Base                        0.60
        + extra                     (0.20 for confirmed-internal, 0.10 other)
        + 0.05  if file is complex  (complexity > 10)
        Cap at 0.85
        """
        score = 0.60 + extra
        if complexity > 10:
            score += 0.05
        return min(score, 0.85)

    @staticmethod
    def _is_test_file(path: str) -> bool:
        name  = Path(path).name
        posix = path.replace("\\", "/")
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in posix
            or "/test/" in posix
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Circular dependency data model
# ---------------------------------------------------------------------------


@dataclass
class CircularDependencyFinding:
    """A single circular-dependency finding.

    Circular dependencies are reported with confidence=1.0 and
    risk="CRITICAL" because they are a factual structural problem, not
    a probabilistic guess.  **Do not attempt to delete any file in the cycle
    without first refactoring the cycle away.**

    Attributes
    ----------
    id:
        Sequential identifier, e.g. "C001".
    type:
        Always "circular_dependency".
    files:
        Deduplicated list of files involved in the cycle.
    cycle_chain:
        The full chain as reported by Phase 1, e.g.
        ["a.py", "b.py", "c.py", "a.py"] where the first and last
        elements are identical.
    reason:
        Human-readable chain string plus a remediation note.
    confidence:
        Always 1.0 -- cycles are deterministic, not probabilistic.
    risk:
        Always "CRITICAL".
    evidence:
        Supporting data: cycle length and severity label.
    """

    id: str
    type: str
    files: List[str]
    cycle_chain: List[str]
    reason: str
    confidence: float
    risk: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Circular dependency analyzer
# ---------------------------------------------------------------------------


class CircularDependencyAnalyzer:
    """Convert the circular_imports list from a Phase 1 report into
    structured :class: objects.

    Circular imports are **not** candidates for automated removal.  They
    require deliberate refactoring (extract a shared module, introduce
    dependency injection, or break the cycle at a well-chosen seam) before
    any individual file in the cycle can safely be touched.

    Parameters
    ----------
    phase1_report:
        The dict produced by Phase1Discovery.scan_project().to_dict().
    verbose:
        When True, print progress messages to stdout.
    """

    def __init__(self, phase1_report: Dict[str, Any], verbose: bool = False) -> None:
        self._report  = phase1_report
        self.verbose  = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_circular_deps(self) -> List[Dict[str, Any]]:
        """Return one :class: per cycle as a dict.

        Cycles are taken directly from phase1_report['circular_imports'].
        Each element is expected to be an ordered list where the first and
        last nodes are identical (e.g. ["a.py", "b.py", "a.py"]).
        Missing or malformed entries are skipped with a warning rather than
        crashing.

        Findings are ordered by cycle length (shortest first), then
        lexicographically by the first file in the chain.
        IDs are sequential starting at "C001".
        """
        raw_cycles: List[Any] = self._report.get("circular_imports", [])

        if not raw_cycles:
            self._log("CircularDependencyAnalyzer: no circular imports found.")
            return []

        findings: List[CircularDependencyFinding] = []
        seen_keys: Set[str] = set()
        counter = 1

        def sort_key(cycle: Any) -> tuple:
            if not isinstance(cycle, list) or not cycle:
                return (999, "")
            return (len(cycle), cycle[0])

        for raw in sorted(raw_cycles, key=sort_key):
            if not isinstance(raw, list) or len(raw) < 2:
                self._log(f"  [!] Skipping malformed cycle entry: {raw!r}")
                continue

            cycle_chain: List[str] = [str(node) for node in raw]

            if cycle_chain[0] != cycle_chain[-1]:
                cycle_chain = cycle_chain + [cycle_chain[0]]

            unique_nodes = list(dict.fromkeys(cycle_chain[:-1]))
            canon_key = "|".join(sorted(unique_nodes))
            if canon_key in seen_keys:
                continue
            seen_keys.add(canon_key)

            cycle_length = len(unique_nodes)
            severity = "simple_2way" if cycle_length == 2 else "complex_chain"

            chain_str = " -> ".join(cycle_chain)
            reason = (
                f"Circular dependency: {chain_str}. "
                "Cannot delete these files separately without refactoring the cycle first."
            )

            evidence: Dict[str, Any] = {
                "cycle_length": cycle_length,
                "severity":     severity,
            }

            finding = CircularDependencyFinding(
                id=f"C{counter:03d}",
                type="circular_dependency",
                files=unique_nodes,
                cycle_chain=cycle_chain,
                reason=reason,
                confidence=1.0,
                risk="CRITICAL",
                evidence=evidence,
            )
            findings.append(finding)
            counter += 1

            self._log(
                f"  [CRITICAL] {severity} ({cycle_length} files): {chain_str}"
            )

        self._log(f"CircularDependencyAnalyzer: {len(findings)} finding(s).")
        return [f.to_dict() for f in findings]

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
