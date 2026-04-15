# Spec Writer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based SpecWriterAgent that converts natural-language input into structured JSON specs, integrated with the existing EventBus/AgentRegistry/StateStore/MemoryAgent architecture.

**Architecture:** Hybrid section-header + keyword parser (SpecParser) feeds a Pydantic SpecDoc through context enrichment (SpecEnricher via MemoryAgent), validation (SpecValidator), and disk I/O (SpecFormatter). No LLM calls. Registered as `"spec"` in AgentRegistry, dispatched via `orchestrator spec <subcommand>`. AgentRegistry.get() gains `**kwargs` so the orchestrator can pass itself to the SpecWriterAgent.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, existing EventBus/AgentRegistry/StateStore

---

## File Map

**New files:**
- `agents/spec_writer/__init__.py`
- `agents/spec_writer/schema.py` — Pydantic v2 SpecDoc, Feature, ProjectSection, etc.
- `agents/spec_writer/parser.py` — SpecParser: section-header + keyword heuristics → SpecDoc
- `agents/spec_writer/enricher.py` — SpecEnricher: queries MemoryAgent via registry
- `agents/spec_writer/validator.py` — SpecValidator: completeness/consistency, never raises
- `agents/spec_writer/formatter.py` — SpecFormatter: JSON, Markdown, disk I/O
- `agents/spec_writer/agent.py` — SpecWriterAgent (name="spec")
- `agents/spec_writer/tests/__init__.py`
- `agents/spec_writer/tests/test_parser.py`
- `agents/spec_writer/tests/test_enricher.py`
- `agents/spec_writer/tests/test_validator.py`
- `agents/spec_writer/tests/test_formatter.py`
- `agents/spec_writer/tests/test_agent.py`

**Modified files:**
- `agents/orchestrator/events.py` — add SpecCreated, SpecValidated, SpecUpdated, SpecFailed
- `agents/orchestrator/registry.py` — add `**kwargs` to `get()`
- `agents/orchestrator/orchestrator.py` — add `"spec"` to INTENT_MAP, pass registry for spec
- `agents/orchestrator/tests/test_registry.py` — add kwargs forwarding test
- `agents/orchestrator/tests/test_orchestrator.py` — add spec dispatch test
- `agents/orchestrator/tests/test_events.py` — add spec event tests

---

### Task 1: Schema

**Files:**
- Create: `agents/spec_writer/__init__.py`
- Create: `agents/spec_writer/tests/__init__.py`
- Create: `agents/spec_writer/schema.py`

- [ ] **Step 1: Create package init files**

`agents/spec_writer/__init__.py`:
```python
"""Spec Writer Agent package."""
```

`agents/spec_writer/tests/__init__.py`:
```python
```

- [ ] **Step 2: Write `agents/spec_writer/schema.py`**

```python
"""
agents/spec_writer/schema.py
============================
Pydantic v2 models for the SpecDoc format.

All fields are Optional or have defaults so partial specs are valid.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class InputSection(BaseModel):
    raw_description: str = ""


class Feature(BaseModel):
    id: str = ""
    name: str = "TODO"
    description: str = "TODO"
    acceptance_criteria: List[str] = Field(default_factory=list)
    priority: Literal["must", "should", "could"] = "should"
    estimated_complexity: Literal["low", "medium", "high"] = "medium"


class ProjectSection(BaseModel):
    name: str = "TODO"
    type: str = "TODO"  # api|frontend|cli|library|fullstack|TODO
    language: str = "TODO"
    framework: str = "TODO"


class TechnicalSpec(BaseModel):
    dependencies: List[str] = Field(default_factory=list)
    architecture_notes: str = ""
    database_schema: Dict[str, Any] = Field(default_factory=dict)
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    file_structure: Dict[str, Any] = Field(default_factory=dict)


class Constraints(BaseModel):
    performance: List[str] = Field(default_factory=list)
    security: List[str] = Field(default_factory=list)
    compatibility: List[str] = Field(default_factory=list)


class ContextApplied(BaseModel):
    patterns_used: List[str] = Field(default_factory=list)
    decisions_referenced: List[str] = Field(default_factory=list)


class SpecDoc(BaseModel):
    spec_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: Literal["draft", "validated", "failed"] = "draft"
    input: InputSection = Field(default_factory=InputSection)
    project: ProjectSection = Field(default_factory=ProjectSection)
    features: List[Feature] = Field(default_factory=list)
    technical: TechnicalSpec = Field(default_factory=TechnicalSpec)
    constraints: Constraints = Field(default_factory=Constraints)
    context_applied: ContextApplied = Field(default_factory=ContextApplied)
    warnings: List[str] = Field(default_factory=list)
```

- [ ] **Step 3: Verify schema imports**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -c "from agents.spec_writer.schema import SpecDoc; s = SpecDoc(); print(s.status)"
```
Expected output: `draft`

- [ ] **Step 4: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/__init__.py agents/spec_writer/tests/__init__.py agents/spec_writer/schema.py
git commit -m "feat(spec): add SpecDoc Pydantic v2 schema"
```

---

### Task 2: SpecParser — section-header extraction

**Files:**
- Create: `agents/spec_writer/parser.py`
- Create: `agents/spec_writer/tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

`agents/spec_writer/tests/test_parser.py`:
```python
"""Tests for agents.spec_writer.parser.SpecParser."""
import pytest
from agents.spec_writer.parser import SpecParser


# ── Section-header extraction ─────────────────────────────────────────────────

def test_section_header_extracts_language():
    text = "## Tech Stack\n- python\n- fastapi"
    spec = SpecParser().parse(text)
    assert spec.project.language == "python"


def test_section_header_extracts_framework():
    text = "## Tech Stack\n- python\n- fastapi"
    spec = SpecParser().parse(text)
    assert spec.project.framework == "fastapi"


def test_section_header_extracts_features_from_requirements():
    text = "## Requirements\n- User can log in\n- User can log out"
    spec = SpecParser().parse(text)
    assert len(spec.features) == 2
    assert spec.features[0].description == "User can log in"
    assert spec.features[1].description == "User can log out"


def test_section_header_extracts_acceptance_criteria():
    text = "## Requirements\n- Implement login\n## Acceptance Criteria\n- Returns 200\n- Invalid password returns 401"
    spec = SpecParser().parse(text)
    assert "Returns 200" in spec.features[-1].acceptance_criteria


def test_section_header_extracts_performance_constraint():
    text = "## Constraints\n- Response time under 200ms"
    spec = SpecParser().parse(text)
    assert len(spec.constraints.performance) == 1
    assert "200ms" in spec.constraints.performance[0]


