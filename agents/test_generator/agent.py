"""
agents/test_generator/agent.py
================================
TestGeneratorAgent — registered as "testgen" in AgentRegistry.

run(args=[subcommand, ...]) dispatches via argparse:
    generate --from-spec <spec_id>
    generate --from-code <path> [--spec <spec_id>]
    coverage <path>
    validate <test_path>
    list
    run <test_path>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import CoverageReport, TestsFailed, TestsGenerated, TestsPassed
from agents.orchestrator.state import StateStore
from agents.test_generator.analyzer import CodeAnalyzer, EXTENSION_MAP
from agents.test_generator.planner import TestPlanner
from agents.test_generator.validator import TestValidator
from agents.test_generator.writer import TestWriter, DEFAULT_TEMPLATES_DIR

DEFAULT_TESTS_DIR = Path("tests")


class TestGeneratorAgent(BaseAgent):
    """Generates test files from specs or existing source code."""

    name = "testgen"
    description = "Generates test files from specs or existing source code"

    def __init__(
        self,
        bus: EventBus,
        state: StateStore,
        registry=None,
        tests_dir: Path = DEFAULT_TESTS_DIR,
        auto_generate: bool = False,
    ) -> None:
        super().__init__(bus=bus, state=state)
        self._registry = registry
        self._tests_dir = Path(tests_dir)
        self._auto_generate = auto_generate
        self._analyzer = CodeAnalyzer()
        self._planner = TestPlanner()
        self._writer = TestWriter(templates_dir=DEFAULT_TEMPLATES_DIR)
        self._validator = TestValidator()

        if auto_generate:
            bus.subscribe("SpecCreated", self._on_spec_event)
            bus.subscribe("SpecUpdated", self._on_spec_event)

    # ── Auto-generation ────────────────────────────────────────────────────

    def _on_spec_event(self, event) -> None:
        spec_id = event.payload.get("spec_id")
        if spec_id:
            try:
                self._generate(from_spec=spec_id)
            except Exception:
                pass  # best-effort

    # ── Dispatch ──────────────────────────────────────────────────────────

    def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
        args = list(args or [])
        parser = argparse.ArgumentParser(
            prog="orchestrator test", add_help=False, exit_on_error=False
        )
        sub = parser.add_subparsers(dest="subcommand")

        gen = sub.add_parser("generate")
        gen.add_argument("--from-spec", dest="from_spec", metavar="SPEC_ID")
        gen.add_argument("--from-code", dest="from_code", metavar="PATH")
        gen.add_argument("--spec",      dest="spec",      metavar="SPEC_ID")

        cov = sub.add_parser("coverage")
        cov.add_argument("path")

        val = sub.add_parser("validate")
        val.add_argument("test_path")

        sub.add_parser("list")

        run_cmd = sub.add_parser("run")
        run_cmd.add_argument("test_path")

        try:
            parsed = parser.parse_args(args)
        except (argparse.ArgumentError, SystemExit) as exc:
            available = ", ".join(sorted(["generate", "coverage", "validate", "list", "run"]))
            raise ValueError(
                f"Unknown test subcommand '{args[0] if args else None}'. Available: {available}"
            ) from exc

        dispatch = {
            "generate": self._cmd_generate,
            "coverage": self._cmd_coverage,
            "validate": self._cmd_validate,
            "list":     self._cmd_list,
            "run":      self._cmd_run,
        }
        if parsed.subcommand not in dispatch:
            available = ", ".join(sorted(dispatch))
            raise ValueError(
                f"Unknown test subcommand '{parsed.subcommand}'. Available: {available}"
            )
        return dispatch[parsed.subcommand](parsed)

    # ── Subcommands ────────────────────────────────────────────────────────

    def _cmd_generate(self, parsed) -> Dict[str, Any]:
        if not parsed.from_spec and not parsed.from_code:
            raise ValueError(
                "Usage: test generate --from-spec <id> | --from-code <path> [--spec <id>]"
            )
        return self._generate(
            from_spec=parsed.from_spec,
            from_code=parsed.from_code,
            spec_id=parsed.spec,
        )

    def _generate(
        self,
        from_spec: Optional[str] = None,
        from_code: Optional[str] = None,
        spec_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from agents.spec_writer.formatter import SpecFormatter
        from agents.spec_writer.agent import DEFAULT_SPECS_DIR

        spec = None
        if from_spec:
            spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(from_spec)
        if spec_id and spec is None:
            spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(spec_id)

        module = self._analyzer.analyze(Path(from_code)) if from_code else None

        plan = self._planner.plan(module=module, spec=spec, spec_id=from_spec or "")
        output_path = self._writer.write(plan)
        vr = self._validator.validate(output_path)

        payload = {
            "output_path":        str(output_path),
            "scenarios":          len(plan.scenarios),
            "estimated_coverage": plan.estimated_coverage,
            "passed":             vr.passed,
            "pending":            vr.pending,
            "failed":             vr.failed,
            "errors":             vr.errors,
        }
        self.emit(TestsGenerated(agent_name=self.name, payload=payload))
        print(f"Tests generated: {output_path}")
        print(f"  Scenarios: {len(plan.scenarios)} | Coverage: {plan.estimated_coverage}%")
        print(f"  Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}")
        return payload

    def _cmd_coverage(self, parsed) -> Dict[str, Any]:
        target = Path(parsed.path)
        modules = []
        if target.is_file():
            modules = [self._analyzer.analyze(target)]
        else:
            for ext in EXTENSION_MAP:
                for p in target.rglob(f"*{ext}"):
                    if p.name.startswith("test_") or "test" in p.stem.lower():
                        continue
                    if any(part in ("tests", "__pycache__", "node_modules") for part in p.parts):
                        continue
                    try:
                        modules.append(self._analyzer.analyze(p))
                    except Exception:
                        pass

        with_tests = sum(1 for m in modules if m.has_tests)
        total_fn = sum(len(m.functions) for m in modules)
        coverage = int((with_tests / len(modules)) * 100) if modules else 0

        suggestions = [
            {
                "file": str(m.path),
                "functions": [f.name for f in m.functions if not f.name.startswith("_")],
                "suggested_command": f"orchestrator test generate --from-code {m.path}",
            }
            for m in modules if not m.has_tests
        ]

        report = {
            "files_analyzed":     len(modules),
            "files_with_tests":   with_tests,
            "total_functions":    total_fn,
            "estimated_coverage": coverage,
            "suggestions":        suggestions,
        }
        self.emit(CoverageReport(agent_name=self.name, payload=report))
        print(f"Coverage: {with_tests}/{len(modules)} files have tests ({coverage}%)")
        for s in suggestions:
            print(f"  Missing: {s['file']}")
        return report

    def _cmd_validate(self, parsed) -> Dict[str, Any]:
        path = Path(parsed.test_path)
        vr = self._validator.validate(path)

        if vr.passed + vr.pending > 0 and vr.failed == 0 and vr.errors == 0:
            self.emit(TestsPassed(agent_name=self.name, payload={"path": str(path), "passed": vr.passed}))
        elif vr.failed > 0 or vr.errors > 0:
            self.emit(TestsFailed(
                agent_name=self.name,
                payload={"path": str(path), "failed": vr.failed, "errors": vr.errors},
            ))

        print(f"Validation: {path}")
        print(f"  Syntax OK: {vr.syntax_ok}")
        if vr.missing_imports:
            print(f"  Missing imports: {', '.join(vr.missing_imports)}")
        print(f"  Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}  Errors: {vr.errors}")

        return {
            "path":            str(path),
            "syntax_ok":       vr.syntax_ok,
            "missing_imports": vr.missing_imports,
            "passed":          vr.passed,
            "pending":         vr.pending,
            "failed":          vr.failed,
            "errors":          vr.errors,
        }

    def _cmd_list(self, parsed) -> Dict[str, Any]:
        test_files = []
        for pattern, lang in [("test_*.py", "python"), ("*.test.ts", "typescript"), ("*.test.js", "typescript")]:
            for p in self._tests_dir.rglob(pattern):
                test_files.append({"path": str(p), "language": lang})
        for tf in test_files:
            print(f"  [{tf['language']:10}] {tf['path']}")
        print(f"Total: {len(test_files)} test file(s)")
        return {"test_files": test_files}

    def _cmd_run(self, parsed) -> Dict[str, Any]:
        path = Path(parsed.test_path)
        if not path.exists():
            raise FileNotFoundError(f"Test file not found: {path}")
        vr = self._validator.validate(path)
        print(vr.output)
        print(f"Passed: {vr.passed}  Pending: {vr.pending}  Failed: {vr.failed}  Errors: {vr.errors}")
        return {
            "path":    str(path),
            "passed":  vr.passed,
            "pending": vr.pending,
            "failed":  vr.failed,
            "errors":  vr.errors,
        }
