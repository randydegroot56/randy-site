"""ScaffolderAgent — generates project skeletons from SpecDocs."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.events import ScaffoldCleaned, ScaffoldCompleted, ScaffoldFailed
from agents.orchestrator.state import StateStore
from agents.scaffolder.blueprint_resolver import BlueprintResolver
from agents.scaffolder.file_generator import FileGenerator
from agents.scaffolder.structure_generator import StructureGenerator, _derive_name_variants
from agents.scaffolder.validator import ScaffoldValidator

DEFAULT_SCAFFOLDS_DIR = Path.home() / ".agent-orchestrator" / "scaffolds"


class ScaffolderAgent(BaseAgent):
    """Generates project skeletons from specs using declarative blueprints."""

    name = "scaffold"
    description = "Generates project skeletons from specs using declarative blueprints"

    def __init__(
        self,
        bus: EventBus,
        state: StateStore,
        registry=None,
        scaffolds_dir: Path = DEFAULT_SCAFFOLDS_DIR,
    ) -> None:
        super().__init__(bus=bus, state=state)
        self._registry = registry
        self._scaffolds_dir = Path(scaffolds_dir)
        self._resolver = BlueprintResolver()
        self._generator = StructureGenerator()
        self._file_gen = FileGenerator()
        self._validator = ScaffoldValidator()
        bus.subscribe("SpecCreated", self._on_spec_event)

    def _on_spec_event(self, event) -> None:
        spec_id = event.payload.get("spec_id")
        if not spec_id:
            return
        try:
            self._generate(spec_id=spec_id, force=False)
        except Exception as exc:
            self.emit(ScaffoldFailed(
                agent_name=self.name,
                error=str(exc),
                payload={"spec_id": spec_id, "error": str(exc)},
            ))

    def run(self, args: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]:
        args = list(args or [])
        parser = argparse.ArgumentParser(
            prog="orchestrator scaffold", add_help=False, exit_on_error=False
        )
        sub = parser.add_subparsers(dest="subcommand")

        gen_p = sub.add_parser("generate")
        gen_p.add_argument("spec_id")
        gen_p.add_argument("--force", action="store_true")

        re_p = sub.add_parser("re-scaffold")
        re_p.add_argument("spec_id")

        sub.add_parser("list")

        show_p = sub.add_parser("show")
        show_p.add_argument("spec_id")

        val_p = sub.add_parser("validate")
        val_p.add_argument("spec_id")

        clean_p = sub.add_parser("clean")
        clean_p.add_argument("spec_id")

        try:
            parsed = parser.parse_args(args)
        except (argparse.ArgumentError, SystemExit) as exc:
            available = "generate, re-scaffold, list, show, validate, clean"
            raise ValueError(
                f"Unknown scaffold subcommand. Available: {available}"
            ) from exc

        dispatch = {
            "generate":    self._cmd_generate,
            "re-scaffold": self._cmd_rescaffold,
            "list":        self._cmd_list,
            "show":        self._cmd_show,
            "validate":    self._cmd_validate,
            "clean":       self._cmd_clean,
        }
        if not parsed.subcommand or parsed.subcommand not in dispatch:
            available = ", ".join(sorted(dispatch))
            raise ValueError(f"Unknown scaffold subcommand. Available: {available}")
        return dispatch[parsed.subcommand](parsed)

    def _cmd_generate(self, parsed) -> Dict[str, Any]:
        return self._generate(spec_id=parsed.spec_id, force=parsed.force)

    def _cmd_rescaffold(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        if not (output_dir / "manifest.json").exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")
        from agents.spec_writer.formatter import SpecFormatter
        from agents.spec_writer.agent import DEFAULT_SPECS_DIR
        spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(parsed.spec_id)
        variants = _derive_name_variants(spec.project.name or "project")
        blueprint, _ = self._resolver.resolve(spec)
        context = {
            "spec_id": parsed.spec_id,
            "project": spec.project,
            "features": spec.features,
            "technical": spec.technical,
            "constraints": spec.constraints,
            "conventions": [],
            "blueprint_name": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).date().isoformat(),
            **variants,
        }
        rendered_files = self._generator.generate(blueprint, context)
        to_write = [
            rf for rf in rendered_files
            if not (output_dir / rf.relative_path).exists()
            or (output_dir / rf.relative_path).stat().st_size == 0
        ]
        written_paths = self._file_gen.write(to_write, output_dir, spec_id=parsed.spec_id)
        vr = self._validator.validate(output_dir)
        payload = {
            "spec_id": parsed.spec_id,
            "blueprint": blueprint.name,
            "output_dir": str(output_dir),
            "files_written": len(written_paths),
            "warnings": vr.warnings,
        }
        self.emit(ScaffoldCompleted(agent_name=self.name, payload=payload))
        print(f"Re-scaffolded {len(written_paths)} file(s) in {output_dir}")
        return payload

    def _cmd_list(self, parsed) -> Dict[str, Any]:
        scaffolds = []
        if self._scaffolds_dir.exists():
            for d in sorted(self._scaffolds_dir.iterdir()):
                mp = d / "manifest.json"
                if mp.exists():
                    try:
                        m = json.loads(mp.read_text(encoding="utf-8"))
                        scaffolds.append({
                            "spec_id":       m.get("spec_id", d.name),
                            "blueprint":     m.get("blueprint", "?"),
                            "scaffold_date": m.get("scaffold_date", "?"),
                        })
                    except Exception:
                        pass
        for s in scaffolds:
            print(f"  [{s['blueprint']:20}] {s['spec_id']}  {s['scaffold_date']}")
        return {"scaffolds": scaffolds}

    def _cmd_show(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        mp = output_dir / "manifest.json"
        if not mp.exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        print(f"Scaffold: {parsed.spec_id}  Blueprint: {manifest.get('blueprint')}")
        for f in manifest.get("files", []):
            exists = "v" if (output_dir / f["relative_path"]).exists() else "x"
            print(f"  {exists} {f['relative_path']}")
        return manifest

    def _cmd_validate(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        vr = self._validator.validate(output_dir)
        status = "OK" if vr.ok else "FAIL"
        print(f"Validation [{status}]: {parsed.spec_id}")
        for m in vr.missing:
            print(f"  missing: {m}")
        for e in vr.empty:
            print(f"  empty:   {e}")
        for w in vr.warnings:
            print(f"  {w}")
        return {"ok": vr.ok, "missing": vr.missing, "empty": vr.empty, "warnings": vr.warnings}

    def _cmd_clean(self, parsed) -> Dict[str, Any]:
        output_dir = self._scaffolds_dir / parsed.spec_id
        if not output_dir.exists():
            raise FileNotFoundError(f"No scaffold found for spec_id '{parsed.spec_id}'")
        shutil.rmtree(output_dir)
        self.emit(ScaffoldCleaned(
            agent_name=self.name,
            payload={"spec_id": parsed.spec_id},
        ))
        print(f"Scaffold cleaned: {parsed.spec_id}")
        return {"spec_id": parsed.spec_id, "cleaned": True}

    def _generate(self, spec_id: str, force: bool = False) -> Dict[str, Any]:
        from agents.spec_writer.formatter import SpecFormatter
        from agents.spec_writer.agent import DEFAULT_SPECS_DIR
        spec = SpecFormatter(specs_dir=DEFAULT_SPECS_DIR).load(spec_id)
        output_dir = self._scaffolds_dir / spec_id
        output_dir.mkdir(parents=True, exist_ok=True)

        conventions: list[str] = []
        if self._registry:
            try:
                result = self._registry.get("memory", self._bus, self._state).run(
                    args=["query", f"{spec.project.name} patterns"]
                )
                conventions = [e["content"] for e in result.get("results", [])]
            except Exception:
                pass

        variants = _derive_name_variants(spec.project.name or "project")
        blueprint, bp_warnings = self._resolver.resolve(spec)
        context = {
            "spec_id": spec_id,
            "project": spec.project,
            "features": spec.features,
            "technical": spec.technical,
            "constraints": spec.constraints,
            "conventions": conventions,
            "blueprint_name": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).date().isoformat(),
            **variants,
        }

        rendered_files = self._generator.generate(blueprint, context)
        written_paths = self._file_gen.write(rendered_files, output_dir, force=force, spec_id=spec_id)

        manifest = {
            "spec_id": spec_id,
            "blueprint": blueprint.name,
            "blueprint_version": blueprint.version,
            "scaffold_date": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(output_dir),
            "warnings": bp_warnings,
            "files": [
                {
                    "relative_path": rf.relative_path,
                    "header": rf.header,
                    "size_bytes": (output_dir / rf.relative_path).stat().st_size,
                }
                for rf in rendered_files
            ],
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        vr = self._validator.validate(output_dir)
        all_warnings = bp_warnings + vr.warnings
        payload = {
            "spec_id": spec_id,
            "blueprint": blueprint.name,
            "output_dir": str(output_dir),
            "files_written": len(written_paths),
            "warnings": all_warnings,
        }
        self.emit(ScaffoldCompleted(agent_name=self.name, payload=payload))
        print(f"Scaffold generated: {output_dir}")
        print(f"  Blueprint: {blueprint.name} v{blueprint.version}")
        print(f"  Files: {len(written_paths)}")
        for w in all_warnings:
            print(f"  {w}")
        return payload
