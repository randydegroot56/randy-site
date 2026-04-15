# Spec Writer Agent — Design

**Date:** 2026-04-14  
**Status:** Approved  
**Integrates with:** EventBus, AgentRegistry, StateStore, OrchestratorLogger, MemoryAgent

---

## Overview

The Spec Writer Agent transforms a natural-language description of a feature or project into a structured, machine-readable specification document. The spec is the authoritative input for all downstream agents (Scaffolder, Code Generator, Test Generator). No LLM calls are made — all parsing is rule-based with heuristics.

---

## Architecture

### Pipeline

```
CLI input (string or file)
   │
   ▼
SpecWriterAgent.run(args)
   │
   ├─ "create"   → SpecParser → SpecEnricher → SpecValidator → SpecFormatter → SpecCreated
   ├─ "validate" → load JSON  → SpecValidator → SpecFormatter (update) → SpecValidated
   ├─ "list"     → scan specs dir → print table
   ├─ "show"     → load JSON → print
   ├─ "update"   → load JSON → SpecParser (delta) → merge → SpecValidator → SpecFormatter → SpecUpdated
   └─ "export"   → load JSON → SpecFormatter.to_markdown() | to_json() → stdout / file
```

### Storage

Specs are persisted as JSON files in `~/.agent-orchestrator/specs/<spec_id>.json`.  
`spec_id` format: `spec_YYYYMMDD_NNN` (zero-padded counter per day).

---

## Components

### schema.py — Pydantic v2 models

All fields are `Optional` with sensible defaults so partial specs are valid.

```
SpecDoc
├── spec_id: str
├── created_at: str (ISO-8601)
├── status: Literal["draft", "validated", "failed"]
├── input: InputSection
│   └── raw_description: str
├── project: ProjectSection
│   ├── name: str | "TODO"
│   ├── type: Literal["api","frontend","cli","library","fullstack"] | "TODO"
│   ├── language: str | "TODO"
│   └── framework: str | "TODO"
├── features: List[Feature]
│   ├── id: str  (F001, F002, …)
│   ├── name: str
│   ├── description: str
│   ├── acceptance_criteria: List[str]
│   ├── priority: Literal["must","should","could"]
│   └── estimated_complexity: Literal["low","medium","high"]
├── technical: TechnicalSpec
│   ├── dependencies: List[str]
│   ├── architecture_notes: str
│   ├── database_schema: dict
│   ├── api_endpoints: List[dict]
│   └── file_structure: dict
├── constraints: Constraints
│   ├── performance: List[str]
│   ├── security: List[str]
│   └── compatibility: List[str]
├── context_applied: ContextApplied
│   ├── patterns_used: List[str]
│   └── decisions_referenced: List[str]
└── warnings: List[str]
```

---

### parser.py — SpecParser

Hybrid extraction: section-headers first, keyword heuristics as fallback.

**Section-header detection** (regex `^#{1,3}\s+` or `^===+`):

| Header pattern | Maps to |
|---|---|
| `goals?`, `doel`, `user stor` | `project.name` hint + feature descriptions |
| `requirements?`, `eisen?` | `features[].description` |
| `constraints?`, `beperkingen?` | `constraints.*` |
| `tech(nical)?`, `stack` | `technical.*` |
| `acceptance criteria?` | `features[].acceptance_criteria` |

**Keyword heuristics** (case-insensitive):

| Pattern | Field |
|---|---|
| `python\|typescript\|go\|rust\|java\|javascript` | `project.language` |
| `fastapi\|flask\|django\|next\|express\|vue\|svelte\|laravel` | `project.framework` |
| `\bapi\b\|rest\|graphql` | `project.type = "api"` |
| `cli\|command.line\|terminal` | `project.type = "cli"` |
| `frontend\|react\|vue\|svelte` | `project.type = "frontend"` |
| `must\b` | `feature.priority = "must"` |
| `should\b` | `feature.priority = "should"` |
| `could\b\|nice.to.have` | `feature.priority = "could"` |
| lines starting with `-`, `*`, or digit+`.` | feature candidates |

**Outputs:** `ParsedInput` dataclass + `List[str]` warnings for unfilled fields.  
Never raises — always returns a result with `"TODO"` placeholders.

---

### enricher.py — SpecEnricher

Queries the MemoryAgent via the AgentRegistry to enrich the parsed spec with project context.

```python
class SpecEnricher:
    def __init__(self, registry: AgentRegistry, bus: EventBus, state: StateStore): ...

    def enrich(self, parsed: ParsedInput) -> ParsedInput:
        # 1. Build query from parsed fields (language, framework, feature names)
        # 2. registry.get("memory", bus, state).run(args=["query", query_text])
        # 3. Fill context_applied.patterns_used from results in category "patterns"
        # 4. Fill context_applied.decisions_referenced from results in category "decisions"
        # 5. If "memory" not in registry → add warning, return parsed unchanged
```

The MemoryAgent is accessed by name via the registry, not imported directly. If unavailable, enrichment is skipped gracefully.

---

### validator.py — SpecValidator

Pure function — never raises, always returns `(SpecDoc, List[str])`.

**Completeness checks** (missing → warning + field stays `"TODO"`):
- `project.name`, `project.type`, `project.language` are `"TODO"`
- `features` list is empty
- any feature has empty `acceptance_criteria`

