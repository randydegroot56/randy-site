"""
agents/code_auditor/core/phase3_verification.py
================================================
Phase 3 Verification Engine -- safety checks before any code is removed.

The key principle: **if something is tested, deleting it is less safe**.
Removing tested code doesn't just delete lines — it also silently breaks
the test suite.  The TestDependencyChecker makes this cost explicit so the
caller can decide whether to proceed, update the tests first, or skip the
finding entirely.

Usage::

    from agents.code_auditor.core.phase3_verification import TestDependencyChecker

    checker = TestDependencyChecker(phase1_report, phase2_findings, verbose=True)
    results = checker.check_test_dependencies()
    for r in results:
        print(r["finding_id"], r["has_tests"], r["reason"])
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TestDependencyResult:
    """Verification result for a single Phase 2 finding.

    Attributes
    ----------
    finding_id:
        The ``id`` of the Phase 2 finding this result corresponds to
        (e.g. ``"U001"``).
    has_tests:
        ``True`` if at least one test file imports or mentions the flagged
        item.
    test_files:
        Paths of every test file that references the item.
    confidence_adjustment:
        Amount added to the original confidence score.  Negative values
        reduce confidence (item is less safe to delete); positive values
        increase it (safer).
    risk_adjustment:
        The *new* risk label after the adjustment, or the original label if
        no change is needed.
    reason:
        Human-readable summary of the test-dependency situation.
    original_finding:
        The original Phase 2 finding dict, included for convenience so
        callers don't need to cross-reference by ID.
    adjusted_confidence:
        The original confidence + ``confidence_adjustment``, clamped to
        ``[0.0, 0.99]``.
    """

    finding_id:            str
    has_tests:             bool
    test_files:            List[str]
    confidence_adjustment: float
    risk_adjustment:       str
    reason:                str
    original_finding:      Dict[str, Any] = field(default_factory=dict)
    adjusted_confidence:   float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_adjusted_finding(self) -> Dict[str, Any]:
        """Return the original finding with confidence and risk updated."""
        updated = dict(self.original_finding)
        updated["confidence"] = round(self.adjusted_confidence, 4)
        updated["risk"]       = self.risk_adjustment
        ev = dict(updated.get("evidence") or {})
        ev["test_files"]   = self.test_files
        ev["has_tests"]    = self.has_tests
        updated["evidence"] = ev
        return updated


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


class TestDependencyChecker:
    """Verify whether Phase 2 findings have test coverage.

    For each finding the checker:

    * Scans every test file in the Phase 1 report.
    * Checks whether the test file's ``imports`` list references the source
      file or the flagged symbol, or whether the symbol appears in the test
      file's ``exports`` list (a proxy for "mentioned in the file").
    * Adjusts confidence and risk accordingly:

      - **Has tests** → ``confidence -= 0.15``, risk raised one step.
        Removing something that is tested will also break the tests.
      - **No tests**  → ``confidence += 0.05``, risk unchanged.
        Nothing to break beyond the production code itself.

    This is intentionally conservative: if there is *any* test coverage,
    it is flagged.  The goal is to surface "this needs a test-update plan"
    before a deletion is executed, not to block deletion permanently.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    phase2_findings:
        The list of finding dicts from Phase 2 detectors (optionally already
        adjusted by ``TestCoverageVerifier``).
    verbose:
        When ``True``, print one line per finding to stdout.
    """

    _RISK_ORDER: Dict[str, int] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    _ORDER_RISK: Dict[int, str] = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "CRITICAL"}

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        phase2_findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self._report   = phase1_report
        self._findings = phase2_findings
        self.verbose   = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

        # Pre-index test files once
        self._test_index: Dict[str, Dict[str, Set[str]]] = {}
        self._build_test_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_test_dependencies(self) -> List[Dict[str, Any]]:
        """Run the test-dependency check for every Phase 2 finding.

        Returns
        -------
        List[dict]
            One :class:`TestDependencyResult` dict per input finding,
            in the same order as ``phase2_findings``.  Each dict also
            exposes a convenience key ``"adjusted_finding"`` containing
            the finding with updated confidence and risk.
        """
        results: List[Dict[str, Any]] = []

        for finding in self._findings:
            result = self._check_one(finding)
            entry  = result.to_dict()
            entry["adjusted_finding"] = result.to_adjusted_finding()
            results.append(entry)

            if self.verbose:
                tag = "tested" if result.has_tests else "no tests"
                self._log(
                    f"  [{finding.get('id', '?'):5s}] {tag}: "
                    f"conf {float(finding.get('confidence', 0)):.2f} -> "
                    f"{result.adjusted_confidence:.2f}  "
                    f"risk {finding.get('risk', '?')} -> {result.risk_adjustment}  "
                    f"({len(result.test_files)} test file(s))"
                )

        self._log(
            f"TestDependencyChecker: {len(results)} result(s), "
            f"{sum(1 for r in results if r['has_tests'])} with test coverage."
        )
        return results

    def get_adjusted_findings(self) -> List[Dict[str, Any]]:
        """Convenience wrapper: return only the adjusted finding dicts.

        Equivalent to ``[r['adjusted_finding'] for r in check_test_dependencies()]``
        but avoids computing results twice when the caller only needs findings.
        """
        return [r["adjusted_finding"] for r in self.check_test_dependencies()]

    # ------------------------------------------------------------------
    # Per-finding logic
    # ------------------------------------------------------------------

    def _check_one(self, finding: Dict[str, Any]) -> TestDependencyResult:
        """Check test coverage for a single finding and return a result."""
        finding_id = finding.get("id", "?")
        ftype      = finding.get("type", "")

        # Determine what to look for
        source_file = finding.get("file", "")
        if not source_file:
            # orphan_file / circular_dependency use "files" list
            files_list  = finding.get("files") or []
            source_file = files_list[0] if files_list else ""

        symbol = finding.get("item", "")  # may be empty for orphan/circular

        # Search test files
        matched_tests = self._find_covering_tests(source_file, symbol)
        has_tests     = len(matched_tests) > 0

        # Adjust confidence
        original_conf = float(finding.get("confidence", 0.70))
        if has_tests:
            delta = -0.15
        else:
            delta = +0.05
        adjusted_conf = round(min(max(original_conf + delta, 0.0), 0.99), 4)

        # Adjust risk
        original_risk = finding.get("risk", "MEDIUM")
        if original_risk == "CRITICAL":
            # Never change CRITICAL — it's structural
            new_risk = "CRITICAL"
        elif has_tests:
            new_risk = self._raise_risk(original_risk)
        else:
            new_risk = original_risk

        # Reason
        reason = self._build_reason(has_tests, matched_tests, ftype)

        return TestDependencyResult(
            finding_id=finding_id,
            has_tests=has_tests,
            test_files=sorted(matched_tests),
            confidence_adjustment=delta,
            risk_adjustment=new_risk,
            reason=reason,
            original_finding=finding,
            adjusted_confidence=adjusted_conf,
        )

    # ------------------------------------------------------------------
    # Test-index builder and lookup
    # ------------------------------------------------------------------

    def _build_test_index(self) -> None:
        """Pre-index every test file by its imports, exports, and stem."""
        for f in self._files:
            path = f.get("path", "")
            if not self._is_test_file(path):
                continue

            imports: List[str] = f.get("imports", [])
            exports: List[str] = f.get("exports", [])

            # Expand imports: store full string + last dotted segment
            expanded_imports: Set[str] = set()
            for imp in imports:
                clean = imp.lstrip(".")
                expanded_imports.add(clean)
                expanded_imports.add(clean.split(".")[-1].split("/")[-1])

            self._test_index[path] = {
                "imports": expanded_imports,
                "exports": set(exports),
            }

    def _find_covering_tests(self, source_file: str, symbol: str) -> List[str]:
        """Return paths of test files that reference *source_file* or *symbol*."""
        file_stem   = Path(source_file).stem if source_file else ""
        file_dotted = (
            Path(source_file).with_suffix("").as_posix().replace("/", ".")
            if source_file
            else ""
        )

        covering: List[str] = []
        for test_path, index in self._test_index.items():
            imp_set  = index["imports"]
            exp_set  = index["exports"]

            # File-level match: test imports the source module
            if file_dotted and file_dotted in imp_set:
                covering.append(test_path)
                continue
            if file_stem and file_stem in imp_set:
                covering.append(test_path)
                continue

            # Symbol-level match: test explicitly names the symbol
            if symbol and (symbol in imp_set or symbol in exp_set):
                covering.append(test_path)
                continue

        return covering

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _raise_risk(self, current: str) -> str:
        """Move risk one level higher, capped at CRITICAL."""
        idx = self._RISK_ORDER.get(current, 1)
        return self._ORDER_RISK.get(min(idx + 1, 3), "CRITICAL")

    @staticmethod
    def _build_reason(has_tests: bool, test_files: List[str], ftype: str) -> str:
        if has_tests:
            n = len(test_files)
            noun = "test file" if n == 1 else "test files"
            return (
                f"Referenced in {n} {noun} -- "
                "removing this item will also require updating the test suite."
            )
        if ftype == "circular_dependency":
            return "No direct test coverage -- refactoring is still required."
        return "No test coverage detected -- safer to remove, but verify manually."

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
# API endpoint safety checker
# ---------------------------------------------------------------------------

import re as _re

# Path fragments that indicate a file lives in an API layer
_API_PATH_FRAGMENTS: Set[str] = {
    "/api/", "/apis/", "/routes/", "/route/",
    "/endpoints/", "/endpoint/", "/views/",
    "/controllers/", "/controller/",
    "/handlers/", "/handler/",
}

# HTTP-verb decorator patterns from common Python frameworks
# FastAPI, Flask, Django REST, aiohttp, Sanic, Starlette, etc.
_ROUTE_DECORATOR_RE = _re.compile(
    r"@\w+\.(get|post|put|patch|delete|head|options|trace|route|add_route"
    r"|api_view|action)\b",
    _re.IGNORECASE,
)

# Function names that follow REST naming conventions
_HTTP_VERB_PREFIX_RE = _re.compile(
    r"^(get|post|put|patch|delete|list|create|update|destroy|retrieve|"
    r"partial_update|handle|serve|fetch|endpoint)_?\w*$",
    _re.IGNORECASE,
)

# URL path patterns inside the function / file name
_URL_PATH_RE = _re.compile(r"[\"'](/[\w/{}_-]+)[\"']")

# Version indicators in paths or names
_VERSION_RE = _re.compile(r"\bv\d+\b|/v\d+/", _re.IGNORECASE)

# Deprecated signals in names
_DEPRECATED_RE = _re.compile(r"\b(deprecated|legacy|old|v\d+|compat)\b", _re.IGNORECASE)


@dataclass
class APIEndpointResult:
    """Safety verdict for a single finding that may be an API endpoint.

    Attributes
    ----------
    finding_id:
        The ``id`` of the Phase 2 finding.
    is_api_endpoint:
        ``True`` if the item was identified as an API endpoint.
    endpoint_type:
        One of ``"fastapi"``, ``"flask"``, ``"django"``, ``"generic_rest"``,
        or ``"unknown"`` when ``is_api_endpoint`` is ``True``.
    versioned:
        ``True`` if the endpoint path or name contains a version token
        (``v1``, ``v2``, …).
    deprecated_signal:
        ``True`` if the name contains words like *deprecated*, *legacy*,
        *old*, or a lower version token.
    recommendation:
        Concrete action to take instead of deletion.
    adjusted_risk:
        Updated risk level (always ``"HIGH"`` for confirmed endpoints,
        ``"MEDIUM"`` for deprecated-signal ones).
    adjusted_confidence:
        Updated confidence score (always low for endpoints).
    reason:
        Human-readable explanation.
    original_finding:
        The original Phase 2 finding dict.
    """

    finding_id:           str
    is_api_endpoint:      bool
    endpoint_type:        str
    versioned:            bool
    deprecated_signal:    bool
    recommendation:       str
    adjusted_risk:        str
    adjusted_confidence:  float
    reason:               str
    original_finding:     Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_adjusted_finding(self) -> Dict[str, Any]:
        """Return the original finding with risk, confidence, and evidence updated."""
        updated = dict(self.original_finding)
        if self.is_api_endpoint:
            updated["risk"]       = self.adjusted_risk
            updated["confidence"] = round(self.adjusted_confidence, 4)
            ev = dict(updated.get("evidence") or {})
            ev["is_api_endpoint"]   = True
            ev["endpoint_type"]     = self.endpoint_type
            ev["versioned"]         = self.versioned
            ev["deprecated_signal"] = self.deprecated_signal
            ev["recommendation"]    = self.recommendation
            updated["evidence"]     = ev
        return updated


class APIEndpointChecker:
    """Identify API endpoints among Phase 2 findings and apply safety rules.

    API endpoints must **never** be deleted outright — external clients may
    depend on them.  This checker:

    1. Detects whether a finding targets an API endpoint by examining:
       - The file path (``api/``, ``routes/``, ``endpoints/`` directories)
       - The symbol name (HTTP-verb prefixes, ``handle_*`` functions)
       - The imports of the containing file (framework imports)
    2. For confirmed endpoints: sets ``risk="HIGH"``, reduces confidence to
       at most ``0.30``, and generates a deprecation-path recommendation.
    3. For endpoints with a deprecated signal (``v1``, ``legacy``, …):
       sets ``risk="MEDIUM"`` to indicate a managed migration is still needed.

    Parameters
    ----------
    phase1_report:
        The dict produced by ``Phase1Discovery.scan_project().to_dict()``.
    phase2_findings:
        The list of finding dicts to inspect.
    verbose:
        When ``True``, print one line per endpoint finding to stdout.
    """

    # Confidence cap for confirmed API endpoints
    _API_CONFIDENCE_CAP: float = 0.30
    # Confidence cap for deprecated-signal endpoints (a bit higher — migration planned)
    _DEPRECATED_CONFIDENCE_CAP: float = 0.45

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        phase2_findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self._report   = phase1_report
        self._findings = phase2_findings
        self.verbose   = verbose
        self._files: List[Dict[str, Any]] = phase1_report.get("files", [])

        # Build a quick lookup: file_path -> file_entry
        self._file_map: Dict[str, Dict[str, Any]] = {
            f["path"]: f for f in self._files if "path" in f
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_api_endpoints(self) -> List[Dict[str, Any]]:
        """Run the API-endpoint safety check on every Phase 2 finding.

        Returns
        -------
        List[dict]
            One :class:`APIEndpointResult` dict per input finding.
            Each dict also includes an ``"adjusted_finding"`` key with the
            finding updated for risk and confidence where relevant.

        Non-endpoint findings are returned unchanged (``is_api_endpoint=False``).
        """
        results: List[Dict[str, Any]] = []

        for finding in self._findings:
            result = self._check_one(finding)
            entry  = result.to_dict()
            entry["adjusted_finding"] = result.to_adjusted_finding()
            results.append(entry)

            if self.verbose and result.is_api_endpoint:
                self._log(
                    f"  [API  ] {finding.get('id', '?'):5s} "
                    f"{finding.get('file', '')}::{finding.get('item', '')} "
                    f"type={result.endpoint_type} "
                    f"deprecated={result.deprecated_signal} "
                    f"risk={result.adjusted_risk} "
                    f"conf={result.adjusted_confidence:.2f}"
                )

        api_count = sum(1 for r in results if r["is_api_endpoint"])
        self._log(
            f"APIEndpointChecker: {len(results)} finding(s) checked, "
            f"{api_count} identified as API endpoint(s)."
        )
        return results

    def get_adjusted_findings(self) -> List[Dict[str, Any]]:
        """Return only the (adjusted) finding dicts."""
        return [r["adjusted_finding"] for r in self.check_api_endpoints()]

    # ------------------------------------------------------------------
    # Per-finding logic
    # ------------------------------------------------------------------

    def _check_one(self, finding: Dict[str, Any]) -> APIEndpointResult:
        file_path = finding.get("file", "")
        symbol    = finding.get("item", "")
        ftype     = finding.get("type", "")
        fid       = finding.get("id", "?")

        # CRITICAL findings are never touched
        if finding.get("risk") == "CRITICAL":
            return self._passthrough(fid, finding)

        file_entry    = self._file_map.get(file_path, {})
        is_endpoint   = self._is_api_endpoint(file_path, symbol, file_entry)
        endpoint_type = self._detect_framework(file_entry) if is_endpoint else "unknown"
        versioned     = self._has_version(file_path, symbol)
        depr_signal   = self._has_deprecated_signal(symbol, file_path)

        if not is_endpoint:
            return self._passthrough(fid, finding)

        # Determine risk and confidence cap
        if depr_signal:
            adj_risk = "MEDIUM"
            conf_cap = self._DEPRECATED_CONFIDENCE_CAP
        else:
            adj_risk = "HIGH"
            conf_cap = self._API_CONFIDENCE_CAP

        original_conf = float(finding.get("confidence", 0.7))
        adj_conf      = min(original_conf, conf_cap)

        recommendation = self._build_recommendation(symbol, file_path, depr_signal, versioned)
        reason         = self._build_reason(endpoint_type, depr_signal, versioned)

        return APIEndpointResult(
            finding_id=fid,
            is_api_endpoint=True,
            endpoint_type=endpoint_type,
            versioned=versioned,
            deprecated_signal=depr_signal,
            recommendation=recommendation,
            adjusted_risk=adj_risk,
            adjusted_confidence=adj_conf,
            reason=reason,
            original_finding=finding,
        )

    @staticmethod
    def _passthrough(fid: str, finding: Dict[str, Any]) -> "APIEndpointResult":
        """Return a no-op result that leaves the finding unchanged."""
        return APIEndpointResult(
            finding_id=fid,
            is_api_endpoint=False,
            endpoint_type="unknown",
            versioned=False,
            deprecated_signal=False,
            recommendation="",
            adjusted_risk=finding.get("risk", "MEDIUM"),
            adjusted_confidence=float(finding.get("confidence", 0.7)),
            reason="",
            original_finding=finding,
        )

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _is_api_endpoint(
        self,
        file_path: str,
        symbol: str,
        file_entry: Dict[str, Any],
    ) -> bool:
        """Return ``True`` if this finding targets an API endpoint."""
        posix = file_path.replace("\\", "/").lower()

        # 1. File lives in an API-layer directory
        if any(frag in posix for frag in _API_PATH_FRAGMENTS):
            return True

        # 2. File name suggests routing
        stem = Path(file_path).stem.lower()
        if any(k in stem for k in ("route", "view", "endpoint", "handler", "controller")):
            return True

        # 3. Symbol name follows HTTP-verb conventions
        if symbol and _HTTP_VERB_PREFIX_RE.match(symbol):
            return True

        # 4. The file imports a web framework
        imports: List[str] = file_entry.get("imports", [])
        for imp in imports:
            top = imp.lstrip(".").split(".")[0].lower()
            if top in ("fastapi", "flask", "django", "aiohttp", "sanic",
                       "starlette", "tornado", "falcon", "bottle", "quart"):
                return True

        return False

    @staticmethod
    def _detect_framework(file_entry: Dict[str, Any]) -> str:
        """Return a framework label based on the file's imports."""
        imports: List[str] = file_entry.get("imports", [])
        tops = {imp.lstrip(".").split(".")[0].lower() for imp in imports}

        if "fastapi" in tops:
            return "fastapi"
        if "flask" in tops:
            return "flask"
        if "django" in tops:
            return "django"
        if "aiohttp" in tops:
            return "aiohttp"
        if "sanic" in tops:
            return "sanic"
        if "starlette" in tops:
            return "starlette"
        return "generic_rest"

    @staticmethod
    def _has_version(file_path: str, symbol: str) -> bool:
        return bool(
            _VERSION_RE.search(file_path)
            or (symbol and _VERSION_RE.search(symbol))
        )

    @staticmethod
    def _has_deprecated_signal(symbol: str, file_path: str) -> bool:
        # Split on non-alphanumeric boundaries so snake_case / paths work
        # e.g. "delete_legacy_v1" -> ["delete", "legacy", "v1"]
        def _segments(text: str) -> List[str]:
            return _re.split(r"[_\-./\\]", text.lower()) if text else []

        _DEPRECATED_WORDS = {"deprecated", "legacy", "old", "compat"}

        for seg in _segments(symbol) + _segments(file_path):
            if seg in _DEPRECATED_WORDS:
                return True
            if _re.fullmatch(r"v\d+", seg):   # v1, v2, v10 ...
                return True
        return False

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_recommendation(
        symbol: str,
        file_path: str,
        deprecated_signal: bool,
        versioned: bool,
    ) -> str:
        name = symbol or Path(file_path).stem

        if deprecated_signal:
            return (
                f"Do not delete '{name}' directly. "
                "Return HTTP 410 Gone with a migration message, then remove "
                "after a deprecation window (recommended: 3-6 months)."
            )
        if versioned:
            return (
                f"Preserve '{name}' until a new version is stable. "
                "Add a deprecation header (Deprecation: true, Sunset: <date>) "
                "and document the migration path in the API changelog."
            )
        return (
            f"Do not delete '{name}' without checking client usage. "
            "Audit access logs, add a deprecation notice, and give consumers "
            "at least one version cycle to migrate before removal."
        )

    @staticmethod
    def _build_reason(endpoint_type: str, deprecated_signal: bool, versioned: bool) -> str:
        parts = [f"External API endpoint ({endpoint_type})"]
        if deprecated_signal:
            parts.append("deprecated signal detected -- migration path required before removal")
        elif versioned:
            parts.append("versioned endpoint -- preserve until next major version")
        else:
            parts.append("external clients may depend on this")
        return ". ".join(parts) + "."

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Phase 3C  --  Configuration & Environment Checker
# ---------------------------------------------------------------------------

