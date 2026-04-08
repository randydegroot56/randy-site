# CODE_AUDITOR_AGENT

> ⚠️ **Safety-first code cleanup. NOTHING is deleted without explicit human approval.**

---

## Overview

The Code Auditor Agent is an automated 5-phase system that safely analyzes your codebase,
identifies unused code, and generates actionable cleanup reports — without ever touching a
single file until you explicitly say so.

Modern projects accumulate dead code fast: abandoned features, forgotten utilities, orphaned
modules left behind after refactors. This degrades readability, slows onboarding, and inflates
bundle sizes. The Code Auditor Agent solves this systematically — not by blindly deleting code,
but by giving you a complete picture first.

The agent runs in five phases: **Discovery → Detection → Verification → Reporting → Execution**.
Only Phase 1 is live today; Phases 2–5 follow in upcoming releases. Every phase is designed to
be reversible, auditable, and non-destructive by default.

**When to run it:** quarterly reviews, pre-release cleanups, or after large refactors that likely
left dead code behind.

---

## The 5 Phases

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1 ✅  │  Discovery & Analysis          │  READ-ONLY          │
│  PHASE 2 🔜  │  Unused Code Detection         │  FLAGS ONLY         │
│  PHASE 3 🔜  │  Safety Verification           │  RISK ASSESSMENT    │
│  PHASE 4 🔜  │  Reporting                     │  REPORT GENERATION  │
│  PHASE 5 🔜  │  Execution & Rollback          │  STAGED + REVERSIBLE│
└─────────────────────────────────────────────────────────────────────┘
```

---

### Phase 1 — Discovery & Analysis ✅ Live

Scans every Python, JavaScript, and TypeScript file in your project. Builds a complete
import/export dependency map and detects circular dependencies.

- Scans all `.py`, `.js`, `.ts`, `.tsx` files
- Resolves import paths to absolute file references
- Detects circular dependency chains
- **Output:** `audit_report.json` + statistics summary
- **Time:** ~10–60 seconds depending on project size
- **Safety:** 100% read-only — no files are modified or created in your project

---

### Phase 2 — Unused Code Detection 🔜 Coming Soon

Cross-references the dependency map against all entry points to find code that is imported
nowhere.

- Detects unused exports, orphan files, dead variables
- Cross-references against test files to avoid false positives
- Assigns confidence scores (LOW / MEDIUM / HIGH certainty)
- **Output:** Ranked candidate list with evidence
- **Safety:** Flags-only — nothing is executed

---

### Phase 3 — Safety Verification 🔜 Coming Soon

Before anything is marked for removal, this phase stress-tests every candidate against
real-world safety checks.

- Test coverage verification (does a test reference this code?)
- API endpoint detection (is this a reachable route?)
- Environment variable usage scan
- Database migration detection
- **Output:** Risk assessment report + mitigation plan per candidate

---

### Phase 4 — Reporting 🔜 Coming Soon

Generates a structured, human-readable cleanup proposal organized by risk level.

- Categorizes findings as LOW / MEDIUM / HIGH risk
- Shows the full dependency graph for each candidate
- Provides removal scenarios with projected impact
- **Output:** Markdown + JSON report ready for review

---

### Phase 5 — Execution & Rollback 🔜 Coming Soon

Only executes after explicit per-item human approval. Staged, reversible, and fully auditable.

- **Dry-run mode:** preview all changes without touching files
- **Staged batches:** removes 1–3 items per session (not bulk deletes)
- **Atomic git commits:** one commit per removed unit
- **Rollback guarantee:** `git revert {hash}` always works
- **Output:** Cleaned codebase with full audit trail

---

## Safety Principles

This is not a bulk-delete tool. The agent's core value is that you stay in control at every step.

### ✅ What the Agent WILL Do

- Read every file in your project during Phase 1
- Analyze all import/export relationships
- Flag potential dead code with evidence
- Generate detailed reports before any action
- Show exact diff previews before Phase 5 runs (dry-run)
- Create individual, reversible git commits per removal

### ❌ What the Agent Will NEVER Do

- Delete files without explicit per-item approval
- Remove API endpoints without a deprecation warning
- Touch or read `.env` / `.env.*` files
- Remove database migration files
- Delete test files (`test_*.py`, `*.test.ts`, etc.)
- Make changes outside of a git-tracked working directory
- Proceed if any test suite would fail after the change

### 🔒 Protected Patterns — Never Touched

These file patterns are permanently excluded from removal candidates, regardless of usage signals:

| Pattern | Reason |
|---|---|
| `.env`, `.env.*` | Environment secrets |
| `__init__.py` | Python package markers |
| `conftest.py`, test fixtures | Test infrastructure |
| `*/migrations/*.py` | Database migration history |
| Route handlers (`@app.get`, `@router.*`) | Live API endpoints |
| `settings.py`, `config.py` | Project configuration |
| Files with top-level side effects | Could break on import |
| Dynamically loaded modules (`importlib.*`) | Can't be statically analyzed |

---

## Getting Started

### Requirements

- Python 3.10+
- Git (repository must be initialized)
- The project you want to audit must be locally cloned

### Installation

```bash
# Clone the agent alongside your project (or into it)
git clone https://github.com/rdg/code-auditor-agent agents/code_auditor

# Install dependencies
cd agents/code_auditor
pip install -r requirements.txt

# Verify installation
python3 agents/code_auditor/phase1_discovery.py --help
```

### Quick Test

```bash
python3 agents/code_auditor/phase1_discovery.py --project . --output audit_report.json
```

If you see `✅ Phase 1 complete — N files scanned` the agent is working correctly.

### Configuration

Open `agents/code_auditor/phase1_config.py` and set `PROJECT_ROOT` to your project path.
All other defaults are safe to leave as-is for a first run.

---

## Phase 1 Usage Guide

### Command

```bash
python3 agents/code_auditor/phase1_discovery.py \
  --project . \
  --output audit_report.json \
  --verbose
```

| Flag | Description | Default |
|---|---|---|
| `--project` | Root directory to scan | `.` (current dir) |
| `--output` | JSON report file path | `audit_report.json` |
| `--verbose` | Print file-by-file progress | off |
| `--timeout` | Max scan time in seconds | `120` |

### What to Expect

```
🔍 Scanning: src/api/routes.py
🔍 Scanning: src/utils/helpers.py
🔍 Scanning: src/models/user.py
...
✅ Phase 1 complete
   Files scanned:    142
   Imports mapped:   891
   Circular deps:    2
   Time elapsed:     8.4s
   Report saved:     audit_report.json
```

### Understanding the Output

```json
{
  "meta": {
    "project_root": "/home/randy/my-project",
    "scanned_at": "2026-04-08T10:32:00Z",
    "total_files": 142
  },
  "statistics": {
    "python_files": 98,
    "js_ts_files": 44,
    "total_imports": 891,
    "circular_dependencies": 2
  },
  "files": {
    "src/utils/helpers.py": {
      "imports": ["os", "json", "src.models.user"],
      "exports": ["format_date", "parse_env", "slugify"],
      "size_bytes": 1840,
      "circular": false
    }
  },
  "circular_chains": [
    ["src/services/auth.py", "src/models/user.py", "src/services/auth.py"]
  ]
}
```

**Fields explained:**

- `files[path].imports` — every module this file depends on
- `files[path].exports` — functions/classes this file exposes
- `files[path].circular` — `true` if this file is part of a circular chain
- `circular_chains` — full circular dependency paths (read left-to-right)
- `statistics.total_imports` — total import statements across all files

**Interpreting statistics:** A `circular_dependencies` count above 0 is worth investigating
before Phase 2 runs — circular imports can cause false "unused" detections.

### Common Issues & Solutions

| Problem | Likely Cause | Solution |
|---|---|---|
| `0 files found` | Wrong `--project` path | Check the path exists and contains source files |
| `Timeout after 120s` | Project is very large | Add large build dirs to `IGNORE_DIRS` in config |
| `Permission denied` | `.env` file in scan path | Add `.env` to `IGNORE_FILES` (it's there by default) |
| `Import parsing fails` | Dynamic import syntax | Safe to ignore — logged but not fatal |
| `JSON decode error` | Interrupted previous run | Delete stale `audit_report.json` and re-run |

---

## Integration Examples

### Example 1 — Standalone (Python script)

```python
from agents.code_auditor.phase1_discovery import Phase1Discovery
import asyncio

async def run():
    scanner = Phase1Discovery(project_root=".")
    registry = await scanner.scan_project()

    print(f"Files scanned: {registry.statistics['total_files']}")
    print(f"Circular deps: {registry.statistics['circular_dependencies']}")

    # Iterate all discovered files
    for path, file_info in registry.files.items():
        print(f"{path}: {len(file_info.exports)} exports")

asyncio.run(run())
```

### Example 2 — With FastAPI (audit endpoint)

```python
from fastapi import BackgroundTasks
from agents.code_auditor.phase1_discovery import Phase1Discovery

@app.post("/audit/phase1")
async def start_audit(project_path: str, background_tasks: BackgroundTasks):
    """Kick off Phase 1 scan in the background."""
    scanner = Phase1Discovery(project_root=project_path)
    background_tasks.add_task(scanner.scan_and_save, output="audit_report.json")
    return {"status": "scanning", "report": "audit_report.json"}
```

### Example 3 — CI/CD (GitHub Actions)

```yaml
name: Code Audit

on:
  schedule:
    - cron: '0 9 1 */3 *'   # Quarterly, first of the month

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r agents/code_auditor/requirements.txt
      - name: Run Phase 1
        run: |
          python3 agents/code_auditor/phase1_discovery.py \
            --project . \
            --output audit_report.json \
            --verbose
      - uses: actions/upload-artifact@v4
        with:
          name: audit-report
          path: audit_report.json
