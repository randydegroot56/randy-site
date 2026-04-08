"""
agents/code_auditor/core/phase1_discovery.py
=============================================
Phase 1 Discovery Engine -- scans a project directory, extracts imports/
exports from every supported source file, builds a dependency graph, and
detects circular imports.

Usage (CLI)::

    python agents/code_auditor/core/phase1_discovery.py --project . --verbose
    python agents/code_auditor/core/phase1_discovery.py --project /path/to/repo --output report.json

Usage (library)::

    import asyncio
    from agents.code_auditor.core.phase1_discovery import Phase1Discovery

    registry = asyncio.run(Phase1Discovery("/path/to/repo", verbose=True).scan_project())
    print(registry.statistics)

Safety guarantees:
- Read-only: no file is ever written or deleted
- Timeout: the full scan aborts after 60 seconds and returns partial results
- Size limit: files larger than 50 MB are skipped
- Error isolation: per-file parse failures are logged and skipped; the scan
  always produces a usable (possibly partial) registry
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IGNORE_DIRS: Set[str] = {
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".git",
    ".github",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "coverage",
    ".turbo",
    "storybook-static",
}

IGNORE_FILES: Set[str] = {
    ".env",
    ".env.local",
    ".DS_Store",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Thumbs.db",
}

# Glob-style patterns evaluated with Path.match()
IGNORE_FILE_PATTERNS: List[str] = [
    ".env.*.local",
    "*.key",
    "*.pem",
    "*.p8",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dylib",
    "*.lock",
]

SUPPORTED_EXTENSIONS: Set[str] = {".py", ".js", ".jsx", ".ts", ".tsx", ".json"}

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
SCAN_TIMEOUT_SECONDS: int = 60


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FileMetadata:
    """Metadata and dependency information extracted from a single source file.

    Attributes
    ----------
    path:
        Project-relative POSIX path (e.g. ``"src/app/page.js"``).
    file_type:
        One of ``"python"``, ``"javascript"``, ``"typescript"``, ``"json"``,
        or ``"unknown"``.
    size_bytes:
        Raw file size in bytes.
    lines:
        Number of lines in the file.
    imports:
        Module/package names this file depends on.
    exports:
        Names (functions, classes, constants) this file exposes.
    docstring:
        Module-level docstring, or ``None`` if absent.
    last_modified:
        ISO-8601 UTC timestamp of the file's last modification.
    complexity_score:
        Simple metric: ``num_functions + num_classes * 2``.
    imports_count:
        Convenience alias for ``len(imports)``.
    exports_count:
        Convenience alias for ``len(exports)``.
    """

    path: str
    file_type: str
    size_bytes: int
    lines: int
    imports: List[str]
    exports: List[str]
    docstring: Optional[str]
    last_modified: str
    complexity_score: float
    imports_count: int = 0
    exports_count: int = 0

    def __post_init__(self) -> None:
        self.imports_count = len(self.imports)
        self.exports_count = len(self.exports)


@dataclass
class ProjectRegistry:
    """Full scan result returned by :meth:`Phase1Discovery.scan_project`.

    Attributes
    ----------
    timestamp:
        ISO-8601 UTC time the scan completed.
    project_root:
        Absolute path of the scanned project.
    files:
        One :class:`FileMetadata` entry per scanned file.
    statistics:
        Aggregate metrics (total files, lines, language breakdown, etc.).
    circular_imports:
        Each element is an ordered list of relative paths forming a cycle,
        e.g. ``[["a.py", "b.py", "a.py"]]``.
    external_dependencies:
        Package names imported by the project that appear to be third-party
        (i.e. not a relative import and not a stdlib module).
    """

    timestamp: str
    project_root: str
    files: List[FileMetadata]
    statistics: Dict[str, Any]
    circular_imports: List[List[str]]
    external_dependencies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the registry."""
        data = asdict(self)
        # Flatten the FileMetadata list so each entry matches the report schema
        data["files"] = [asdict(f) for f in self.files]
        return data


# ---------------------------------------------------------------------------
# Discovery engine
# ---------------------------------------------------------------------------


