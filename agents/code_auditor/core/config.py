"""
agents/code_auditor/core/config.py
===================================
Configuration system for the Code Auditor Agent.

Usage::

    from agents.code_auditor.core.config import get_config

    config = get_config("ai-command-center")
    scanner = Phase1Discovery(config=config)

Extend ``Phase1Config`` to create project-specific profiles, then register
them in ``get_config``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set


# ---------------------------------------------------------------------------
# Base configuration
# ---------------------------------------------------------------------------


@dataclass
class Phase1Config:
    """
    Base configuration for Phase 1 (Discovery & Analysis).

    All attributes are instance variables with sensible defaults so that
    subclasses can override only what they need.  Class-level constants are
    intentionally avoided here — using dataclass fields means every instance
    gets its own mutable copy and there are no accidental shared-state bugs.
    """

    # ── Filesystem scanning ─────────────────────────────────────────────────

    IGNORE_DIRS: Set[str] = field(default_factory=lambda: {
        # Python
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".pytest_cache",
        "*.egg-info",
        # Build artefacts
        "dist",
        "build",
        # JavaScript / Node
        "node_modules",
        "coverage",
        ".next",
        # Version control & editors
        ".git",
        ".github",
        ".vscode",
        ".idea",
        # OS
        ".DS_Store",
    })

    IGNORE_FILES: Set[str] = field(default_factory=lambda: {
        # Secrets
        ".env",
        ".env.*",
        "*.key",
        "*.pem",
        "*.p8",
        # Lock files (large, auto-generated)
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        # OS artefacts
        ".DS_Store",
        "Thumbs.db",
        # Compiled Python
        "*.pyc",
        "*.pyo",
        "*.pyd",
        # Native extensions
        "*.so",
        "*.dylib",
    })

    SUPPORTED_EXTENSIONS: Set[str] = field(default_factory=lambda: {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".json",
    })

    # ── Safety limits ───────────────────────────────────────────────────────

    MAX_SCAN_TIME_SECONDS: int = 120
    """Hard wall-clock timeout for the full scan.  Raises ``ScanTimeoutError``
    if exceeded so the caller always gets a clean failure rather than a hang."""

    MAX_FILE_SIZE_MB: int = 50
    """Files larger than this are skipped and logged as ``oversized``.
    Prevents memory spikes when accidentally scanning binary blobs."""

    MAX_FILES_TO_SCAN: int = 5000
    """Upper bound on the number of files processed in a single run.
    Increase for very large monorepos, but expect longer scan times."""

    # ── Language-specific analysis options ──────────────────────────────────

    PYTHON_ANALYSIS: Dict[str, bool] = field(default_factory=lambda: {
        # Include module/function/class docstrings in the registry
        "extract_docstrings": True,
        # Capture PEP 484 type annotations for each export
        "extract_type_hints": True,
        # Honour __all__ when present; fall back to public names otherwise
        "extract_all_exports": True,
    })

    JS_ANALYSIS: Dict[str, bool] = field(default_factory=lambda: {
        # Parse JSDoc comment blocks attached to exported symbols
        "extract_jsdoc": True,
        # Attempt best-effort resolution of dynamic import() calls
        "handle_dynamic_imports": True,
        # Track `export default` separately from named exports
        "extract_default_exports": True,
    })

    # ── Report generation ────────────────────────────────────────────────────

    REPORT: Dict = field(default_factory=lambda: {
        # Append the list of detected circular import chains to the report
        "include_circular_imports": True,
        # Include per-file metrics (LOC, complexity, size) in the registry
        "include_metrics": True,
        # Cap the number of circular chains written to the report to avoid
        # noise in pathological codebases
        "max_circular_imports_to_report": 50,
    })

    # ── Post-init hook ───────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Hook for subclasses to extend sets/dicts after field initialisation.

        ``Phase1Config`` itself does nothing here, but defining the method
        ensures that the dataclass-generated ``__init__`` always emits a
        ``self.__post_init__()`` call.  Subclasses that override this method
        MUST either call ``super().__post_init__()`` or be decorated with
        ``@dataclass`` so Python regenerates an appropriate ``__init__``.
        """

    # ── Helpers ──────────────────────────────────────────────────────────────

    def is_ignored_dir(self, name: str) -> bool:
        """Return ``True`` if a directory name matches any ignored pattern.

        Supports exact matches and simple glob-style ``*`` prefix/suffix
        patterns (e.g. ``*.egg-info``).
        """
        import fnmatch
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.IGNORE_DIRS)

    def is_ignored_file(self, filename: str) -> bool:
        """Return ``True`` if a file name matches any ignored pattern."""
        import fnmatch
        return any(fnmatch.fnmatch(filename, pattern) for pattern in self.IGNORE_FILES)

    def is_supported(self, filename: str) -> bool:
        """Return ``True`` if the file extension is in the supported set."""
        from pathlib import Path
        return Path(filename).suffix in self.SUPPORTED_EXTENSIONS

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"extensions={self.SUPPORTED_EXTENSIONS}, "
            f"max_files={self.MAX_FILES_TO_SCAN}, "
            f"timeout={self.MAX_SCAN_TIME_SECONDS}s)"
        )


