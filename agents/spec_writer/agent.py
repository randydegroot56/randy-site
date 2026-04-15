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
        if fmt not in ("json", "md"):
            raise ValueError(f"Unsupported format '{fmt}'. Use json or md.")
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
        prefix = f"spec_{today}_"
        count = sum(1 for s in self._formatter.list_specs() if s["spec_id"].startswith(prefix))
        return f"spec_{today}_{count + 1:03d}"