```

---

## Configuration Reference

Configuration lives in `agents/code_auditor/phase1_config.py`.

```python
# ── Directories to skip entirely ─────────────────────────────────────
IGNORE_DIRS = [
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "coverage", ".pytest_cache",
]

# ── File patterns to skip ─────────────────────────────────────────────
IGNORE_FILES = [
    ".env", ".env.*", "*.pyc", "*.min.js",
]

# ── File extensions to scan ───────────────────────────────────────────
SUPPORTED_EXTENSIONS = [".py", ".js", ".ts", ".tsx", ".jsx"]

# ── Safety limits ─────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 500_000    # Skip files larger than 500KB
SCAN_TIMEOUT_SECONDS = 120       # Abort if scan takes too long
MAX_IMPORT_DEPTH = 20            # Circular dep detection depth limit
```

### Per-Project Config Override

Create `audit_config.local.py` in your project root to override defaults without editing
the agent source:

```python
# audit_config.local.py
from agents.code_auditor.phase1_config import *

IGNORE_DIRS += ["legacy", "archive"]
SUPPORTED_EXTENSIONS += [".vue"]
```

Then run with `--config audit_config.local.py`.

---

## Understanding the Report

### JSON Structure

```
audit_report.json
├── meta              — scan metadata (when, where, version)
├── statistics        — totals and summary numbers
├── files             — per-file dependency data (the main payload)
└── circular_chains   — list of circular import paths
```

### Reading the Statistics Block

```json
"statistics": {
  "python_files": 98,
  "js_ts_files": 44,
  "total_files": 142,
  "total_imports": 891,
  "total_exports": 634,
  "circular_dependencies": 2,
  "scan_duration_ms": 8400
}
```

- **`total_imports` vs `total_exports`** — a large gap here suggests many re-exports or
  possible dead code accumulation.
- **`circular_dependencies`** — any value > 0 should be reviewed before running Phase 2.
  Circular imports can create false negatives in unused code detection.

### CSV Export

Add `--csv audit_report.csv` to get a flat, spreadsheet-friendly export. Useful for
quick reviews without parsing JSON.

---

## FAQ

**Q: Can this delete my API endpoints?**
A: No. API route handlers are in the protected patterns list (see Safety Principles).
Phase 3 adds a secondary check before any route-adjacent file is flagged.

**Q: What if Phase 1 misses a file?**
A: Phase 1 is intentionally conservative — it reports what it statically detects.
Dynamic imports (`importlib`, `require()` with variables) are logged as unresolvable
and excluded from candidates in Phase 2. Nothing is flagged as unused unless Phase 1
can prove it.

**Q: Can I undo changes made in Phase 5?**
A: Yes. Every removal in Phase 5 is a single atomic git commit. Run
`git revert {commit_hash}` to restore any removed file instantly.

**Q: How often should I run the audit?**
A: Quarterly is a good baseline for active projects. Also run it after large refactors,
feature removals, or dependency upgrades that touched many files.

**Q: Does it work with TypeScript and Next.js?**
A: Yes. Phase 1 scans `.ts`, `.tsx`, `.jsx`, and `.js` files. Next.js projects are
fully supported — `pages/`, `app/`, and `src/` directories are all scanned.

**Q: Will running this break my running tests?**
A: Phase 1 is read-only and cannot affect your tests. Phase 5 (when live) verifies
the full test suite passes before committing any removal.

**Q: What about files loaded with `require()` or `importlib`?**
A: These are flagged as "dynamic import — cannot verify" in the report. They will
never be proposed for removal in Phase 2.

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `0 files found` | Wrong path or no matching extensions | Verify `--project` path; check `SUPPORTED_EXTENSIONS` |
| `JSON decode error on output` | Previous run was interrupted | Delete the output file and re-run |
| `Import parsing fails on X.py` | Complex or dynamic import syntax | Safe to ignore; file is excluded from candidates |
| `Circular dep count seems wrong` | Nested re-export chains | Run `--verbose` and review `circular_chains` in output |
| `Timeout reached` | Very large monorepo | Add build directories to `IGNORE_DIRS`; increase `SCAN_TIMEOUT_SECONDS` |
| `Permission denied: .env` | `.env` in scan path | Confirm `.env` is in `IGNORE_FILES` (default: yes) |

---

## Next Steps

### What's Live Now

- ✅ **Phase 1 — Discovery & Analysis** — scan any project, get full dependency map

### What's Coming

| Phase | ETA | Description |
|---|---|---|
| Phase 2 | Q3 2026 | Unused export detection with confidence scores |
| Phase 3 | Q3 2026 | Safety verification (tests, APIs, migrations) |
| Phase 4 | Q4 2026 | Structured Markdown + JSON reporting |
| Phase 5 | Q4 2026 | Staged execution with dry-run + rollback |

### Stay Updated

Watch the repository for release tags. Each phase ships as a tagged release with a
`CHANGELOG.md` entry describing exactly what changed.

### Filing Issues or Feedback

Open an issue in the project repository. Include your Phase 1 `audit_report.json`
(redact any sensitive paths) and the exact command you ran.

---

## Appendix

### A — Full Config Options

```python
# agents/code_auditor/phase1_config.py — all available options