import re as _re

# Path fragments that indicate a configuration / environment file
_CONFIG_PATH_FRAGMENTS: Set[str] = {
    "config", "conf", "settings", "setting", "env", "environment",
    "options", "params", "parameters", "constants", "const",
    "secrets", "credentials", "credential",
}

# File stems that are almost always configuration
_CONFIG_STEMS: Set[str] = {
    "config", "configuration", "settings", "options", "constants",
    "env", "environment", "secrets", "credentials", "params", "parameters",
    "app_config", "app_settings", "base_settings", "dev_settings",
    "prod_settings", "local_settings",
}

# Import names that load / validate configuration at runtime
_CONFIG_IMPORTS: Set[str] = {
    "pydantic", "pydantic_settings", "dynaconf", "decouple", "environs",
    "dotenv", "python_dotenv", "python-dotenv", "hydra", "omegaconf",
    "confz", "configparser", "tomllib", "toml", "yaml", "dotmap",
    "strictyaml", "cerberus", "voluptuous", "marshmallow", "dataclasses_json",
    "django.conf", "flask", "fastapi", "starlette.config",
}

# Symbol-name regex patterns that suggest configuration objects
_CONFIG_SYMBOL_RE = _re.compile(
    r"\b(?:config|cfg|conf|settings?|options?|params?|constants?|env|secrets?)\b",
    _re.IGNORECASE,
)

