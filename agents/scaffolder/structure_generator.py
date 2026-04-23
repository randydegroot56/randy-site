"""StructureGenerator — renders Jinja2 templates into RenderedFile objects."""
from __future__ import annotations

import re
from dataclasses import dataclass

from jinja2 import Environment, FileSystemLoader

from agents.scaffolder.blueprint_resolver import Blueprint


@dataclass
class RenderedFile:
    relative_path: str
    content: str
    header: bool


def _derive_name_variants(name: str) -> dict[str, str]:
    """Return snake_case, PascalCase, and kebab-case variants of a project name."""
    clean = (name or "project").strip()
    # First, insert underscores before uppercase letters (for camelCase handling)
    with_underscores = re.sub(r"([a-z])([A-Z])", r"\1_\2", clean)
    # Then normalize to snake_case: lowercase, replace non-alphanumeric with underscore
    snake = re.sub(r"[^a-z0-9]+", "_", with_underscores.lower()).strip("_") or "project"
    pascal = "".join(w.capitalize() for w in re.split(r"[^a-zA-Z0-9]+", clean) if w)
    kebab = re.sub(r"[^a-z0-9]+", "-", with_underscores.lower()).strip("-") or "project"
    return {
        "project_name_snake": snake,
        "project_name_pascal": pascal,
        "project_name_kebab": kebab,
    }


class StructureGenerator:
    """Renders a Blueprint's Jinja2 templates into a list of RenderedFile objects."""

    def generate(self, blueprint: Blueprint, context: dict) -> list[RenderedFile]:
        """Render all blueprint templates. Returns RenderedFile list; never raises on missing optional fields."""
        env = Environment(
            loader=FileSystemLoader(str(blueprint.blueprints_dir / "templates")),
            keep_trailing_newline=True,
        )
        path_env = Environment()  # separate env for expanding path strings

        files: list[RenderedFile] = []
        for bf in blueprint.files:
            rendered_path = path_env.from_string(bf.path).render(context)
            tpl_name = bf.template.split("/")[-1]
            template = env.get_template(tpl_name)
            content = template.render(context)
            files.append(RenderedFile(
                relative_path=rendered_path,
                content=content,
                header=bf.header,
            ))
        return files