def test_section_header_extracts_security_constraint():
    text = "## Constraints\n- All endpoints must use HTTPS\n- Auth required"
    spec = SpecParser().parse(text)
    assert len(spec.constraints.security) >= 1


def test_feature_ids_are_sequential():
    text = "## Requirements\n- Feature A\n- Feature B\n- Feature C"
    spec = SpecParser().parse(text)
    assert [f.id for f in spec.features] == ["F001", "F002", "F003"]


def test_raw_description_stored():
    text = "Build a REST API"
    spec = SpecParser().parse(text)
    assert spec.input.raw_description == text
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_parser.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError` (parser.py doesn't exist)

- [ ] **Step 3: Write `agents/spec_writer/parser.py`**

```python
"""
agents/spec_writer/parser.py
=============================
SpecParser — hybrid section-header + keyword heuristic extractor.

parse(text) -> SpecDoc. Never raises. Vague input produces warnings.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from agents.spec_writer.schema import (
    Constraints, ContextApplied, Feature, InputSection,
    ProjectSection, SpecDoc, TechnicalSpec,
)

# ── Compiled patterns ──────────────────────────────────────────────────────────

_SECTION_HEADER = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)
_LIST_ITEM = re.compile(r'^[ \t]*[-*]\s+(.+)$|^[ \t]*\d+\.\s+(.+)$', re.MULTILINE)

_LANGUAGE = re.compile(
    r'\b(python|typescript|javascript|go|rust|java|kotlin|swift|php|ruby)\b',
    re.IGNORECASE,
)
_FRAMEWORK = re.compile(
    r'\b(fastapi|flask|django|next(?:\.js|js)?|express|vue|svelte|laravel|rails|spring|gin|fiber)\b',
    re.IGNORECASE,
)
_PROJECT_TYPES: List[Tuple[str, re.Pattern]] = [
    ("fullstack", re.compile(r'\b(fullstack|full.stack|full stack)\b', re.IGNORECASE)),
    ("api",       re.compile(r'\b(api|rest(?:ful)?|graphql|grpc)\b', re.IGNORECASE)),
    ("cli",       re.compile(r'\b(cli|command.line|terminal)\b', re.IGNORECASE)),
    ("frontend",  re.compile(r'\b(frontend|front.end|webapp|web app)\b', re.IGNORECASE)),
    ("library",   re.compile(r'\b(library|lib|package|module|sdk)\b', re.IGNORECASE)),
]
_PRIORITY_MUST  = re.compile(r'\bmust\b', re.IGNORECASE)
_PRIORITY_COULD = re.compile(r'\b(could|nice.to.have)\b', re.IGNORECASE)
_SECURITY_WORDS = re.compile(
    r'\b(security|auth(?:en)?|https|ssl|encrypt|jwt|oauth)\b', re.IGNORECASE
)

_H_GOAL         = re.compile(r'(goals?|doel|user stor|purpose)', re.IGNORECASE)
_H_REQUIREMENTS = re.compile(r'(requirements?|eisen?|functioneel|features?)', re.IGNORECASE)
_H_TECH         = re.compile(r'(tech(?:nical)?|stack|dependencies|afhankelijkheden)', re.IGNORECASE)
_H_CONSTRAINTS  = re.compile(r'(constraints?|beperkingen?|non.functional)', re.IGNORECASE)
_H_ACCEPTANCE   = re.compile(r'(acceptance.criteria|acceptatiecriteria)', re.IGNORECASE)


def _list_items(text: str) -> List[str]:
    return [(a or b).strip() for a, b in _LIST_ITEM.findall(text) if (a or b).strip()]


def _feature_priority(text: str) -> str:
    if _PRIORITY_MUST.search(text):
        return "must"
    if _PRIORITY_COULD.search(text):
        return "could"
    return "should"


def _normalise_framework(raw: str) -> str:
    norm = raw.lower()
    return norm.replace("next.js", "next").replace("nextjs", "next")


class SpecParser:
    """Converts free-form text to a SpecDoc. Never raises."""

    def parse(self, text: str) -> SpecDoc:
        spec = SpecDoc(input=InputSection(raw_description=text or ""))

        if not text or not text.strip():
            spec.warnings.append("Input is empty — all fields set to TODO")
            return spec

        sections = self._split_sections(text)
        self._apply_sections(spec, sections)
        self._apply_heuristics(spec, text)
        self._number_features(spec)
        self._add_missing_warnings(spec)
        return spec

    # ── Section extraction ─────────────────────────────────────────────────────

    def _split_sections(self, text: str) -> Dict[str, str]:
        parts: Dict[str, List[str]] = {"_preamble": []}
        current = "_preamble"
        for line in text.splitlines():
            m = _SECTION_HEADER.match(line)
            if m:
                current = m.group(1).strip()
                parts.setdefault(current, [])
            else:
                parts.setdefault(current, []).append(line)
        return {k: "\n".join(v) for k, v in parts.items()}

    def _apply_sections(self, spec: SpecDoc, sections: Dict[str, str]) -> None:
        acceptance_buffer: List[str] = []
        for header, body in sections.items():
            if header == "_preamble":
                continue
            if _H_GOAL.search(header):
                items = _list_items(body)
                if items:
                    for item in items:
                        spec.features.append(Feature(
                            name=item[:60],
                            description=item,
                            priority=_feature_priority(item),
                        ))
                elif body.strip():
                    spec.project.name = body.strip().splitlines()[0][:80]
            elif _H_REQUIREMENTS.search(header):
                for item in _list_items(body):
                    spec.features.append(Feature(
                        name=item[:60],
                        description=item,
                        priority=_feature_priority(item),
                    ))
            elif _H_TECH.search(header):
                for item in _list_items(body):
                    m_lang = _LANGUAGE.search(item)
                    m_fw = _FRAMEWORK.search(item)
                    if m_lang and spec.project.language == "TODO":
                        spec.project.language = m_lang.group(1).lower()
                    elif m_fw and spec.project.framework == "TODO":
                        spec.project.framework = _normalise_framework(m_fw.group(1))
                    else:
                        spec.technical.dependencies.append(item)
                if body.strip():
                    spec.technical.architecture_notes = body.strip()[:500]
            elif _H_CONSTRAINTS.search(header):
                for item in _list_items(body):
                    if _SECURITY_WORDS.search(item):
                        spec.constraints.security.append(item)
                    else:
                        spec.constraints.performance.append(item)
            elif _H_ACCEPTANCE.search(header):
                acceptance_buffer.extend(_list_items(body))

        if acceptance_buffer and spec.features:
            spec.features[-1].acceptance_criteria = acceptance_buffer

    # ── Keyword heuristics ─────────────────────────────────────────────────────

    def _apply_heuristics(self, spec: SpecDoc, text: str) -> None:
        if spec.project.language == "TODO":
            m = _LANGUAGE.search(text)
            if m:
                spec.project.language = m.group(1).lower()

        if spec.project.framework == "TODO":
            m = _FRAMEWORK.search(text)
            if m:
                spec.project.framework = _normalise_framework(m.group(1))

        if spec.project.type == "TODO":
            for ptype, pattern in _PROJECT_TYPES:
                if pattern.search(text):
                    spec.project.type = ptype
                    break

        if not spec.features:
            for item in _list_items(text):
                spec.features.append(Feature(
                    name=item[:60],
                    description=item,
                    priority=_feature_priority(item),
                ))

        if not spec.features and text.strip():
            spec.features.append(Feature(
                name=text.strip()[:60],
                description=text.strip()[:200],
            ))
            spec.warnings.append(
                "No structured features found — entire input used as single feature description"
            )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _number_features(self, spec: SpecDoc) -> None:
        for i, feature in enumerate(spec.features, start=1):
            feature.id = f"F{i:03d}"

    def _add_missing_warnings(self, spec: SpecDoc) -> None:
        if spec.project.name == "TODO":
            spec.warnings.append("project.name could not be determined — set manually")
        if spec.project.language == "TODO":
            spec.warnings.append("project.language could not be determined — set manually")
        if spec.project.type == "TODO":
            spec.warnings.append("project.type could not be determined — set manually")
        if not spec.features:
            spec.warnings.append("No features extracted — add feature descriptions to input")
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_parser.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/parser.py agents/spec_writer/tests/test_parser.py
git commit -m "feat(spec): add SpecParser with section-header extraction"
```

---

### Task 3: SpecParser — keyword heuristics + robustness

**Files:**
- Modify: `agents/spec_writer/tests/test_parser.py` (append tests)

- [ ] **Step 1: Append failing tests to `agents/spec_writer/tests/test_parser.py`**

```python
# ── Keyword heuristics ─────────────────────────────────────────────────────────

def test_keyword_detects_language_no_header():
    spec = SpecParser().parse("Build a CLI tool in Python that reads CSV files")
    assert spec.project.language == "python"


def test_keyword_detects_framework_no_header():
    spec = SpecParser().parse("Build a REST API with FastAPI and Python")
    assert spec.project.framework == "fastapi"


def test_keyword_detects_project_type_api():
    spec = SpecParser().parse("Build a REST API for user management")
    assert spec.project.type == "api"


def test_keyword_detects_project_type_cli():
    spec = SpecParser().parse("Build a CLI tool for file conversion")
    assert spec.project.type == "cli"


def test_keyword_detects_project_type_frontend():
    spec = SpecParser().parse("Build a frontend web app with Vue")
    assert spec.project.type == "frontend"


def test_feature_priority_must():
    spec = SpecParser().parse("## Requirements\n- Must support authentication")
    assert spec.features[0].priority == "must"


def test_feature_priority_could():
    spec = SpecParser().parse("## Requirements\n- Could add dark mode")
    assert spec.features[0].priority == "could"


def test_feature_priority_default_should():
    spec = SpecParser().parse("## Requirements\n- Support CSV export")
    assert spec.features[0].priority == "should"


# ── Robustness ────────────────────────────────────────────────────────────────

def test_empty_input_returns_todo_fields():
    spec = SpecParser().parse("")
    assert spec.project.language == "TODO"
    assert spec.project.type == "TODO"


def test_empty_input_has_warning():
    spec = SpecParser().parse("")
    assert any("empty" in w.lower() for w in spec.warnings)


def test_vague_input_never_raises():
    spec = SpecParser().parse("something something ???")
    assert spec is not None


def test_vague_input_produces_warnings():
    spec = SpecParser().parse("something unclear")
    assert len(spec.warnings) >= 1


def test_unstructured_list_items_become_features():
    spec = SpecParser().parse("- User login\n- User registration\n- Password reset")
    assert len(spec.features) == 3


def test_fallback_to_single_feature_when_no_list():
    spec = SpecParser().parse("Build me a thing that does stuff")
    assert len(spec.features) >= 1
```

- [ ] **Step 2: Run all parser tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_parser.py -v
```
Expected: all 22 tests PASS

- [ ] **Step 3: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/tests/test_parser.py
git commit -m "test(spec): add keyword heuristic and robustness tests for SpecParser"
```

---

### Task 4: SpecValidator

**Files:**
- Create: `agents/spec_writer/validator.py`
- Create: `agents/spec_writer/tests/test_validator.py`

- [ ] **Step 1: Write failing tests**

`agents/spec_writer/tests/test_validator.py`:
```python
"""Tests for agents.spec_writer.validator.SpecValidator."""
import pytest
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc
from agents.spec_writer.validator import SpecValidator


def make_valid_spec() -> SpecDoc:
    return SpecDoc(
        spec_id="spec_20260415_001",
        project=ProjectSection(name="MyApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in",
                          acceptance_criteria=["Returns 200 on success"])],
    )


def test_valid_spec_has_validated_status():
    result = SpecValidator().validate(make_valid_spec())
    assert result.status == "validated"


def test_valid_spec_has_no_warnings():
    result = SpecValidator().validate(make_valid_spec())
    assert result.warnings == []


def test_missing_project_name_adds_warning():
    spec = make_valid_spec()
    spec.project.name = "TODO"
    result = SpecValidator().validate(spec)
    assert any("project.name" in w for w in result.warnings)


def test_missing_language_adds_warning():
    spec = make_valid_spec()
    spec.project.language = "TODO"
    result = SpecValidator().validate(spec)
    assert any("language" in w for w in result.warnings)


def test_empty_features_adds_warning():
    spec = make_valid_spec()
    spec.features = []
    result = SpecValidator().validate(spec)
    assert any("features" in w for w in result.warnings)


def test_feature_without_acceptance_criteria_adds_warning():
    spec = make_valid_spec()
    spec.features[0].acceptance_criteria = []
    result = SpecValidator().validate(spec)
    assert any("acceptance" in w.lower() for w in result.warnings)


def test_api_type_without_endpoints_adds_warning():
    spec = make_valid_spec()
    spec.project.type = "api"
    spec.technical.api_endpoints = []
    result = SpecValidator().validate(spec)
    assert any("endpoint" in w.lower() for w in result.warnings)


def test_frontend_with_python_adds_warning():
    spec = make_valid_spec()
    spec.project.type = "frontend"
    spec.project.language = "python"
    result = SpecValidator().validate(spec)
    assert any("frontend" in w.lower() or "python" in w.lower() for w in result.warnings)


def test_duplicate_feature_names_add_warning():
    spec = make_valid_spec()
    spec.features.append(Feature(id="F002", name="Login", description="Another login"))
    result = SpecValidator().validate(spec)
    assert any("duplicate" in w.lower() for w in result.warnings)


def test_validator_never_raises_on_empty_spec():
    result = SpecValidator().validate(SpecDoc())
    assert result is not None


def test_warnings_produce_draft_status():
    result = SpecValidator().validate(SpecDoc())  # all TODOs
    assert result.status == "draft"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_validator.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write `agents/spec_writer/validator.py`**

```python
"""
agents/spec_writer/validator.py
================================
SpecValidator — pure validation, no side-effects, never raises.