**Consistency checks**:
- `project.type == "api"` but no `technical.api_endpoints` → warning
- `project.type == "frontend"` but `project.language` is `"python"` → warning
- duplicate feature names → warning

**Feasibility checks**:
- conflicting constraints (e.g., "no database" + "persists data") → warning

All warnings are appended to `spec.warnings`. Status is set to `"validated"` if no blocking issues, `"draft"` otherwise.

---

### formatter.py — SpecFormatter

```python
class SpecFormatter:
    def __init__(self, specs_dir: Path = DEFAULT_SPECS_DIR): ...

    def save(self, spec: SpecDoc) -> Path:
        """Write spec to ~/.agent-orchestrator/specs/<spec_id>.json. Returns path."""

    def load(self, spec_id: str) -> SpecDoc:
        """Load a spec by ID. Raises FileNotFoundError if not found."""

    def list_specs(self) -> List[Dict]:
        """Return [{spec_id, status, created_at, project_name}] for all specs."""

    def to_json(self, spec: SpecDoc) -> str:
        """Serialize to formatted JSON string."""

    def to_markdown(self, spec: SpecDoc) -> str:
        """Render spec as human-readable Markdown."""
```

`DEFAULT_SPECS_DIR = Path.home() / ".agent-orchestrator" / "specs"`

---

### agent.py — SpecWriterAgent

```python
class SpecWriterAgent(BaseAgent):
    name = "spec"
    description = "Generates and manages structured feature specifications"

    def __init__(self, bus, state, registry=None, specs_dir=DEFAULT_SPECS_DIR): ...

    def run(self, args=None, **kwargs):
        # Dispatches: create, validate, list, show, update, export
```

Subcommand dispatch mirrors the MemoryAgent pattern (`args[0]` = subcommand, `args[1:]` = params).

---

## EventBus Integration

| Direction | Event | Trigger |
|---|---|---|
| Subscribes | `ContextProvided` | MemoryAgent query results (future use) |
| Publishes | `SpecCreated` | After successful create |
| Publishes | `SpecValidated` | After validate subcommand |
| Publishes | `SpecUpdated` | After update subcommand |
| Publishes | `SpecFailed` | On any unrecoverable error |

New event dataclasses added to `orchestrator/events.py`:
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

---

## Orchestrator Integration

### INTENT_MAP addition

```python
INTENT_MAP["spec"] = ("spec", "args")
```

### Registry.get() extension

`AgentRegistry.get()` gains `**kwargs` forwarded to the agent constructor:

```python
def get(self, name: str, bus: EventBus, state: StateStore, **kwargs) -> BaseAgent:
    return self._classes[name](bus=bus, state=state, **kwargs)
```

### Orchestrator dispatch for "spec"

```python
if command == "spec":
    agent = self._registry.get("spec", self._bus, self._state, registry=self._registry)
    return agent.run(args=args)
```

---

## CLI Commands

All routed through `orchestrator spec <subcommand>`:

| Command | Args | Behaviour |
|---|---|---|
| `spec create "<description>"` | string | Parse → enrich → validate → save → print spec_id |
| `spec create --file input.txt` | `--file <path>` | Read file → same pipeline |
| `spec validate <spec_id>` | spec_id | Load → re-validate → update file |
| `spec list` | — | Print table of all specs |
| `spec show <spec_id>` | spec_id | Pretty-print JSON |
| `spec update <spec_id> "<delta>"` | spec_id + string | Merge delta → re-validate → save |
| `spec export <spec_id> --format json\|md` | spec_id + format | Print to stdout |

---

## File Structure

```
agents/spec_writer/
├── __init__.py
├── agent.py        ← SpecWriterAgent (BaseAgent subclass, name="spec")
├── parser.py       ← SpecParser (hybrid section-header + keyword extraction)
├── enricher.py     ← SpecEnricher (queries MemoryAgent via AgentRegistry)
├── validator.py    ← SpecValidator (pure function, no exceptions)
├── formatter.py    ← SpecFormatter (JSON + Markdown, disk I/O)
├── schema.py       ← Pydantic v2 models (SpecDoc, Feature, etc.)
└── tests/
    ├── __init__.py
    ├── test_parser.py
    ├── test_enricher.py
    ├── test_validator.py
    └── test_formatter.py
```

Modified files:
- `agents/orchestrator/events.py` — add SpecCreated, SpecValidated, SpecUpdated, SpecFailed
- `agents/orchestrator/registry.py` — add `**kwargs` to `get()`
- `agents/orchestrator/orchestrator.py` — add `"spec"` to INTENT_MAP, pass registry for spec command

---

## Testing Strategy

- **test_parser.py** — structured input → exact field extraction; empty string → all `"TODO"` + warnings; messy input → partial extraction + warnings
- **test_enricher.py** — `FakeRegistry` with stub MemoryAgent; verify `context_applied` populated; verify graceful fallback when "memory" absent
- **test_validator.py** — one test per validation rule; verify no exceptions ever raised
- **test_formatter.py** — JSON round-trip; Markdown contains all feature names; file written to disk; `list_specs()` returns correct metadata

---

## Constraints

- No LLM calls anywhere in the pipeline
- Vague/incomplete input produces a spec with `"TODO"` fields and warnings, never an error
- SpecEnricher accesses MemoryAgent via AgentRegistry only (no direct import of MemoryAgent class in enricher.py)
- All persistence in `~/.agent-orchestrator/specs/`
- Python only, same style as existing agents
