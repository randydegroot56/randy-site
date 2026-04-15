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
