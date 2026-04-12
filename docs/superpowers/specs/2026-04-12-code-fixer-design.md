# Code Fixer Agent — Design Spec
**Date:** 2026-04-12  
**Status:** Approved  
**Location:** `agents/code_fixer/`

---

## 1. Purpose

Code Fixer is a **production orchestrator** for Code Auditor. Code Auditor (phases 1–4) detects and verifies unused code; Code Fixer batches those verified findings, executes removals via Auditor's Phase 5 engine, tests each batch, commits atomically, and produces a machine- and human-readable report.

**Without Code Fixer:** 138 items removed manually (one `auditor execute` call each) — 4–5 hours of tedious, error-prone work.  
**With Code Fixer:** `fixer fix --report phase3_verified.json` — 15–30 minutes, 100% reversible, full audit trail.

---

## 2. Scope

| Concern | Code Auditor | Code Fixer |
|---|---|---|
| Find unused code | ✅ Phases 1–4 | ❌ |
| Remove one item | ✅ Phase 5 | ✅ (calls Phase 5) |
| Batch 50+ items | ❌ | ✅ |
| Test per batch | ❌ | ✅ |
| Commit per batch | ❌ | ✅ |
| Risk filtering | ❌ | ✅ |
| 6-layer safety validation | ❌ | ✅ |
| HTML + JSON reporting | ❌ | ✅ |
| Scheduler-ready output | ❌ | ✅ |

---

## 3. File Structure

```
agents/code_fixer/
  cli.py                      ← Entry point: FixerEngine + 5 cmd_* functions
  core/
    __init__.py
    safety_validator.py       ← SafetyValidator (6-layer pre-flight)
    git_orchestrator.py       ← GitOrchestrator (all git/subprocess calls)
    report_generator.py       ← ReportGenerator (HTML + JSON output)
  tests/
    __init__.py
    test_safety_validator.py
    test_git_orchestrator.py
    test_report_generator.py
```

**Import contract:**
- `cli.py` and core modules import `BatchRemover`, `DryRunExecutor` from `agents.code_auditor.core.phase5_executor`
- `report_generator.py` imports `HTMLExporter`, `CSVExporter` from `agents.code_auditor.core.phase4_reporting`
- No other cross-agent imports

---

## 4. Data Flow

```
phase3_verified.json
       │
       ▼
FixerEngine.load_report()
  • reads "all_checks" list (normalised from "assessments" if needed)
  • filters by --risk threshold (LOW / LOW+MEDIUM / LOW+MEDIUM+HIGH)
  • filters by --items (specific IDs) if provided
       │
       ▼
FixerEngine.build_batches()
  • sorts: risk ASC → confidence DESC → type (orphan_file first)
  • chunks into groups of --batch-size (default 3)
       │
       ▼
For each batch (FixerEngine.run_batch):
  ┌──────────────────────────────────────────────────────────────┐
  │ 1. SafetyValidator.validate_batch(batch)                      │
  │    • dry-run via DryRunExecutor → abort if is_safe=False      │
  │                                                               │
  │ 2. BatchRemover.remove_batch(ids, phase3_data)                │
  │    • deletes/edits files on feature branch                    │
  │                                                               │
  │ 3. run pytest (if available)                                  │
  │    pass  → continue                                           │
  │    fail + default      → STOP + GitOrchestrator.cleanup()    │
  │    fail + --skip-failed → log + next batch                    │
  │    fail + --no-cleanup  → leave branch + STOP                 │
  │                                                               │
  │ 4. GitOrchestrator.commit_batch(message, files)               │
  │    • "fix: remove <id1>, <id2>, <id3> (LOW risk)"             │
  └──────────────────────────────────────────────────────────────┘
       │
       ▼
ReportGenerator.write_reports()
  • fix_report_YYYYMMDD_HHMMSS.json
  • fix_report_YYYYMMDD_HHMMSS.html
```

---

## 5. Module Specifications

### 5.1 `SafetyValidator`

Pre-flight checks only. **No file modifications.**

| Layer | Check | Failure action |
|---|---|---|
| 1 | `phase3_verified.json` parses as valid JSON with `all_checks` key | Hard abort (exit 3) |
| 2 | Git working tree is clean (no uncommitted changes) | Hard abort (exit 3) |
| 3 | All requested item IDs exist in the report | Hard abort (exit 3) |
| 4 | Item risk level ≤ requested threshold | Skip item with warning |
| 5 | `DryRunExecutor` returns `is_safe=True` for the batch | Abort batch per failure strategy |
| 6 | Baseline pytest run passes before any changes | Hard abort (exit 3) |

```python
class SafetyValidator:
    def __init__(self, report_data: dict, project_root: Path, verbose: bool = False)
    def validate_report(self) -> ValidationResult
    def validate_batch(self, batch: List[str]) -> ValidationResult
    def run_baseline_tests(self) -> TestResult
```

### 5.2 `GitOrchestrator`

All `subprocess`/git calls are isolated here. The CLI and `FixerEngine` never call `subprocess` directly.

```python
class GitOrchestrator:
    def __init__(self, project_root: Path, verbose: bool = False)
    def is_clean(self) -> bool
    def current_branch(self) -> str
    def commit_batch(self, message: str) -> str           # returns commit hash
    def cleanup_branch(self, branch: str) -> None         # checkout main + delete branch
    def get_status(self) -> dict                          # branch, clean, audit branches
    def list_audit_branches(self) -> List[str]
```

