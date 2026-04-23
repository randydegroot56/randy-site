"""Blueprint resolver — selects a project blueprint from a SpecDoc."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BLUEPRINTS_DIR = Path(__file__).parent / "blueprints"

_FALLBACK = "python-library"

_SELECTION: list[tuple[str, frozenset[str], str]] = [
    ("python",     frozenset({"api", "fullstack"}), "fastapi-service"),
    ("python",     frozenset({"cli"}),              "python-cli"),
    ("python",     frozenset({"library"}),          "python-library"),
    ("typescript", frozenset({"api"}),              "express-api"),
    ("typescript", frozenset({"frontend"}),         "nextjs-app"),
]


@dataclass
class BlueprintFile:
    path: str        # may contain Jinja2 {{ var }} expressions
    template: str    # relative path to .jinja2 file within blueprints_dir
    header: bool     # whether FileGenerator should prepend the generated-by comment


@dataclass
class Blueprint:
    name: str
    version: str
    description: str
    language: str
    files: list[BlueprintFile]
    required_spec_fields: list[str]
    optional_spec_fields: list[str]
    blueprints_dir: Path


class BlueprintResolver:
    """Selects a Blueprint based on spec.project.language and spec.project.type."""

    def __init__(self, blueprints_dir: Path = DEFAULT_BLUEPRINTS_DIR) -> None:
        self._dir = blueprints_dir

    def resolve(self, spec) -> tuple[Blueprint, list[str]]:
        """Return (blueprint, warnings). Always returns a Blueprint; never raises."""
        warnings: list[str] = []
        lang = (spec.project.language or "").lower()
        ptype = (spec.project.type or "").lower()

        blueprint_name = _FALLBACK
        matched = False

        for row_lang, row_types, row_name in _SELECTION:
            if lang == row_lang and ptype in row_types:
                blueprint_name = row_name
                matched = True
                break

        if not matched:
            if lang in ("todo", ""):
                warnings.append(
                    f"spec.project.language is '{spec.project.language}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )
            elif ptype in ("todo", ""):
                warnings.append(
                    f"spec.project.type is '{spec.project.type}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )
            else:
                warnings.append(
                    f"No blueprint for language='{lang}' type='{ptype}'; "
                    f"using conservative fallback '{_FALLBACK}'"
                )

        return self._load(blueprint_name), warnings

    def _load(self, name: str) -> Blueprint:
        path = self._dir / name / "blueprint.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        files = [
            BlueprintFile(
                path=f["path"],
                template=f["template"],
                header=f.get("header", True),
            )
            for f in data["files"]
        ]
        return Blueprint(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            language=data["language"],
            files=files,
            required_spec_fields=data.get("required_spec_fields", []),
            optional_spec_fields=data.get("optional_spec_fields", []),
            blueprints_dir=self._dir / name,
        )