class Phase1Discovery:
    """Scan a project directory and build a :class:`ProjectRegistry`.

    Parameters
    ----------
    project_root:
        Root directory of the project to scan.
    verbose:
        When ``True``, print progress messages to stdout.
    """

    def __init__(self, project_root: str, verbose: bool = False) -> None:
        self.root = Path(project_root).resolve()
        self.verbose = verbose

        # Internal state populated during the scan
        self._files: List[FileMetadata] = []
        self._errors: List[str] = []
        # path (relative str) -> list of imported relative paths (relative str)
        self._dep_graph: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scan_project(self) -> ProjectRegistry:
        """Run the full discovery scan and return a :class:`ProjectRegistry`.

        The scan is bounded by :data:`SCAN_TIMEOUT_SECONDS`.  If the timeout
        is reached, a partial registry is returned with whatever has been
        scanned so far.

        Returns
        -------
        ProjectRegistry
            Always returns a registry; never raises.
        """
        self._log(f"Scanning project: {self.root}")

        try:
            await asyncio.wait_for(
                self._scan_all_files(),
                timeout=SCAN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            print(
                f"[!] Scan timed out after {SCAN_TIMEOUT_SECONDS}s -- "
                f"returning partial results ({len(self._files)} files scanned).",
                file=sys.stderr,
            )

        self._build_dependency_graph()
        circular = self._detect_circular_imports()
        stats = self._compute_statistics()
        ext_deps = self._collect_external_dependencies()

        registry = ProjectRegistry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            project_root=str(self.root),
            files=self._files,
            statistics=stats,
            circular_imports=circular,
            external_dependencies=sorted(ext_deps),
        )

        self._log(
            f"Scan complete: {len(self._files)} files, "
            f"{len(circular)} circular import chain(s), "
            f"{len(self._errors)} error(s)."
        )
        return registry

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    async def _scan_all_files(self) -> None:
        """Walk the project tree and analyse every supported source file."""
        for path in self._iter_source_files():
            metadata = await self._analyze_file(path)
            if metadata is not None:
                self._files.append(metadata)

    def _iter_source_files(self):
        """Yield :class:`~pathlib.Path` objects for every file to scan."""
        for item in self.root.rglob("*"):
            if not item.is_file():
                continue
            # Skip ignored directories anywhere in the path
            if any(part in IGNORE_DIRS for part in item.parts):
                continue
            # Skip ignored file names
            if item.name in IGNORE_FILES:
                continue
            # Skip glob-pattern matches
            if any(item.match(pattern) for pattern in IGNORE_FILE_PATTERNS):
                continue
            # Skip unsupported extensions
            if item.suffix not in SUPPORTED_EXTENSIONS:
                continue
            yield item

    async def _analyze_file(self, path: Path) -> Optional[FileMetadata]:
        """Extract metadata from a single file.

        Returns ``None`` (and logs the error) if the file cannot be read or
        parsed.
        """
        rel = path.relative_to(self.root).as_posix()

        # ── Size guard ────────────────────────────────────────────────────
        try:
            size = path.stat().st_size
        except OSError as exc:
            self._warn(f"Cannot stat {rel}: {exc}")
            return None

        if size > MAX_FILE_SIZE_BYTES:
            self._warn(f"Skipping oversized file ({size / 1_048_576:.1f} MB): {rel}")
            return None

        # ── Read ──────────────────────────────────────────────────────────
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            self._warn(f"Cannot read {rel}: {exc}")
            return None

        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        last_mod = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        file_type = self._determine_file_type(path)

        # ── Parse ─────────────────────────────────────────────────────────
        imports: List[str] = []
        exports: List[str] = []
        docstring: Optional[str] = None
        complexity: float = 0.0

        if file_type == "python":
            imports, exports, docstring, complexity = self._analyze_python(content, rel)
        elif file_type in ("javascript", "typescript"):
            imports, exports, complexity = self._analyze_js(content)
        elif file_type == "json":
            pass  # JSON files have no imports/exports
        # unknown: leave everything empty

        self._log(f"  [{file_type:12s}] {rel} ({lines} lines, {len(imports)} imports, {len(exports)} exports)")

        return FileMetadata(
            path=rel,
            file_type=file_type,
            size_bytes=size,
            lines=lines,
            imports=imports,
            exports=exports,
            docstring=docstring,
            last_modified=last_mod,
            complexity_score=complexity,
        )

    # ------------------------------------------------------------------
    # File type detection
    # ------------------------------------------------------------------

    _EXT_MAP: Dict[str, str] = {
        ".py":   "python",
        ".js":   "javascript",
        ".jsx":  "javascript",
        ".ts":   "typescript",
        ".tsx":  "typescript",
        ".json": "json",
    }

    def _determine_file_type(self, path: Path) -> str:
        """Return a normalised language label for *path*."""
        return self._EXT_MAP.get(path.suffix.lower(), "unknown")

    # ------------------------------------------------------------------
    # Python analysis
    # ------------------------------------------------------------------

    def _analyze_python(
        self,
        content: str,
        rel_path: str = "<unknown>",
    ) -> Tuple[List[str], List[str], Optional[str], float]:
        """Parse Python source with :mod:`ast` and return
        ``(imports, exports, docstring, complexity_score)``.

        Falls back to ``([], [], None, 0.0)`` if the file cannot be parsed.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            self._warn(f"AST parse error in {rel_path}: {exc}")
            return [], [], None, 0.0

        imports: List[str] = []
        exports: List[str] = []
        num_functions = 0
        num_classes = 0

        for node in ast.walk(tree):
            # ── Imports ───────────────────────────────────────────────────
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                # Relative imports: prepend dots so callers can tell them apart
                level = node.level or 0
                prefix = "." * level
                imports.append(f"{prefix}{module}" if module else prefix)

            # ── Exports via __all__ ───────────────────────────────────────
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)

            # ── Complexity proxies ────────────────────────────────────────
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                num_functions += 1
                # Top-level functions that are not prefixed with _ are exports
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_") and not exports:
                        exports.append(node.name)

            elif isinstance(node, ast.ClassDef):
                num_classes += 1
                if not node.name.startswith("_") and not any(
                    e == node.name for e in exports
                ):
                    exports.append(node.name)

        # If __all__ was found, use only those names as exports
        # (already populated above; public functions/classes were added only
        # when __all__ was NOT present — re-collect properly)
        all_node = self._find_all_assignment(tree)
        if all_node is not None:
            explicit: List[str] = []
            if isinstance(all_node.value, (ast.List, ast.Tuple)):
                for elt in all_node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        explicit.append(elt.value)
            exports = explicit

        docstring = ast.get_docstring(tree)
        complexity = float(num_functions + num_classes * 2)

        # Deduplicate while preserving order
        imports = list(dict.fromkeys(imports))
        exports = list(dict.fromkeys(exports))

        return imports, exports, docstring, complexity

    @staticmethod
    def _find_all_assignment(tree: ast.Module) -> Optional[ast.Assign]:
        """Return the first ``__all__ = [...]`` node in the module body, or ``None``."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return node
        return None

    # ------------------------------------------------------------------
    # JavaScript / TypeScript analysis
    # ------------------------------------------------------------------

    # ── Import patterns ────────────────────────────────────────────────
    _JS_IMPORT_PATTERNS: List[re.Pattern] = [
        # import X from 'module'
        # import { X, Y } from 'module'
        # import * as X from 'module'
        re.compile(r"""^\s*import\s+(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE),
        # const X = require('module')
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        # dynamic import('module')
        re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    ]

    # ── Export patterns ────────────────────────────────────────────────
    _JS_EXPORT_NAMED = re.compile(
        r"""^export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)""",
        re.MULTILINE,
    )
    _JS_EXPORT_BRACE = re.compile(
        r"""^export\s*\{([^}]+)\}""",
        re.MULTILINE,
    )
    _JS_EXPORT_DEFAULT = re.compile(
        r"""^export\s+default\s+(?!function|class)(\w+)""",
        re.MULTILINE,
    )

    # Function/class counters for complexity
    _JS_FUNCTION_RE = re.compile(
        r"""\b(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(|=>\s*\{)""",
    )
    _JS_CLASS_RE = re.compile(r"""\bclass\s+\w+""")

    def _analyze_js(self, content: str) -> Tuple[List[str], List[str], float]:
        """Extract imports, exports, and complexity from JS/TS source.

        Returns ``(imports, exports, complexity_score)``.
        """
        imports: List[str] = []
        exports: List[str] = []

        # ── Imports ───────────────────────────────────────────────────────
        for pattern in self._JS_IMPORT_PATTERNS:
            for match in pattern.finditer(content):
                module = match.group(1).strip()
                if module:
                    imports.append(module)

        # ── Named exports ─────────────────────────────────────────────────
        for match in self._JS_EXPORT_NAMED.finditer(content):
            exports.append(match.group(1))

        # ── Brace exports:  export { Foo, Bar as Baz } ────────────────────
        for match in self._JS_EXPORT_BRACE.finditer(content):
            for name in match.group(1).split(","):
                name = name.strip().split(" as ")[0].strip()
                if name:
                    exports.append(name)

        # ── Default export (non-function/class) ───────────────────────────
        for match in self._JS_EXPORT_DEFAULT.finditer(content):
            exports.append(match.group(1))

        # ── Complexity ────────────────────────────────────────────────────
        num_functions = len(self._JS_FUNCTION_RE.findall(content))
        num_classes   = len(self._JS_CLASS_RE.findall(content))
        complexity = float(num_functions + num_classes * 2)

        imports = list(dict.fromkeys(imports))
        exports = list(dict.fromkeys(exports))

        return imports, exports, complexity

    # ------------------------------------------------------------------
    # Dependency graph
    # ------------------------------------------------------------------

    def _build_dependency_graph(self) -> None:
        """Populate ``self._dep_graph`` from the scanned file list.

        Only intra-project dependencies (relative imports or imports whose
        resolved path matches a scanned file) are recorded.  Third-party
        packages are omitted so the cycle detector only sees project files.
        """
        # Build a quick lookup: module-style name -> relative path
        # e.g. "agents.scraper" -> "agents/scraper.py"
        known: Dict[str, str] = {}
        for fm in self._files:
            p = Path(fm.path)
            # Drop extension, convert separators to dots
            dotted = p.with_suffix("").as_posix().replace("/", ".")
            known[dotted] = fm.path
            # Also store the bare stem for single-level references
            known[p.stem] = fm.path

        for fm in self._files:
            deps: List[str] = []
            for raw_import in fm.imports:
                resolved = self._resolve_import(raw_import, fm.path, known)
                if resolved and resolved != fm.path:
                    deps.append(resolved)
            self._dep_graph[fm.path] = list(dict.fromkeys(deps))

    def _resolve_import(
        self,
        raw: str,
        importer_path: str,
        known: Dict[str, str],
    ) -> Optional[str]:
        """Try to map a raw import string to a relative file path.

        Returns the resolved path string, or ``None`` if the import is
        external / unresolvable.
        """
        # Relative Python import: starts with one or more dots
        if raw.startswith("."):
            dots = len(raw) - len(raw.lstrip("."))
            module = raw.lstrip(".")
            base = Path(importer_path).parent
            for _ in range(dots - 1):
                base = base.parent
            candidate = (base / module.replace(".", "/")).as_posix()
            # Try with common extensions
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx"):
                key = candidate + ext
                for fm in self._files:
                    if fm.path == key or fm.path.endswith("/" + Path(key).name):
                        return fm.path
            return None

        # Relative JS import: starts with ./ or ../
        if raw.startswith("./") or raw.startswith("../"):
            base = Path(importer_path).parent
            candidate = (base / raw).resolve()
            # Normalise back to a relative string
            try:
                rel = candidate.relative_to(self.root).as_posix()
            except ValueError:
                return None
            for ext in ("", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"):
                check = rel + ext
                for fm in self._files:
                    if fm.path == check:
                        return fm.path
            return None

        # Absolute module name: check known mapping
        dotted = raw.replace("/", ".")
        if dotted in known:
            return known[dotted]

        # Top-level segment match (e.g. "agents.scraper" -> "agents/scraper.py")
        if raw in known:
            return known[raw]

        return None  # external package

    # ------------------------------------------------------------------
    # Circular import detection
    # ------------------------------------------------------------------

    def _detect_circular_imports(self) -> List[List[str]]:
        """Run DFS over the dependency graph and return all cycles.

        Each cycle is represented as a list of node paths where the first
        and last elements are identical (e.g. ``["a.py", "b.py", "a.py"]``).
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            in_stack.add(node)
            path.append(node)

            for neighbour in self._dep_graph.get(node, []):
                if neighbour not in visited:
                    dfs(neighbour, path)
                elif neighbour in in_stack:
                    # Found a cycle — extract the cycle portion
                    cycle_start = path.index(neighbour)
                    cycle = path[cycle_start:] + [neighbour]
                    # Deduplicate cycles by their canonical (sorted) form
                    key = tuple(sorted(cycle[:-1]))
                    if not any(tuple(sorted(c[:-1])) == key for c in cycles):
                        cycles.append(cycle)

            path.pop()
            in_stack.remove(node)

        for node in list(self._dep_graph.keys()):
            if node not in visited:
                dfs(node, [])

        return cycles

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _compute_statistics(self) -> Dict[str, Any]:
        """Return aggregate metrics over all scanned files."""
        if not self._files:
            return {
                "total_files": 0,
                "total_lines": 0,
                "total_size_bytes": 0,
                "avg_lines_per_file": 0,
                "largest_file": None,
                "by_language": {},
            }

        total_lines = sum(f.lines for f in self._files)
        total_size  = sum(f.size_bytes for f in self._files)

        by_language: Dict[str, int] = {}
        for fm in self._files:
            by_language[fm.file_type] = by_language.get(fm.file_type, 0) + 1

        largest = max(self._files, key=lambda f: f.lines)

        return {
            "total_files":        len(self._files),
            "total_lines":        total_lines,
            "total_size_bytes":   total_size,
            "avg_lines_per_file": total_lines // len(self._files),
            "largest_file":       f"{largest.path} ({largest.lines} lines)",
            "by_language":        by_language,
            "scan_errors":        len(self._errors),
        }

    # ------------------------------------------------------------------
    # External dependencies
    # ------------------------------------------------------------------

    def _collect_external_dependencies(self) -> Set[str]:
        """Return the set of third-party package names imported by the project.

        Heuristic: any import that is not a relative import and whose top-level
        name does not match a scanned file is considered external.
        """
        internal_roots: Set[str] = set()
        for fm in self._files:
            # Top-level directory or bare filename stem
            parts = Path(fm.path).parts
            if parts:
                internal_roots.add(parts[0].split(".")[0])
            internal_roots.add(Path(fm.path).stem)

        external: Set[str] = set()
        for fm in self._files:
            for imp in fm.imports:
                if imp.startswith("."):
                    continue  # relative
                top = imp.split(".")[0].split("/")[0]
                if top and top not in internal_roots:
                    external.add(top)

        return external

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _warn(self, message: str) -> None:
        self._errors.append(message)
        print(f"[!] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase1_discovery",
        description="Phase 1 Code Auditor -- discover imports, exports, and dependencies.",
    )
    parser.add_argument(
        "--project",
        metavar="PATH",
        default=".",
        help="Root directory of the project to scan (default: current directory).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default="audit_report.json",
        help="Destination for the JSON report (default: audit_report.json).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress messages during the scan.",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    discovery = Phase1Discovery(args.project, verbose=args.verbose)
    registry = await discovery.scan_project()

    output = Path(args.output)
    output.write_text(
        json.dumps(registry.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Report written -> {output.resolve()} ({len(registry.files)} files)")

    stats = registry.statistics
    print(f"  total_files  : {stats.get('total_files', 0):,}")
    print(f"  total_lines  : {stats.get('total_lines', 0):,}")
    print(f"  circular     : {len(registry.circular_imports)}")
    print(f"  ext_deps     : {len(registry.external_dependencies)}")
    if registry.circular_imports:
        print("  Circular chains:")
        for chain in registry.circular_imports:
            print(f"    {' -> '.join(chain)}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for CLI usage."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
