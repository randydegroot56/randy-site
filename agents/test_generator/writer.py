"""
agents/test_generator/writer.py
==================================
TestWriter — renders Jinja2 templates to produce test files on disk.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from agents.test_generator.planner import TestPlan

DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "templates"


class TestWriter:
    """Loads Jinja2 templates and renders test files to disk."""

    def __init__(self, templates_dir: Path = DEFAULT_TEMPLATES_DIR) -> None:
        self._templates_dir = Path(templates_dir)
        self._envs: dict[str, Environment] = {}

    def write(self, plan: TestPlan) -> Path:
        """Render the plan to disk. Returns path of the written file."""
        template_name = self._pick_template_name(plan)
        env = self._env(plan.language)
        template = env.get_template(template_name)
        content = template.render(**self._build_context(plan))
        plan.output_path.parent.mkdir(parents=True, exist_ok=True)
        plan.output_path.write_text(content, encoding="utf-8")
        return plan.output_path

    def _env(self, language: str) -> Environment:
        if language not in self._envs:
            lang_dir = self._templates_dir / language
            self._envs[language] = Environment(
                loader=FileSystemLoader(str(lang_dir)),
                undefined=StrictUndefined,
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        return self._envs[language]

    def _pick_template_name(self, plan: TestPlan) -> str:
        templates = {s.template for s in plan.scenarios}
        if "api" in templates:
            primary = "api"
        elif "database" in templates:
            primary = "database"
        else:
            primary = "unit"
        ext = "py" if plan.language == "python" else "ts"
        return f"{primary}.{ext}.j2"

    def _build_context(self, plan: TestPlan) -> dict:
        source_path = str(plan.module_path) if plan.module_path else ""
        module_name = plan.module_path.stem if plan.module_path else "generated"
        module_import = self._compute_module_import(plan.module_path)
        source_ref = plan.scenarios[0].source if plan.scenarios else "unknown"
        tdd_mode = any(s.tdd_pending for s in plan.scenarios)

        if source_ref.startswith("spec:"):
            sid = source_ref[5:]
            regen_cmd = f"orchestrator test generate --from-spec {sid}"
        else:
            regen_cmd = f"orchestrator test generate --from-code {source_path}"

        return {
            "module_name": module_name,
            "module_import": module_import,
            "source_path": source_path,
            "source_ref": source_ref,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "functions": [],
            "scenarios": plan.scenarios,
            "fixtures_needed": plan.fixtures_needed,
            "tdd_mode": tdd_mode,
            "regen_cmd": regen_cmd,
        }

    def _compute_module_import(self, path: Optional[Path]) -> str:
        if path is None:
            return ""
        try:
            rel = path.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            # Path is outside cwd (e.g. tmp_path in tests); fall back to filename only.
            rel = Path(path.stem)
        return str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