# ---------------------------------------------------------------------------
# Project-specific subclasses
# ---------------------------------------------------------------------------


@dataclass
class AiCommandCenterConfig(Phase1Config):
    """
    Configuration profile for the ``ai-command-center`` project.

    Extends the base config with project-specific ignore rules to avoid
    scanning large data directories and generated artefacts that are not
    part of the source graph.
    """

    def __post_init__(self) -> None:
        # Extend (not replace) the inherited sets so base safety rules remain.
        self.IGNORE_DIRS = self.IGNORE_DIRS | {
            "chromadb_data",   # vector-store persisted data
            "logs",            # runtime log directories
            "uploads",         # user-uploaded file storage
            "celery_data",     # Celery result backend persistence
        }
        self.IGNORE_FILES = self.IGNORE_FILES | {
            "*.log",
            "*.sqlite3",
            "*.db",
        }


@dataclass
class NextJsConfig(Phase1Config):
    """
    Configuration profile for Next.js / React projects.

    Focuses on TypeScript/JavaScript source; excludes generated Next.js
    cache and output directories that would otherwise inflate file counts.
    """

    def __post_init__(self) -> None:
        self.IGNORE_DIRS = self.IGNORE_DIRS | {
            ".next",
            "out",
            "storybook-static",
            ".turbo",
        }
        self.IGNORE_FILES = self.IGNORE_FILES | {
            "next-env.d.ts",   # auto-generated; not part of the source graph
            "*.stories.tsx",   # Storybook story files (optional — remove if you want them)
        }
        # For pure front-end projects JSON configs are noise; opt out if desired.
        # self.SUPPORTED_EXTENSIONS -= {".json"}


@dataclass
class PythonOnlyConfig(Phase1Config):
    """
    Minimal profile for pure-Python projects.

    Strips JavaScript/TypeScript extensions so the scanner focuses exclusively
    on Python files and avoids parsing any bundled front-end assets.
    """

    def __post_init__(self) -> None:
        self.SUPPORTED_EXTENSIONS = {".py"}
        self.JS_ANALYSIS = {
            "extract_jsdoc": False,
            "handle_dynamic_imports": False,
            "extract_default_exports": False,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, type[Phase1Config]] = {
    "default":           Phase1Config,
    "ai-command-center": AiCommandCenterConfig,
    "nextjs":            NextJsConfig,
    "next":              NextJsConfig,          # alias
    "python":            PythonOnlyConfig,
}


def get_config(project_type: str = "default") -> Phase1Config:
    """
    Return an instantiated config object for the given project type.

    Parameters
    ----------
    project_type:
        A string key identifying the project profile.  Built-in keys:

        * ``"default"``           — base config, works for most projects
        * ``"ai-command-center"`` — tuned for the AI Command Center backend
        * ``"nextjs"`` / ``"next"`` — tuned for Next.js front-end projects
        * ``"python"``            — Python-only, skips JS/TS parsing

        Unknown keys fall back to ``"default"`` with a warning.

    Returns
    -------
    Phase1Config
        An instantiated (and ``__post_init__``-resolved) config object.

    Examples
    --------
    >>> config = get_config("ai-command-center")
    >>> config.is_ignored_dir("logs")
    True
    >>> config.is_supported("scanner.py")
    True
    """
    key = project_type.lower().strip()
    cls = _REGISTRY.get(key)

    if cls is None:
        import warnings
        warnings.warn(
            f"Unknown project_type {project_type!r}. "
            f"Available: {list(_REGISTRY)}. Falling back to 'default'.",
            UserWarning,
            stacklevel=2,
        )
        cls = Phase1Config

    return cls()


def register_config(name: str, config_class: type[Phase1Config]) -> None:
    """
    Register a custom config class under a project-type name.

    Useful when the auditor is used as a library and the calling project
    wants to inject its own profile without modifying this file.

    Parameters
    ----------
    name:
        The key to use when calling ``get_config(name)``.
    config_class:
        A ``Phase1Config`` subclass (not an instance).

    Examples
    --------
    >>> from agents.code_auditor.core.config import Phase1Config, register_config
    >>>
    >>> class MyProjectConfig(Phase1Config):
    ...     def __post_init__(self):
    ...         self.IGNORE_DIRS |= {"generated"}
    ...
    >>> register_config("my-project", MyProjectConfig)
    >>> config = get_config("my-project")
    """
    if not (isinstance(config_class, type) and issubclass(config_class, Phase1Config)):
        raise TypeError(
            f"config_class must be a subclass of Phase1Config, got {config_class!r}"
        )
    _REGISTRY[name.lower().strip()] = config_class
