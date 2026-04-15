"""
agents/spec_writer/validator.py
================================
SpecValidator — pure validation, no side-effects, never raises.

validate(spec) -> SpecDoc with updated warnings and status.
Status is "validated" when warnings is empty, "draft" otherwise.
"""
from __future__ import annotations

from typing import List

from agents.spec_writer.schema import SpecDoc


class SpecValidator:
    """Validates a SpecDoc for completeness and consistency. Never raises."""

    def validate(self, spec: SpecDoc) -> SpecDoc:
        warnings: List[str] = list(spec.warnings)
        self._check_completeness(spec, warnings)
        self._check_consistency(spec, warnings)
        spec.warnings = warnings
        spec.status = "draft" if warnings else "validated"
        return spec

    def _check_completeness(self, spec: SpecDoc, warnings: List[str]) -> None:
        if spec.project.name == "TODO":
            warnings.append("project.name is TODO — set a project name")
        if spec.project.language == "TODO":
            warnings.append("project.language is TODO — specify the programming language")
        if spec.project.type == "TODO":
            warnings.append("project.type is TODO — specify api|frontend|cli|library|fullstack")
        if not spec.features:
            warnings.append("features list is empty — add at least one feature")
        for feature in spec.features:
            if not feature.acceptance_criteria:
                warnings.append(
                    f"Feature '{feature.name}' ({feature.id}) has no acceptance criteria"
                )

    def _check_consistency(self, spec: SpecDoc, warnings: List[str]) -> None:
        if spec.project.type == "api" and not spec.technical.api_endpoints:
            warnings.append(
                "project.type is 'api' but no api_endpoints defined — add endpoint definitions"
            )
        if spec.project.type == "frontend" and spec.project.language == "python":
            warnings.append(
                "project.type is 'frontend' but language is 'python' — "
                "consider typescript/javascript for frontend projects"
            )
        seen_names: set = set()
        for feature in spec.features:
            if feature.name in seen_names:
                warnings.append(f"Duplicate feature name: '{feature.name}'")
            seen_names.add(feature.name)