_CAP_HIGH_IMPACT: float = 0.25
_CAP_MEDIUM_IMPACT: float = 0.40

_IMPACT_HIGH = "HIGH_IMPACT"
_IMPACT_MEDIUM = "MEDIUM_IMPACT"


@dataclass
class ConfigurationResult:
    """Verification result for a single Phase 2 finding against configuration heuristics.

    Attributes
    ----------
    finding_id:
        ``id`` of the Phase 2 finding.
    is_configuration:
        ``True`` when the item looks like a configuration / environment concern.
    config_type:
        Human-readable label for the kind of configuration detected,
        e.g. ``"config file"`` or ``"settings symbol"``.
    impact:
        ``"HIGH_IMPACT"`` or ``"MEDIUM_IMPACT"`` -- controls risk floor and
        confidence cap.
    adjusted_risk:
        Risk level after applying the configuration safety floor.
    adjusted_confidence:
        Confidence value after capping.
    reason:
        Free-text explanation of why the item is considered configuration.
    recommendation:
        Actionable advice for the reviewer.
    original_finding:
        The raw Phase 2 finding dict, unchanged.
    """

    finding_id: str
    is_configuration: bool
    config_type: str
    impact: str
    adjusted_risk: str
    adjusted_confidence: float
    reason: str
    recommendation: str
    original_finding: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id":          self.finding_id,
            "is_configuration":    self.is_configuration,
            "config_type":         self.config_type,
            "impact":              self.impact,
            "adjusted_risk":       self.adjusted_risk,
            "adjusted_confidence": round(self.adjusted_confidence, 4),
            "reason":              self.reason,
            "recommendation":      self.recommendation,
        }

    def to_adjusted_finding(self) -> Dict[str, Any]:
        """Return the original finding dict with risk/confidence overwritten."""
        out = dict(self.original_finding)
        out["risk"]       = self.adjusted_risk
        out["confidence"] = round(self.adjusted_confidence, 4)
        if "evidence" not in out or not isinstance(out["evidence"], dict):
            out["evidence"] = {}
        out["evidence"]["configuration_check"] = self.to_dict()
        return out