> **Note:** Branch *creation* is handled by `BatchRemover.create_feature_branch()` (inherited from Code Auditor Phase 5). `GitOrchestrator` covers the operations `BatchRemover` does not: committing, cleanup on failure, and status reporting.

### 5.3 `ReportGenerator`

Produces two output files per run. Reuses `HTMLExporter` pattern from `phase4_reporting.py`.

```python
class ReportGenerator:
    def __init__(self, run_data: dict)
    def write_json(self, path: Path) -> None
    def write_html(self, path: Path) -> None
```

`run_data` schema:
```json
{
  "run_id": "20260412_143022",
  "started_at": "ISO timestamp",
  "finished_at": "ISO timestamp",
  "report_input": "phase3_verified.json",
  "risk_filter": "LOW",
  "batch_size": 3,
  "total_candidates": 97,
  "batches_attempted": 33,
  "batches_succeeded": 32,
  "batches_failed": 1,
  "items_fixed": 96,
  "items_failed": ["U055", "U056", "U057"],
  "lines_removed": 2280,
  "commits": ["abc1234", "def5678", "..."],
  "batches": [ /* per-batch detail */ ]
}
```

### 5.4 `FixerEngine` (in `cli.py`)

Orchestrates the full run. Instantiated by `cmd_fix`; also importable by Scheduler Agent.

```python
class FixerEngine:
    def __init__(self, report_path: Path, project_root: Path, ...)
    def load_report(self) -> List[dict]           # parsed + filtered candidates
    def build_batches(self) -> List[List[str]]    # ordered list of ID batches
    def run(self) -> RunResult                    # full execution loop
    def dry_run(self) -> DryRunSummary            # preview with no changes
```

---

## 6. CLI Reference

```
python agents/code_fixer/cli.py <subcommand> [options]
```

### `fix`
```
fix --report phase3_verified.json
    [--items U001 U002 ...]    # restrict to specific IDs
    [--risk LOW|MEDIUM|HIGH]   # default: LOW
    [--dry-run]                # preview only, no changes
    [--batch-size 3]           # default: 3
    [--skip-failed]            # best-effort: skip failing batches, continue
    [--no-cleanup]             # leave failed branch for manual debug
    [--verbose]
```

### `analyze`
```
analyze --report phase3_verified.json
        [--verbose]
```
Prints: counts by risk, estimated lines, recommended batch count, estimated runtime.

### `plan`
```
plan --report phase3_verified.json
     [--output fix_plan_DATE.json]
```
Writes: ordered list of batches with IDs, lines estimate, safety score.

### `status`
```
status
```
Prints: current branch, clean/dirty, open `audit/remove-*` branches, last fix report path.

### `verify`
```
verify --report phase3_verified.json
       --items U001 U002 U003
```
Runs `SafetyValidator` on the specified items and prints per-layer pass/fail + go/no-go.

---

## 7. Progress Output

All progress goes to `stdout`; errors go to `stderr`.

```
🔍 Loading phase3_verified.json... 97 LOW-risk candidates
📋 Building batches: 33 batches × 3 items
🔒 Safety baseline: pytest 42 passed in 3.1s ✅

✅ Batch  1/33: U010, U011, U012  →  45 lines  →  abc1234
✅ Batch  2/33: U013, U014, U015  →  88 lines  →  def5678
❌ Batch  3/33: U016, U017, U018  →  tests failed  →  cleaned up
...

📊 Run complete
   Fixed:   96 items / 2280 lines removed
   Failed:   1 batch (3 items) — see fix_report_20260412_1430.html
   Commits: 32 atomic commits on main
```

---

## 8. Exit Codes

| Code | Meaning |
|---|---|
| `0` | All batches succeeded |
| `1` | Partial success (`--skip-failed`, some batches failed) |
| `2` | Full stop — batch failed, repo cleaned up |
| `3` | Pre-flight failure (validation, dirty tree, bad report) |
| `4` | Input error (bad args, file not found) |

---

## 9. Error Messages

All errors include an actionable next step:

```
❌ Error: phase3_verified.json not found
   Run: python agents/code_auditor/cli.py verify --report phase2_findings.json

❌ Error: git working tree is dirty
   Run: git stash   or   git commit -am "wip"

❌ Error: item U999 not found in report
   Available IDs: U001–U138
   Run: python agents/code_fixer/cli.py analyze --report phase3_verified.json

❌ Error: code_auditor modules not found
   Run from repo root: python agents/code_fixer/cli.py ...
```

---

## 10. pytest Integration

- **Not installed:** warning logged, test step skipped, execution continues
- **No test files found:** test step skipped, execution continues
- **Baseline fails:** hard abort (exit 3) before any changes
- **Batch fails:** apply failure strategy (stop/skip/no-cleanup)

---

## 11. Risk Threshold Mapping

| `--risk` | Items included |
|---|---|
| `LOW` (default) | LOW only |
| `MEDIUM` | LOW + MEDIUM |
| `HIGH` | LOW + MEDIUM + HIGH |

---

## 12. Testing

Three test files, all using mocks — no real git or file system required:

- `test_safety_validator.py` — mock `DryRunExecutor`; test each of the 6 layers independently; assert `ValidationResult` fields
- `test_git_orchestrator.py` — mock `subprocess.run`; assert correct git command sequences for create/commit/cleanup flows
- `test_report_generator.py` — feed fixture `run_data`; assert HTML contains expected sections; assert JSON schema matches spec

---

## 13. Open Questions

None — all design decisions resolved during brainstorming.