validate(spec) -> SpecDoc with updated warnings and status.
Status is "validated" when warnings is empty, "draft" otherwise.
"""
from __future__ import annotations

from typing import List

from agents.spec_writer.schema import SpecDoc


class SpecValidator:
    """Validates a SpecDoc for completeness and consistency. Never raises."""

    def validate(self, spec: SpecDoc) -> SpecDoc:
        warnings: List[str] = list(spec.warnings)
        self._check_completeness(spec, warnings)
        self._check_consistency(spec, warnings)
        spec.warnings = warnings
        spec.status = "draft" if warnings else "validated"
        return spec

    def _check_completeness(self, spec: SpecDoc, warnings: List[str]) -> None:
        if spec.project.name == "TODO":
            warnings.append("project.name is TODO — set a project name")
        if spec.project.language == "TODO":
            warnings.append("project.language is TODO — specify the programming language")
        if spec.project.type == "TODO":
            warnings.append("project.type is TODO — specify api|frontend|cli|library|fullstack")
        if not spec.features:
            warnings.append("features list is empty — add at least one feature")
        for feature in spec.features:
            if not feature.acceptance_criteria:
                warnings.append(
                    f"Feature '{feature.name}' ({feature.id}) has no acceptance criteria"
                )

    def _check_consistency(self, spec: SpecDoc, warnings: List[str]) -> None:
        if spec.project.type == "api" and not spec.technical.api_endpoints:
            warnings.append(
                "project.type is 'api' but no api_endpoints defined — add endpoint definitions"
            )
        if spec.project.type == "frontend" and spec.project.language == "python":
            warnings.append(
                "project.type is 'frontend' but language is 'python' — "
                "consider typescript/javascript for frontend projects"
            )
        seen_names: set = set()
        for feature in spec.features:
            if feature.name in seen_names:
                warnings.append(f"Duplicate feature name: '{feature.name}'")
            seen_names.add(feature.name)
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_validator.py -v
```
Expected: all 11 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/validator.py agents/spec_writer/tests/test_validator.py
git commit -m "feat(spec): add SpecValidator with completeness and consistency checks"
```

---

### Task 5: SpecFormatter — JSON + disk I/O

**Files:**
- Create: `agents/spec_writer/formatter.py`
- Create: `agents/spec_writer/tests/test_formatter.py`

- [ ] **Step 1: Write failing tests**

`agents/spec_writer/tests/test_formatter.py`:
```python
"""Tests for agents.spec_writer.formatter.SpecFormatter."""
import json
import pytest
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc
from agents.spec_writer.formatter import SpecFormatter


def make_spec(spec_id="spec_20260415_001") -> SpecDoc:
    return SpecDoc(
        spec_id=spec_id,
        project=ProjectSection(name="TestApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in",
                          acceptance_criteria=["Returns 200 on success"])],
    )


def test_save_writes_json_file(tmp_path):
    path = SpecFormatter(specs_dir=tmp_path).save(make_spec())
    assert path.exists()
    assert path.suffix == ".json"


def test_save_filename_matches_spec_id(tmp_path):
    path = SpecFormatter(specs_dir=tmp_path).save(make_spec("spec_20260415_042"))
    assert path.name == "spec_20260415_042.json"


def test_load_round_trip(tmp_path):
    formatter = SpecFormatter(specs_dir=tmp_path)
    formatter.save(make_spec())
    loaded = formatter.load("spec_20260415_001")
    assert loaded.spec_id == "spec_20260415_001"
    assert loaded.project.language == "python"
    assert loaded.features[0].name == "Login"


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        SpecFormatter(specs_dir=tmp_path).load("spec_no_such_id")


def test_to_json_is_valid_json(tmp_path):
    result = SpecFormatter(specs_dir=tmp_path).to_json(make_spec())
    data = json.loads(result)
    assert data["spec_id"] == "spec_20260415_001"


def test_list_specs_returns_metadata(tmp_path):
    formatter = SpecFormatter(specs_dir=tmp_path)
    formatter.save(make_spec("spec_20260415_001"))
    formatter.save(make_spec("spec_20260415_002"))
    items = formatter.list_specs()
    assert len(items) == 2
    assert all("spec_id" in item for item in items)
    assert all("status" in item for item in items)


def test_list_specs_empty_dir(tmp_path):
    assert SpecFormatter(specs_dir=tmp_path).list_specs() == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_formatter.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write `agents/spec_writer/formatter.py`**

```python
"""
agents/spec_writer/formatter.py
================================
SpecFormatter — serialises SpecDoc to JSON or Markdown and manages disk I/O.