PROJECT_ROOT          = "."                    # Default scan root
OUTPUT_FILE           = "audit_report.json"    # Default output path
VERBOSE               = False                  # Per-file progress logging
IGNORE_DIRS           = [...]                  # See defaults above
IGNORE_FILES          = [...]                  # See defaults above
SUPPORTED_EXTENSIONS  = [...]                  # See defaults above
MAX_FILE_SIZE_BYTES   = 500_000                # Skip oversized files
SCAN_TIMEOUT_SECONDS  = 120                    # Hard timeout
MAX_IMPORT_DEPTH      = 20                     # Circular detection limit
EXPORT_CSV            = False                  # Also write .csv output
```

### B — Sample JSON Output (Annotated)

```json
{
  "meta": {
    "agent_version": "1.0.0",
    "project_root": "/home/randy/my-project",  // ← absolute path at scan time
    "scanned_at": "2026-04-08T10:32:00Z",
    "git_branch": "main",
    "git_commit": "a3f92b1"
  },
  "statistics": {
    "total_files": 142,          // ← all scanned files
    "python_files": 98,
    "js_ts_files": 44,
    "total_imports": 891,        // ← total import statements found
    "total_exports": 634,        // ← total exported symbols found
    "circular_dependencies": 2,  // ← number of circular import chains
    "scan_duration_ms": 8400
  },
  "files": {
    "src/utils/helpers.py": {
      "imports": ["os", "json", "src.models.user"],  // ← what this file needs
      "exports": ["format_date", "parse_env"],       // ← what this file provides
      "size_bytes": 1840,
      "circular": false,                             // ← part of a circular chain?
      "last_modified": "2026-03-12T08:22:00Z"
    }
  },
  "circular_chains": [
    ["src/services/auth.py", "src/models/user.py", "src/services/auth.py"]
    // ↑ read as: auth imports user, user imports auth — circular
  ]
}
```

### C — Glossary

| Term | Meaning |
|---|---|
| **Import** | A dependency statement (`import x`, `require('x')`) |
| **Export** | A symbol made available to other modules |
| **Orphan file** | A file not imported by any other file in the project |
| **Dead code** | Code that exists but is never called or imported |
| **Circular dependency** | A → B → A; two or more files that mutually import each other |
| **Confidence score** | Phase 2 metric: how certain the agent is that code is unused |
| **Dry run** | Phase 5 mode that shows changes without applying them |

### D — Recommended Git Workflow for Code Cleanup

```bash
# 1. Create a cleanup branch
git checkout -b cleanup/phase5-batch-1

# 2. Run Phase 5 in dry-run first
python3 agents/code_auditor/phase5_execute.py --dry-run --batch 1

# 3. Review the proposed diff
git diff --staged

# 4. If satisfied, apply
python3 agents/code_auditor/phase5_execute.py --apply --batch 1

# 5. Run tests
npm test && pytest

# 6. Merge or rollback
git merge cleanup/phase5-batch-1   # ← if tests pass
git revert HEAD                     # ← if anything breaks
```

### E — Contact & Support

For questions, bug reports, or Phase 2 preview access — open an issue in the project
repository or reach out via the engineering Slack channel.

---

*Code Auditor Agent — built for Randy's engineering team. Safety first, always.*