class ConfigurationChecker:
    """Phase 3C: flag findings that touch configuration / environment code.

    Configuration files are load-bearing at runtime.  Deleting or refactoring
    them without a migration plan can break deployments silently.  This checker
    applies two safety measures:

    * Caps confidence so the item cannot float into "safe to delete" territory.
    * Raises the risk floor so human review is always required.

    Parameters
    ----------
    phase1_report:
        The full Phase 1 JSON report (``{"files": [...], ...}``).
    phase2_findings:
        List of Phase 2 finding dicts.
    verbose:
        Print progress lines when ``True``.
    """

    # Risk ordering for floor enforcement
    _RISK_ORDER = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        phase2_findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self.phase1_report   = phase1_report
        self.phase2_findings = phase2_findings
        self.verbose         = verbose

        # Build a quick-lookup: path -> list-of-imports from Phase 1
        self._imports_by_path: Dict[str, List[str]] = {
            f["path"]: f.get("imports", [])
            for f in phase1_report.get("files", [])
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_configuration_usage(self) -> List[ConfigurationResult]:
        """Run configuration checks on every Phase 2 finding.

        Returns
        -------
        List[ConfigurationResult]
            One result per finding, in the same order as ``phase2_findings``.
        """
        results: List[ConfigurationResult] = []
        for finding in self.phase2_findings:
            result = self._check_one(finding)
            if result.is_configuration:
                self._log(
                    f"[config] {result.finding_id} -> {result.config_type} "
                    f"({result.impact}): {result.reason}"
                )
            results.append(result)
        return results

    def get_adjusted_findings(self) -> List[Dict[str, Any]]:
        """Return all Phase 2 findings with configuration adjustments applied."""
        return [r.to_adjusted_finding() for r in self.check_configuration_usage()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_one(self, finding: Dict[str, Any]) -> ConfigurationResult:
        finding_id = finding.get("id", "UNKNOWN")
        file_path  = finding.get("file_path", "")
        symbol     = finding.get("symbol_name") or finding.get("name", "")
        orig_risk  = finding.get("risk", "LOW")
        orig_conf  = float(finding.get("confidence", 0.5))

        if not self._is_configuration(file_path, symbol, finding):
            return self._passthrough(finding_id, orig_risk, orig_conf, finding)

        config_type    = self._classify_config_type(file_path, symbol, finding)
        impact         = self._assess_impact(config_type, file_path, symbol)
        adj_risk       = self._adjust_risk(orig_risk, impact)
        adj_conf       = self._cap_confidence(orig_conf, impact)
        reason         = self._build_reason(config_type, impact, file_path, symbol)
        recommendation = self._build_recommendation(config_type, impact)

        return ConfigurationResult(
            finding_id=finding_id,
            is_configuration=True,
            config_type=config_type,
            impact=impact,
            adjusted_risk=adj_risk,
            adjusted_confidence=adj_conf,
            reason=reason,
            recommendation=recommendation,
            original_finding=finding,
        )

    def _passthrough(
        self,
        finding_id: str,
        risk: str,
        confidence: float,
        finding: Dict[str, Any],
    ) -> ConfigurationResult:
        return ConfigurationResult(
            finding_id=finding_id,
            is_configuration=False,
            config_type="",
            impact="",
            adjusted_risk=risk,
            adjusted_confidence=confidence,
            reason="",
            recommendation="",
            original_finding=finding,
        )

    def _is_configuration(
        self,
        file_path: str,
        symbol: str,
        finding: Dict[str, Any],
    ) -> bool:
        """Return True when any configuration signal is found."""
        # 1. Path-fragment match
        segments = _re.split(r"[/\\]", file_path.lower())
        for seg in segments:
            stem = Path(seg).stem
            if stem in _CONFIG_STEMS:
                return True
            for frag in _CONFIG_PATH_FRAGMENTS:
                if frag in stem:
                    return True

        # 2. Symbol-name match
        if symbol and _CONFIG_SYMBOL_RE.search(symbol):
            return True

        # 3. Config-framework import in the same file
        file_imports = self._imports_by_path.get(file_path, [])
        for imp in file_imports:
            for cfg_imp in _CONFIG_IMPORTS:
                if cfg_imp in imp.lower():
                    return True

        # 4. Finding type is an unused import that looks like a config loader
        if finding.get("type") == "unused_import":
            import_name = finding.get("import_name", "").lower()
            for cfg_imp in _CONFIG_IMPORTS:
                if cfg_imp in import_name:
                    return True

        return False

    def _classify_config_type(
        self,
        file_path: str,
        symbol: str,
        finding: Dict[str, Any],
    ) -> str:
        if finding.get("type") == "unused_import":
            return "config import"

        segments = _re.split(r"[/\\]", file_path.lower())
        for seg in segments:
            stem = Path(seg).stem
            if stem in _CONFIG_STEMS:
                return "config file"
            for frag in _CONFIG_PATH_FRAGMENTS:
                if frag in stem:
                    return "config file"

        file_imports = self._imports_by_path.get(file_path, [])
        for imp in file_imports:
            for cfg_imp in _CONFIG_IMPORTS:
                if cfg_imp in imp.lower():
                    return "settings module"

        if symbol and _CONFIG_SYMBOL_RE.search(symbol):
            return "settings symbol"

        return "config-related code"

    def _assess_impact(self, config_type: str, file_path: str, symbol: str) -> str:
        if config_type in {"config file", "settings module", "config import"}:
            return _IMPACT_HIGH

        # Secrets / credentials / env patterns always HIGH
        path_lower = file_path.lower()
        if any(kw in path_lower for kw in ("secret", "credential", "env")):
            return _IMPACT_HIGH

        if symbol:
            sym_lower = symbol.lower()
            if any(kw in sym_lower for kw in ("secret", "credential", "token", "password", "api_key")):
                return _IMPACT_HIGH

        return _IMPACT_MEDIUM

    def _adjust_risk(self, orig_risk: str, impact: str) -> str:
        """Enforce risk floor: HIGH_IMPACT -> min HIGH; MEDIUM_IMPACT -> min MEDIUM."""
        floors = {_IMPACT_HIGH: "HIGH", _IMPACT_MEDIUM: "MEDIUM"}
        floor  = floors.get(impact, "LOW")
        try:
            orig_idx  = self._RISK_ORDER.index(orig_risk)
            floor_idx = self._RISK_ORDER.index(floor)
        except ValueError:
            return floor
        return self._RISK_ORDER[max(orig_idx, floor_idx)]

    def _cap_confidence(self, orig_conf: float, impact: str) -> float:
        cap = _CAP_HIGH_IMPACT if impact == _IMPACT_HIGH else _CAP_MEDIUM_IMPACT
        return min(orig_conf, cap)

    @staticmethod
    def _build_reason(
        config_type: str,
        impact: str,
        file_path: str,
        symbol: str,
    ) -> str:
        parts = [f"Identified as {config_type}"]
        if impact == _IMPACT_HIGH:
            parts.append(
                "removal could break runtime configuration, "
                "environment variable loading, or secret injection"
            )
        else:
            parts.append(
                "may affect application behaviour if removed without "
                "verifying all consumers"
            )
        if symbol:
            parts.append(f"flagged symbol: '{symbol}'")
        return ". ".join(parts) + "."

    @staticmethod
    def _build_recommendation(config_type: str, impact: str) -> str:
        if impact == _IMPACT_HIGH:
            return (
                f"Do not delete this {config_type} without a full environment audit. "
                "Check all deployment environments (dev/staging/prod), "
                "CI/CD pipelines, and container configurations for references. "
                "Coordinate with the infrastructure or DevOps team before removal."
            )
        return (
            f"Review all callers of this {config_type} before removing. "
            "Ensure no environment-specific code path depends on this value "
            "at startup or during configuration loading."
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Phase 3D  --  Database Migration Checker
# ---------------------------------------------------------------------------

# Folder names that contain database / migration artefacts
_DB_PATH_FRAGMENTS: Set[str] = {
    "migrations", "migration", "migrate",
    "db", "database", "databases",
    "alembic", "versions",
    "schema", "schemas",
    "models",
}

# File-stem patterns that identify migration files
# e.g. 0001_initial.py, 0023_add_email_column.py, V2__create_table.sql
_MIGRATION_STEM_RE = _re.compile(
    r"^(?:\d{4,}_|v\d+__)",  # Django / Alembic / Flyway-style prefixes
    _re.IGNORECASE,
)

# Python imports from database / ORM / migration libraries
_DB_IMPORTS: Set[str] = {
    # Django
    "django.db", "django.db.models", "django.db.migrations",
    "django.contrib.contenttypes",
    # SQLAlchemy
    "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext",
    "sqlalchemy.schema", "sqlalchemy.types",
    # Alembic
    "alembic", "alembic.op", "alembic.context",
    # Other ORMs
    "peewee", "tortoise", "databases",
    "mongoengine", "motor", "pymongo",
    "cassandra", "aiopg", "asyncpg", "psycopg2",
    "pymysql", "aiomysql", "cx_oracle",
}

# Source-code patterns that signal schema / migration definitions
# Each entry: (human-readable label, compiled regex)
_DB_CODE_PATTERNS: List[tuple] = [
    # Alembic
    ("alembic upgrade function",     _re.compile(r"\bdef\s+upgrade\s*\(", _re.MULTILINE)),
    ("alembic downgrade function",   _re.compile(r"\bdef\s+downgrade\s*\(", _re.MULTILINE)),
    # Django ORM
    ("django migration class",       _re.compile(r"\bclass\s+Migration\b", _re.MULTILINE)),
    ("django model Meta class",      _re.compile(r"\bclass\s+Meta\s*:", _re.MULTILINE)),
    ("django migration operations",  _re.compile(r"\boperations\s*=\s*\[", _re.MULTILINE)),
    # SQLAlchemy
    ("sqlalchemy Table definition",  _re.compile(r"\bTable\s*\(", _re.MULTILINE)),
    ("sqlalchemy Column definition",  _re.compile(r"\bColumn\s*\(", _re.MULTILINE)),
    ("sqlalchemy relationship",       _re.compile(r"\brelationship\s*\(", _re.MULTILINE)),
    ("sqlalchemy declarative base",   _re.compile(r"\bDeclarativeBase\b|\bdeclarative_base\s*\(", _re.MULTILINE)),
    # Generic
    ("migrate function",              _re.compile(r"\bdef\s+migrate\s*\(", _re.MULTILINE)),
    ("schema definition",             _re.compile(r"\bschema\s*=\s*\{", _re.MULTILINE | _re.IGNORECASE)),
]

_DB_WARNING = (
    "[!] CRITICAL: This is database-related code.\n"
    "    Deleting will cause:\n"
    "      - Data loss\n"
    "      - Schema mismatch\n"
    "      - Migration failures\n"
    "      - Production downtime\n"
    "\n"
    "    DO NOT DELETE without database expert review."
)


class DatabaseMigrationChecker:
    """Phase 3D: mark database / migration findings as CRITICAL -- never delete.

    Database migrations are permanent historical records of schema changes.
    Deleting them corrupts the migration graph and can cause data loss or
    production downtime.  This checker hard-blocks any such finding by
    setting ``risk="CRITICAL"`` and ``confidence=0.0`` (zero confidence it
    is safe to remove).

    Parameters
    ----------
    phase1_report:
        The full Phase 1 JSON report (``{"files": [...], ...}``).
    phase2_findings:
        List of Phase 2 finding dicts.
    verbose:
        Print progress lines when ``True``.
    """

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        phase2_findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self.phase1_report   = phase1_report
        self.phase2_findings = phase2_findings
        self.verbose         = verbose

        # path -> raw source text (for pattern scanning); empty string if unavailable
        self._source_by_path: Dict[str, str] = {
            f["path"]: f.get("source", "") or ""
            for f in phase1_report.get("files", [])
        }

        # path -> imports list
        self._imports_by_path: Dict[str, List[str]] = {
            f["path"]: f.get("imports", [])
            for f in phase1_report.get("files", [])
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_database_safety(self) -> List[Dict[str, Any]]:
        """Evaluate every Phase 2 finding for database safety.

        Returns
        -------
        List[dict]
            One adjusted finding dict per input finding.  Database-related
            findings have ``risk="CRITICAL"`` and ``confidence=0.0``; all
            others are returned unchanged.
        """
        results: List[Dict[str, Any]] = []
        for finding in self.phase2_findings:
            result = self._check_one(finding)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_one(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        file_path  = finding.get("file_path", "")
        symbol     = finding.get("symbol_name") or finding.get("name", "")
        finding_id = finding.get("id", "UNKNOWN")

        db_type = self._detect_db_type(file_path, symbol, finding)
        if db_type is None:
            return finding  # passthrough -- not database-related

        reason = self._build_reason(db_type, file_path, symbol)
        self._log(
            f"[!] DATABASE_CRITICAL {finding_id}: {db_type} in '{file_path}'"
        )
        if self.verbose:
            for line in _DB_WARNING.splitlines():
                self._log(f"    {line}")

        out = dict(finding)
        out["risk"]       = "CRITICAL"
        out["confidence"] = 0.0

        if "evidence" not in out or not isinstance(out["evidence"], dict):
            out["evidence"] = {}
        out["evidence"]["database_check"] = {
            "is_database_critical": True,
            "db_type":              db_type,
            "reason":               reason,
            "warning":              _DB_WARNING,
            "recommendation": (
                "DATABASE MIGRATION -- DELETING CAUSES DATA LOSS. "
                "Migrations are permanent historical records. "
                "Schema changes are irreversible. "
                "Even old migrations matter -- they define the rollback path. "
                "DO NOT DELETE without a database expert review, "
                "a full backup, and a tested rollback plan."
            ),
        }
        return out

    def _detect_db_type(
        self,
        file_path: str,
        symbol: str,
        finding: Dict[str, Any],
    ) -> Optional[str]:
        """Return a human-readable db type label, or None if not db-related."""

        # 1. Migration file by stem naming convention
        stem = Path(file_path).stem
        if _MIGRATION_STEM_RE.match(stem):
            return "migration file"

        # 2. Path-fragment match (migrations/, db/, alembic/versions/, ...)
        segments = set(_re.split(r"[/\\]", file_path.lower()))
        for seg in segments:
            seg_stem = Path(seg).stem if "." in seg else seg
            if seg_stem in _DB_PATH_FRAGMENTS:
                return f"database path ({seg_stem}/)"

        # 3. ORM / migration library import in the same file
        file_imports = self._imports_by_path.get(file_path, [])
        for imp in file_imports:
            imp_lower = imp.lower().lstrip(".")
            for db_imp in _DB_IMPORTS:
                if db_imp in imp_lower:
                    return f"ORM import ({db_imp})"

        # 4. Source-code pattern scan
        source = self._source_by_path.get(file_path, "")
        if source:
            for label, pattern in _DB_CODE_PATTERNS:
                if pattern.search(source):
                    return label

        # 5. Symbol-name heuristics
        if symbol:
            sym_lower = symbol.lower()
            db_symbol_keywords = (
                "migration", "migrate", "schema", "table", "column",
                "model", "orm", "alembic", "upgrade", "downgrade",
            )
            for kw in db_symbol_keywords:
                if kw in sym_lower:
                    return f"database symbol ({symbol})"

        return None

    @staticmethod
    def _build_reason(db_type: str, file_path: str, symbol: str) -> str:
        parts = [f"DATABASE_CRITICAL: identified as {db_type}"]
        parts.append(
            "deleting database migrations or schema definitions causes "
            "irreversible data loss, schema drift, and migration failures"
        )
        if symbol:
            parts.append(f"flagged symbol: '{symbol}'")
        return ". ".join(parts) + "."

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)


# ---------------------------------------------------------------------------
# Phase 3E  --  Dynamic Import Detector
# ---------------------------------------------------------------------------

# Each entry: (human-readable label, compiled regex that fires on source text)
# Ordered from most specific to least specific so the first match gives the
# most informative label.
_DYNAMIC_PATTERNS: List[tuple] = [
    # importlib
    ("importlib.import_module call",
     _re.compile(r"\bimportlib\.import_module\s*\(", _re.MULTILINE)),
    ("importlib.util.spec_from_file_location",
     _re.compile(r"\bimportlib\.util\.spec_from_file_location\s*\(", _re.MULTILINE)),

    # built-in __import__
    ("__import__ call",
     _re.compile(r"\b__import__\s*\(", _re.MULTILINE)),

    # getattr on a module object used as a loader (getattr(mod, name))
    ("getattr dynamic attribute lookup",
     _re.compile(r"\bgetattr\s*\(\s*\w+\s*,\s*\w+", _re.MULTILINE)),

    # globals() / locals() used for dynamic dispatch
    ("globals() dynamic dispatch",
     _re.compile(r"\bglobals\s*\(\s*\)\s*(?:\.get|\.pop|\[)", _re.MULTILINE)),
    ("locals() dynamic dispatch",
     _re.compile(r"\blocals\s*\(\s*\)\s*(?:\.get|\.pop|\[)", _re.MULTILINE)),

    # pkgutil / pkg_resources discovery
    ("pkgutil plugin discovery",
     _re.compile(r"\bpkgutil\.import_module\b|\bpkgutil\.iter_modules\b", _re.MULTILINE)),
    ("pkg_resources plugin discovery",
     _re.compile(r"\bpkg_resources\.load_entry_point\b|\bentry_points\s*\(", _re.MULTILINE)),

    # Common factory / registry patterns
    ("string-keyed factory pattern",
     _re.compile(
         r"(?:REGISTRY|HANDLERS?|PLUGINS?|LOADERS?|DISPATCH|COMMANDS?|STRATEGIES?)"
         r"\s*(?:\[|\.\s*get\s*\()",
         _re.MULTILINE | _re.IGNORECASE,
     )),

    # eval / exec importing modules by string
    ("eval/exec dynamic execution",
     _re.compile(r"\b(?:eval|exec)\s*\(", _re.MULTILINE)),

    # sys.modules manipulation
    ("sys.modules manipulation",
     _re.compile(r"\bsys\.modules\s*\[", _re.MULTILINE)),

    # __subclasses__ walk (plugin discovery via inheritance)
    ("__subclasses__ plugin walk",
     _re.compile(r"\b__subclasses__\s*\(\s*\)", _re.MULTILINE)),
]

# How much to subtract from confidence when a dynamic pattern is found
_DYNAMIC_CONF_PENALTY: float = 0.20

# Minimum confidence floor after the penalty (never go below 0)
_DYNAMIC_CONF_FLOOR: float = 0.0

# Risk floor for dynamically-loaded items
_DYNAMIC_RISK_FLOOR = "HIGH"

# Risk order for floor enforcement (re-use from ConfigurationChecker logic)
_RISK_ORDER_DYN = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class DynamicImportDetector:
    """Phase 3E: lower confidence for findings that may be dynamically imported.

    Static analysis cannot follow ``importlib.import_module()``,
    ``__import__()``, ``globals().get(name)()``, or string-keyed registries.
    If any such pattern exists in the *same file* as a flagged symbol, we
    cannot prove the symbol is truly unused -- it may be loaded at runtime
    by name.

    Adjustments applied when a dynamic pattern is detected:

    * ``confidence``  reduced by :data:`_DYNAMIC_CONF_PENALTY` (0.20), floored at 0.
    * ``risk``        raised to at least ``"HIGH"`` (never lowered).
    * ``evidence["dynamic_check"]`` populated with pattern label and reason.

    Parameters
    ----------
    phase1_report:
        The full Phase 1 JSON report (``{"files": [...], ...}``).
    phase2_findings:
        List of Phase 2 finding dicts.
    verbose:
        Print one progress line per flagged finding when ``True``.
    """

    def __init__(
        self,
        phase1_report: Dict[str, Any],
        phase2_findings: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> None:
        self.phase1_report   = phase1_report
        self.phase2_findings = phase2_findings
        self.verbose         = verbose

        # path -> raw source text; empty string when unavailable
        self._source_by_path: Dict[str, str] = {
            f["path"]: f.get("source", "") or ""
            for f in phase1_report.get("files", [])
        }

        # Pre-scan every file and cache which dynamic pattern (if any) fired.
        # This avoids re-running all regexes for every finding that shares
        # the same file.
        self._dynamic_signal_cache: Dict[str, Optional[str]] = {
            path: self._scan_source(source)
            for path, source in self._source_by_path.items()
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_dynamic_imports(self) -> List[Dict[str, Any]]:
        """Evaluate every Phase 2 finding for dynamic-import risk.

        Returns
        -------
        List[dict]
            One finding dict per input.  Findings whose file contains a
            dynamic-import pattern have lowered confidence and raised risk;
            all others are returned unchanged.
        """
        results: List[Dict[str, Any]] = []
        for finding in self.phase2_findings:
            results.append(self._check_one(finding))
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_one(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        file_path  = finding.get("file_path", "")
        finding_id = finding.get("id", "UNKNOWN")
        orig_risk  = finding.get("risk", "LOW")
        orig_conf  = float(finding.get("confidence", 0.5))

        pattern_label = self._dynamic_signal_cache.get(file_path)

        # Also check the project-wide source for files that import this
        # module by string (best-effort: scan *all* sources for the stem)
        if pattern_label is None:
            pattern_label = self._scan_project_for_string_ref(file_path)

        if pattern_label is None:
            return finding  # no dynamic signal -- passthrough

        adj_conf = max(orig_conf - _DYNAMIC_CONF_PENALTY, _DYNAMIC_CONF_FLOOR)
        adj_risk = self._raise_risk(orig_risk, _DYNAMIC_RISK_FLOOR)
        reason   = (
            f"May be dynamically imported -- static analysis misses it. "
            f"Pattern detected: {pattern_label}."
        )

        self._log(
            f"[dynamic] {finding_id} in '{file_path}': "
            f"{pattern_label} (conf {orig_conf:.2f} -> {adj_conf:.2f}, "
            f"risk {orig_risk} -> {adj_risk})"
        )

        out = dict(finding)
        out["risk"]       = adj_risk
        out["confidence"] = round(adj_conf, 4)

        if "evidence" not in out or not isinstance(out["evidence"], dict):
            out["evidence"] = {}
        out["evidence"]["dynamic_check"] = {
            "is_dynamically_loaded":   True,
            "pattern_detected":        pattern_label,
            "confidence_penalty":      _DYNAMIC_CONF_PENALTY,
            "original_confidence":     orig_conf,
            "original_risk":           orig_risk,
            "reason":                  reason,
            "recommendation": (
                "DYNAMICALLY_LOADED: static analysis cannot prove this symbol "
                "is unused. It may be referenced by name at runtime via "
                "importlib, __import__, getattr, a string registry, or a "
                "plugin loader. Requires human review before removal."
            ),
        }
        return out

    @staticmethod
    def _scan_source(source: str) -> Optional[str]:
        """Return the label of the first dynamic pattern found, or None."""
        if not source:
            return None
        for label, pattern in _DYNAMIC_PATTERNS:
            if pattern.search(source):
                return label
        return None

    def _scan_project_for_string_ref(self, file_path: str) -> Optional[str]:
        """Check whether *any* file in the project references this module's
        stem or dotted path as a string literal (best-effort).

        Catches patterns like::

            importlib.import_module("myapp.utils.helpers")
            __import__("helpers")
        """
        stem     = Path(file_path).stem
        # Build a dotted module path from the file path for a tighter match
        parts    = _re.split(r"[/\\]", file_path)
        dot_path = ".".join(Path(p).stem if p.endswith((".py", ".js", ".ts")) else p
                            for p in parts).strip(".")

        string_ref_re = _re.compile(
            r"""['"]\s*(?:""" + _re.escape(dot_path) + r"""|""" + _re.escape(stem) + r""")\s*['"]""",
            _re.MULTILINE,
        )
        loader_re = _re.compile(
            r"\b(?:importlib\.import_module|__import__|importlib\.util\.spec_from_file_location)\s*\(",
            _re.MULTILINE,
        )

        for path, source in self._source_by_path.items():
            if path == file_path or not source:
                continue
            # Only flag when the string reference co-occurs with a loader call
            if string_ref_re.search(source) and loader_re.search(source):
                return "string-literal module reference with loader call"

        return None

    @staticmethod
    def _raise_risk(current: str, floor: str) -> str:
        """Return the higher of *current* and *floor* in the risk order."""
        try:
            cur_idx   = _RISK_ORDER_DYN.index(current)
            floor_idx = _RISK_ORDER_DYN.index(floor)
        except ValueError:
            return floor
        return _RISK_ORDER_DYN[max(cur_idx, floor_idx)]

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