Default storage: ~/.agent-orchestrator/specs/
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from agents.spec_writer.schema import SpecDoc

DEFAULT_SPECS_DIR = Path.home() / ".agent-orchestrator" / "specs"


class SpecFormatter:
    def __init__(self, specs_dir: Path = DEFAULT_SPECS_DIR) -> None:
        self._specs_dir = Path(specs_dir)
        self._specs_dir.mkdir(parents=True, exist_ok=True)

    # ── Disk I/O ───────────────────────────────────────────────────────────────

    def save(self, spec: SpecDoc) -> Path:
        """Write spec to <specs_dir>/<spec_id>.json. Returns the path."""
        path = self._specs_dir / f"{spec.spec_id}.json"
        path.write_text(
            json.dumps(spec.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
        return path

    def load(self, spec_id: str) -> SpecDoc:
        """Load a spec by ID. Raises FileNotFoundError if not found."""
        path = self._specs_dir / f"{spec_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Spec not found: {spec_id}")
        return SpecDoc.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_specs(self) -> List[Dict[str, Any]]:
        """Return summary dicts for all specs, sorted by spec_id."""
        result = []
        for path in sorted(self._specs_dir.glob("spec_*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append({
                    "spec_id": data.get("spec_id", path.stem),
                    "status": data.get("status", "unknown"),
                    "created_at": data.get("created_at", ""),
                    "project_name": data.get("project", {}).get("name", "TODO"),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return result

    # ── Serialisation ──────────────────────────────────────────────────────────

    def to_json(self, spec: SpecDoc) -> str:
        """Serialise spec to a formatted JSON string."""
        return json.dumps(spec.model_dump(), indent=2, default=str)

    def to_markdown(self, spec: SpecDoc) -> str:
        """Render spec as human-readable Markdown."""
        lines = [
            f"# Spec: {spec.project.name}",
            f"",
            f"**ID:** {spec.spec_id}  ",
            f"**Status:** {spec.status}  ",
            f"**Created:** {spec.created_at}  ",
            f"",
            f"## Project",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Type | {spec.project.type} |",
            f"| Language | {spec.project.language} |",
            f"| Framework | {spec.project.framework} |",
            f"",
            f"## Features",
            f"",
        ]
        for feature in spec.features:
            lines += [
                f"### {feature.id}: {feature.name}",
                f"",
                f"**Priority:** {feature.priority} | **Complexity:** {feature.estimated_complexity}",
                f"",
                f"{feature.description}",
                f"",
            ]
            if feature.acceptance_criteria:
                lines.append("**Acceptance Criteria:**")
                for criterion in feature.acceptance_criteria:
                    lines.append(f"- {criterion}")
                lines.append("")

        if spec.technical.dependencies:
            lines += ["## Dependencies", ""]
            for dep in spec.technical.dependencies:
                lines.append(f"- {dep}")
            lines.append("")

        if spec.constraints.performance or spec.constraints.security:
            lines += ["## Constraints", ""]
            for c in spec.constraints.performance:
                lines.append(f"- (performance) {c}")
            for c in spec.constraints.security:
                lines.append(f"- (security) {c}")
            lines.append("")

        if spec.context_applied.patterns_used or spec.context_applied.decisions_referenced:
            lines += ["## Context Applied", ""]
            for p in spec.context_applied.patterns_used:
                lines.append(f"- (pattern) {p}")
            for d in spec.context_applied.decisions_referenced:
                lines.append(f"- (decision) {d}")
            lines.append("")

        if spec.warnings:
            lines += ["## Warnings", ""]
            for w in spec.warnings:
                lines.append(f"- ⚠ {w}")
            lines.append("")

        return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_formatter.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/formatter.py agents/spec_writer/tests/test_formatter.py
git commit -m "feat(spec): add SpecFormatter with JSON serialization and disk I/O"
```

---

### Task 6: SpecFormatter — Markdown output

**Files:**
- Modify: `agents/spec_writer/tests/test_formatter.py` (append tests)

- [ ] **Step 1: Append Markdown tests to `agents/spec_writer/tests/test_formatter.py`**

```python
# ── Markdown output ────────────────────────────────────────────────────────────

def test_to_markdown_contains_project_name(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "TestApp" in md


def test_to_markdown_contains_feature_name(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "Login" in md


def test_to_markdown_contains_feature_id(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "F001" in md


def test_to_markdown_contains_acceptance_criteria(tmp_path):
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(make_spec())
    assert "Returns 200 on success" in md


def test_to_markdown_warnings_section(tmp_path):
    spec = make_spec()
    spec.warnings = ["project.name is TODO"]
    md = SpecFormatter(specs_dir=tmp_path).to_markdown(spec)
    assert "Warnings" in md
    assert "project.name is TODO" in md
```

- [ ] **Step 2: Run all formatter tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_formatter.py -v
```
Expected: all 12 tests PASS

- [ ] **Step 3: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/tests/test_formatter.py
git commit -m "test(spec): add Markdown output tests for SpecFormatter"
```

---

### Task 7: SpecEnricher

**Files:**
- Create: `agents/spec_writer/enricher.py`
- Create: `agents/spec_writer/tests/test_enricher.py`

- [ ] **Step 1: Write failing tests**

`agents/spec_writer/tests/test_enricher.py`:
```python
"""Tests for agents.spec_writer.enricher.SpecEnricher."""
import pytest
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.spec_writer.enricher import SpecEnricher
from agents.spec_writer.schema import Feature, ProjectSection, SpecDoc


class FakeMemoryAgent:
    name = "memory"

    def run(self, args=None, **kwargs):
        return {
            "results": [
                {"category": "patterns",   "content": "Use repository pattern"},
                {"category": "decisions",  "content": "We use FastAPI for REST"},
            ]
        }


class FakeRegistry:
    def __init__(self, has_memory=True):
        self._has_memory = has_memory

    def get(self, name, bus, state, **kwargs):
        if name == "memory" and self._has_memory:
            return FakeMemoryAgent()
        raise KeyError(f"No agent '{name}'")


def make_spec() -> SpecDoc:
    return SpecDoc(
        spec_id="spec_20260415_001",
        project=ProjectSection(name="TestApp", type="api", language="python", framework="fastapi"),
        features=[Feature(id="F001", name="Login", description="User can log in")],
    )


def test_enrich_fills_patterns_used(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(make_spec())
    assert "Use repository pattern" in spec.context_applied.patterns_used


def test_enrich_fills_decisions_referenced(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(make_spec())
    assert "We use FastAPI for REST" in spec.context_applied.decisions_referenced


def test_enrich_without_memory_agent_adds_warning(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(has_memory=False), bus, state).enrich(make_spec())
    assert any("MemoryAgent" in w or "memory" in w.lower() for w in spec.warnings)


def test_enrich_without_registry_adds_warning(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(None, bus, state).enrich(make_spec())
    assert any("registry" in w.lower() for w in spec.warnings)


def test_enrich_does_not_raise_on_empty_spec(tmp_path):
    bus, state = EventBus(), StateStore(tmp_path / "state.json")
    spec = SpecEnricher(FakeRegistry(), bus, state).enrich(SpecDoc())
    assert spec is not None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_enricher.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write `agents/spec_writer/enricher.py`**

```python
"""
agents/spec_writer/enricher.py
================================
SpecEnricher — queries the MemoryAgent via AgentRegistry to add project context.

enrich(spec) -> SpecDoc with context_applied populated.
Never raises — missing registry or MemoryAgent produces a warning.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from agents.spec_writer.schema import SpecDoc

if TYPE_CHECKING:
    from agents.orchestrator.bus import EventBus
    from agents.orchestrator.registry import AgentRegistry
    from agents.orchestrator.state import StateStore


class SpecEnricher:
    """Enriches a SpecDoc with context from the MemoryAgent via AgentRegistry."""

    def __init__(
        self,
        registry: Optional["AgentRegistry"],
        bus: "EventBus",
        state: "StateStore",
    ) -> None:
        self._registry = registry
        self._bus = bus
        self._state = state

    def enrich(self, spec: SpecDoc) -> SpecDoc:
        if self._registry is None:
            spec.warnings.append("No registry provided — context enrichment skipped")
            return spec

        try:
            agent = self._registry.get("memory", self._bus, self._state)
        except KeyError:
            spec.warnings.append("MemoryAgent not registered — context enrichment skipped")
            return spec

        query = self._build_query(spec)
        if not query:
            return spec

        try:
            result = agent.run(args=["query", query])
        except Exception as exc:
            spec.warnings.append(f"Memory query failed: {exc}")
            return spec

        for entry in result.get("results", []):
            category = entry.get("category", "")
            content = entry.get("content", "")
            if not content:
                continue
            if category == "patterns":
                spec.context_applied.patterns_used.append(content)
            elif category == "decisions":
                spec.context_applied.decisions_referenced.append(content)

        return spec

    def _build_query(self, spec: SpecDoc) -> str:
        parts = [
            spec.project.language,
            spec.project.framework,
            spec.project.type,
            *(f.description for f in spec.features[:3]),
        ]
        return " ".join(p for p in parts if p and p != "TODO")
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_enricher.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/enricher.py agents/spec_writer/tests/test_enricher.py
git commit -m "feat(spec): add SpecEnricher with MemoryAgent integration via registry"
```

---

### Task 8: New events

**Files:**
- Modify: `agents/orchestrator/events.py` (append 4 dataclasses)
- Modify: `agents/orchestrator/tests/test_events.py` (append 4 tests)

- [ ] **Step 1: Append failing tests to `agents/orchestrator/tests/test_events.py`**

```python
# ── Spec events ────────────────────────────────────────────────────────────────

def test_spec_created_event():
    from agents.orchestrator.events import SpecCreated
    e = SpecCreated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecCreated"
    assert e.status == "success"


def test_spec_validated_event():
    from agents.orchestrator.events import SpecValidated
    e = SpecValidated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecValidated"


def test_spec_updated_event():
    from agents.orchestrator.events import SpecUpdated
    e = SpecUpdated(agent_name="spec", payload={"spec_id": "spec_20260415_001"})
    assert e.event_type == "SpecUpdated"


def test_spec_failed_event():
    from agents.orchestrator.events import SpecFailed
    e = SpecFailed(agent_name="spec", error="something went wrong")
    assert e.event_type == "SpecFailed"
    assert e.status == "failed"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/test_events.py -v 2>&1 | tail -10
```
Expected: `ImportError: cannot import name 'SpecCreated'`

- [ ] **Step 3: Append to `agents/orchestrator/events.py`**

Add after the `ContextProvided` dataclass at the end of the file:
```python


@dataclass
class SpecCreated(AgentEvent):
    event_type: str = "SpecCreated"


@dataclass
class SpecValidated(AgentEvent):
    event_type: str = "SpecValidated"


@dataclass
class SpecUpdated(AgentEvent):
    event_type: str = "SpecUpdated"


@dataclass
class SpecFailed(AgentEvent):
    event_type: str = "SpecFailed"
    status: str = "failed"
```

- [ ] **Step 4: Run all events tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/test_events.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/orchestrator/events.py agents/orchestrator/tests/test_events.py
git commit -m "feat(orchestrator): add SpecCreated/Validated/Updated/Failed events"
```

---

### Task 9: AgentRegistry `**kwargs` extension

**Files:**
- Modify: `agents/orchestrator/registry.py` (one line change in `get()`)
- Modify: `agents/orchestrator/tests/test_registry.py` (append one test)

- [ ] **Step 1: Append failing test to `agents/orchestrator/tests/test_registry.py`**

```python
def test_registry_get_forwards_kwargs(tmp_path):
    """Extra kwargs passed to get() are forwarded to the agent constructor."""
    from agents.orchestrator.base_agent import BaseAgent
    from agents.orchestrator.bus import EventBus
    from agents.orchestrator.registry import AgentRegistry
    from agents.orchestrator.state import StateStore

    class KwargsCapture(BaseAgent):
        name = "kwarg_test"
        description = "captures kwargs"
        received_extra = None

        def __init__(self, bus, state, extra_param=None, **kwargs):
            super().__init__(bus=bus, state=state)
            KwargsCapture.received_extra = extra_param

        def run(self, **kwargs):
            return {}

    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    registry = AgentRegistry()
    registry.register(KwargsCapture)
    registry.get("kwarg_test", bus, state, extra_param="hello")
    assert KwargsCapture.received_extra == "hello"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/test_registry.py::test_registry_get_forwards_kwargs -v
```
Expected: FAIL — extra kwarg is not forwarded (TypeError or assertion fails)

- [ ] **Step 3: Edit `agents/orchestrator/registry.py` — update `get()` signature and body**

Old (line 35–40):
```python
    def get(self, name: str, bus: EventBus, state: StateStore) -> BaseAgent:
        """Instantiate and return a registered agent by name."""
        if name not in self._classes:
            available = ", ".join(sorted(self._classes))
            raise KeyError(f"No agent '{name}'. Available: {available or '(none)'}")
        return self._classes[name](bus=bus, state=state)
```

New:
```python
    def get(self, name: str, bus: EventBus, state: StateStore, **kwargs) -> BaseAgent:
        """Instantiate and return a registered agent by name."""
        if name not in self._classes:
            available = ", ".join(sorted(self._classes))
            raise KeyError(f"No agent '{name}'. Available: {available or '(none)'}")
        return self._classes[name](bus=bus, state=state, **kwargs)
```

- [ ] **Step 4: Run all registry tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/test_registry.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/orchestrator/registry.py agents/orchestrator/tests/test_registry.py
git commit -m "feat(orchestrator): extend AgentRegistry.get() with **kwargs forwarding"
```

---

### Task 10: SpecWriterAgent

**Files:**
- Create: `agents/spec_writer/agent.py`
- Create: `agents/spec_writer/tests/test_agent.py`

- [ ] **Step 1: Write failing tests**

`agents/spec_writer/tests/test_agent.py`:
```python
"""Tests for agents.spec_writer.agent.SpecWriterAgent."""
import pytest
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore
from agents.spec_writer.agent import SpecWriterAgent


def make_agent(tmp_path):
    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    agent = SpecWriterAgent(bus=bus, state=state, specs_dir=tmp_path / "specs")
    return agent, bus, state


def test_agent_name():
    assert SpecWriterAgent.name == "spec"


def test_unknown_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError, match="Unknown spec subcommand"):
        agent.run(args=["bogus"])


def test_none_subcommand_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(ValueError):
        agent.run(args=[])


def test_create_returns_spec_id(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "Build a Python REST API with FastAPI"])
    assert "spec_id" in result
    assert result["spec_id"].startswith("spec_")


def test_create_saves_file(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "Build a Python REST API"])
    spec_id = result["spec_id"]
    assert (tmp_path / "specs" / f"{spec_id}.json").exists()


def test_create_publishes_spec_created(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    received = []
    bus.subscribe("SpecCreated", received.append)
    agent.run(args=["create", "Build a Python CLI tool"])
    assert len(received) == 1
    assert received[0].event_type == "SpecCreated"


def test_list_returns_entries(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    agent.run(args=["create", "First project"])
    agent.run(args=["create", "Second project"])
    result = agent.run(args=["list"])
    assert len(result["specs"]) == 2


def test_show_returns_spec(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "A Python API"])
    spec_id = created["spec_id"]
    result = agent.run(args=["show", spec_id])
    assert result["spec"]["spec_id"] == spec_id


def test_show_unknown_id_raises(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    with pytest.raises(FileNotFoundError):
        agent.run(args=["show", "spec_no_such"])


def test_validate_publishes_spec_validated(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build a thing"])
    spec_id = created["spec_id"]
    received = []
    bus.subscribe("SpecValidated", received.append)
    agent.run(args=["validate", spec_id])
    assert len(received) == 1
    assert received[0].event_type == "SpecValidated"


def test_export_json(tmp_path):
    import json
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    result = agent.run(args=["export", spec_id, "--format", "json"])
    assert "output" in result
    data = json.loads(result["output"])
    assert data["spec_id"] == spec_id


def test_export_markdown(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    result = agent.run(args=["export", spec_id, "--format", "md"])
    assert "output" in result
    assert "# Spec:" in result["output"]


def test_create_from_file(tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("Build a Python CLI tool that converts CSV to JSON", encoding="utf-8")
    agent, _, _ = make_agent(tmp_path)
    result = agent.run(args=["create", "--file", str(input_file)])
    assert "spec_id" in result


def test_update_adds_new_feature(tmp_path):
    agent, _, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build a Python CLI tool"])
    spec_id = created["spec_id"]
    agent.run(args=["update", spec_id, "- Add export to CSV feature"])
    result = agent.run(args=["show", spec_id])
    feature_names = [f["name"] for f in result["spec"]["features"]]
    assert any("CSV" in name or "export" in name.lower() for name in feature_names)


def test_update_publishes_spec_updated(tmp_path):
    agent, bus, _ = make_agent(tmp_path)
    created = agent.run(args=["create", "Build something"])
    spec_id = created["spec_id"]
    received = []
    bus.subscribe("SpecUpdated", received.append)
    agent.run(args=["update", spec_id, "- Add new feature"])
    assert len(received) == 1
    assert received[0].event_type == "SpecUpdated"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_agent.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write `agents/spec_writer/agent.py`**

```python
"""
agents/spec_writer/agent.py
============================
SpecWriterAgent — registered as "spec" in AgentRegistry.

run(args=[subcommand, ...]) dispatches to:
    create <description> | --file <path>
    validate <spec_id>
    list
    show <spec_id>
    update <spec_id> <delta>
    export <spec_id> [--format json|md]
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import SpecCreated, SpecFailed, SpecUpdated, SpecValidated
from agents.orchestrator.state import StateStore
from agents.spec_writer.enricher import SpecEnricher
from agents.spec_writer.formatter import SpecFormatter
from agents.spec_writer.parser import SpecParser
from agents.spec_writer.validator import SpecValidator

DEFAULT_SPECS_DIR = Path.home() / ".agent-orchestrator" / "specs"


class SpecWriterAgent(BaseAgent):
    """Generates and manages structured feature specifications."""

    name = "spec"
    description = "Generates and manages structured feature specifications"

    def __init__(
        self,
        bus: EventBus,
        state: StateStore,
        registry=None,
        specs_dir: Path = DEFAULT_SPECS_DIR,
    ) -> None:
        super().__init__(bus=bus, state=state)
        self._registry = registry
        self._parser = SpecParser()
        self._validator = SpecValidator()
        self._formatter = SpecFormatter(specs_dir=Path(specs_dir))

    # ── Dispatch ───────────────────────────────────────────────────────────────

    def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
        args = list(args or [])
        dispatch = {
            "create":   self._cmd_create,
            "validate": self._cmd_validate,
            "list":     self._cmd_list,
            "show":     self._cmd_show,
            "update":   self._cmd_update,
            "export":   self._cmd_export,
        }
        subcommand = args[0] if args else None
        if subcommand not in dispatch:
            available = ", ".join(sorted(dispatch))
            raise ValueError(
                f"Unknown spec subcommand '{subcommand}'. Available: {available}"
            )
        try:
            return dispatch[subcommand](args[1:])
        except (ValueError, FileNotFoundError):
            raise  # re-raise expected errors without wrapping
        except Exception as exc:
            self.emit(SpecFailed(
                agent_name=self.name,
                error=str(exc),
                payload={"subcommand": subcommand, "error": str(exc)},
            ))
            raise

    # ── Subcommands ────────────────────────────────────────────────────────────

    def _cmd_create(self, args: List[str]) -> Dict[str, Any]:
        """create <description> | --file <path>"""
        text = self._resolve_input(args)
        spec = self._parser.parse(text)
        spec = SpecEnricher(registry=self._registry, bus=self._bus, state=self._state).enrich(spec)
        spec = self._validator.validate(spec)
        spec.spec_id = self._next_spec_id()
        path = self._formatter.save(spec)
        self.emit(SpecCreated(
            agent_name=self.name,
            payload={"spec_id": spec.spec_id, "status": spec.status, "path": str(path)},
        ))
        print(f"Spec created: {spec.spec_id}  [{spec.status}]")
        for w in spec.warnings:
            print(f"  ⚠ {w}")
        return {"spec_id": spec.spec_id, "status": spec.status, "warnings": spec.warnings}

    def _cmd_validate(self, args: List[str]) -> Dict[str, Any]:
        """validate <spec_id>"""
        if not args:
            raise ValueError("Usage: spec validate <spec_id>")
        spec_id = args[0]
        spec = self._formatter.load(spec_id)
        spec.warnings = []
        spec = self._validator.validate(spec)
        self._formatter.save(spec)
        self.emit(SpecValidated(
            agent_name=self.name,
            payload={"spec_id": spec_id, "status": spec.status},
        ))
        print(f"Spec {spec_id}: {spec.status} ({len(spec.warnings)} warnings)")
        return {"spec_id": spec_id, "status": spec.status, "warnings": spec.warnings}

    def _cmd_list(self, args: List[str]) -> Dict[str, Any]:
        """list — show all specs"""
        specs = self._formatter.list_specs()
        for s in specs:
            print(f"[{s['status']:10}] {s['spec_id']}  {s['project_name']}")
        return {"specs": specs}

    def _cmd_show(self, args: List[str]) -> Dict[str, Any]:
        """show <spec_id>"""
        if not args:
            raise ValueError("Usage: spec show <spec_id>")
        spec = self._formatter.load(args[0])
        print(self._formatter.to_json(spec))
        return {"spec": spec.model_dump()}

    def _cmd_update(self, args: List[str]) -> Dict[str, Any]:
        """update <spec_id> <delta_description>"""
        if len(args) < 2:
            raise ValueError("Usage: spec update <spec_id> <description>")
        spec_id = args[0]
        delta_text = " ".join(args[1:])
        spec = self._formatter.load(spec_id)
        delta = self._parser.parse(delta_text)
        existing_names = {f.name for f in spec.features}
        for feature in delta.features:
            if feature.name not in existing_names:
                spec.features.append(feature)
        if delta.project.language != "TODO" and spec.project.language == "TODO":
            spec.project.language = delta.project.language
        if delta.project.framework != "TODO" and spec.project.framework == "TODO":
            spec.project.framework = delta.project.framework
        spec.warnings = []
        spec = self._validator.validate(spec)
        self._formatter.save(spec)
        self.emit(SpecUpdated(
            agent_name=self.name,
            payload={"spec_id": spec_id, "status": spec.status},
        ))
        print(f"Spec {spec_id} updated: {spec.status}")
        return {"spec_id": spec_id, "status": spec.status, "warnings": spec.warnings}

    def _cmd_export(self, args: List[str]) -> Dict[str, Any]:
        """export <spec_id> [--format json|md]"""
        if not args:
            raise ValueError("Usage: spec export <spec_id> [--format json|md]")
        spec_id = args[0]
        fmt = "json"
        if "--format" in args:
            idx = args.index("--format")
            if idx + 1 < len(args):
                fmt = args[idx + 1]
        spec = self._formatter.load(spec_id)
        output = self._formatter.to_markdown(spec) if fmt == "md" else self._formatter.to_json(spec)
        print(output)
        return {"spec_id": spec_id, "format": fmt, "output": output}

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve_input(self, args: List[str]) -> str:
        if not args:
            raise ValueError("Usage: spec create <description> | --file <path>")
        if args[0] == "--file":
            if len(args) < 2:
                raise ValueError("Usage: spec create --file <path>")
            return Path(args[1]).read_text(encoding="utf-8")
        return " ".join(args)

    def _next_spec_id(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        existing = list(self._formatter._specs_dir.glob(f"spec_{today}_*.json"))
        return f"spec_{today}_{len(existing) + 1:03d}"
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/spec_writer/tests/test_agent.py -v
```
Expected: all 16 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/spec_writer/agent.py agents/spec_writer/tests/test_agent.py
git commit -m "feat(spec): add SpecWriterAgent with full subcommand dispatch"
```

---

### Task 11: Orchestrator integration

**Files:**
- Modify: `agents/orchestrator/orchestrator.py`
- Modify: `agents/orchestrator/tests/test_orchestrator.py` (append one test)

- [ ] **Step 1: Append failing integration test to `agents/orchestrator/tests/test_orchestrator.py`**

```python
def test_spec_create_dispatches_to_spec_agent(tmp_path):
    import io
    from agents.orchestrator.bus import EventBus
    from agents.orchestrator.logger import OrchestratorLogger
    from agents.orchestrator.orchestrator import Orchestrator
    from agents.orchestrator.registry import AgentRegistry
    from agents.orchestrator.state import StateStore
    from agents.spec_writer.agent import SpecWriterAgent

    bus = EventBus()
    state = StateStore(tmp_path / "state.json")
    logger = OrchestratorLogger(bus, stream=io.StringIO())
    registry = AgentRegistry()

    class TestSpecAgent(SpecWriterAgent):
        def __init__(self, bus, state, **kwargs):
            super().__init__(bus=bus, state=state, specs_dir=tmp_path / "specs", **kwargs)

    TestSpecAgent.name = "spec"
    registry.register(TestSpecAgent)

    orch = Orchestrator(registry, bus, state, logger)
    result = orch.run("spec", ["create", "Build a Python API"])
    assert "spec_id" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/test_orchestrator.py::test_spec_create_dispatches_to_spec_agent -v 2>&1 | tail -10
```
Expected: FAIL — `"spec"` not in INTENT_MAP

- [ ] **Step 3: Edit `agents/orchestrator/orchestrator.py`**

Update `INTENT_MAP` — add `"spec"` entry:

Old:
```python
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":  ("code_auditor", "target"),
    "fix":    ("code_fixer",   "target"),
    "memory": ("memory",       "args"),    # memory agent receives full arg list
}
```

New:
```python
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":  ("code_auditor", "target"),
    "fix":    ("code_fixer",   "target"),
    "memory": ("memory",       "args"),    # memory agent receives full arg list
    "spec":   ("spec",         "args"),    # spec agent receives full arg list
}
```

Update the agent instantiation in `run()` — add `extra` dict before the existing `agent = ...` line:

Old:
```python
        agent = self._registry.get(agent_name, self._bus, self._state)
        return agent.run(**kwargs)
```

New:
```python
        extra: Dict[str, Any] = {}
        if command == "spec":
            extra["registry"] = self._registry

        agent = self._registry.get(agent_name, self._bus, self._state, **extra)
        return agent.run(**kwargs)
```

- [ ] **Step 4: Run all orchestrator tests**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/orchestrator/tests/ -v
```
Expected: all tests PASS

- [ ] **Step 5: Run full agent test suite**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
python -m pytest agents/ -v --tb=short 2>&1 | tail -20
```
Expected: all tests PASS, no failures

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/degro/OneDrive/Bureaublad/coderen/Claude Code/randy-site"
git add agents/orchestrator/orchestrator.py agents/orchestrator/tests/test_orchestrator.py
git commit -m "feat(orchestrator): register 'spec' command and pass registry to SpecWriterAgent"
```
