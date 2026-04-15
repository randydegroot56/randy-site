"""
agents/spec_writer/parser.py
=============================
SpecParser — hybrid section-header + keyword heuristic extractor.

parse(text) -> SpecDoc. Never raises. Vague input produces warnings.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from agents.spec_writer.schema import (
    Constraints, ContextApplied, Feature, InputSection,
    ProjectSection, SpecDoc, TechnicalSpec,
)

# ── Compiled patterns ──────────────────────────────────────────────────────────

_SECTION_HEADER = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)
_LIST_ITEM = re.compile(r'^[ \t]*[-*]\s+(.+)$|^[ \t]*\d+\.\s+(.+)$', re.MULTILINE)

_LANGUAGE = re.compile(
    r'\b(python|typescript|javascript|go|rust|java|kotlin|swift|php|ruby)\b',
    re.IGNORECASE,
)
_FRAMEWORK = re.compile(
    r'\b(fastapi|flask|django|next(?:\.js|js)?|express|vue|svelte|laravel|rails|spring|gin|fiber)\b',
    re.IGNORECASE,
)
_PROJECT_TYPES: List[Tuple[str, re.Pattern]] = [
    ("fullstack", re.compile(r'\b(fullstack|full.stack|full stack)\b', re.IGNORECASE)),
    ("api",       re.compile(r'\b(api|rest(?:ful)?|graphql|grpc)\b', re.IGNORECASE)),
    ("cli",       re.compile(r'\b(cli|command.line|terminal)\b', re.IGNORECASE)),
    ("frontend",  re.compile(r'\b(frontend|front.end|webapp|web app)\b', re.IGNORECASE)),
    ("library",   re.compile(r'\b(library|lib|package|module|sdk)\b', re.IGNORECASE)),
]
_PRIORITY_MUST  = re.compile(r'\bmust\b', re.IGNORECASE)
_PRIORITY_COULD = re.compile(r'\b(could|nice.to.have)\b', re.IGNORECASE)
_SECURITY_WORDS = re.compile(
    r'\b(security|auth(?:en)?|https|ssl|encrypt|jwt|oauth)\b', re.IGNORECASE
)

_H_GOAL         = re.compile(r'(goals?|doel|user stor|purpose)', re.IGNORECASE)
_H_REQUIREMENTS = re.compile(r'(requirements?|eisen?|functioneel|features?)', re.IGNORECASE)
_H_TECH         = re.compile(r'(tech(?:nical)?|stack|dependencies|afhankelijkheden)', re.IGNORECASE)
_H_CONSTRAINTS  = re.compile(r'(constraints?|beperkingen?|non.functional)', re.IGNORECASE)
_H_ACCEPTANCE   = re.compile(r'(acceptance.criteria|acceptatiecriteria)', re.IGNORECASE)


def _list_items(text: str) -> List[str]:
    return [(a or b).strip() for a, b in _LIST_ITEM.findall(text) if (a or b).strip()]


def _feature_priority(text: str) -> str:
    if _PRIORITY_MUST.search(text):
        return "must"
    if _PRIORITY_COULD.search(text):
        return "could"
    return "should"


def _normalise_framework(raw: str) -> str:
    norm = raw.lower()
    return norm.replace("next.js", "next").replace("nextjs", "next")


class SpecParser:
    """Converts free-form text to a SpecDoc. Never raises."""

    def parse(self, text: str) -> SpecDoc:
        spec = SpecDoc(input=InputSection(raw_description=text or ""))

        if not text or not text.strip():
            spec.warnings.append("Input is empty — all fields set to TODO")
            return spec

        sections = self._split_sections(text)
        self._apply_sections(spec, sections)
        self._apply_heuristics(spec, text)
        self._number_features(spec)
        self._add_missing_warnings(spec)
        return spec

    # ── Section extraction ─────────────────────────────────────────────────────

    def _split_sections(self, text: str) -> Dict[str, str]:
        parts: Dict[str, List[str]] = {"_preamble": []}
        current = "_preamble"
        for line in text.splitlines():
            m = _SECTION_HEADER.match(line)
            if m:
                current = m.group(1).strip()
                parts.setdefault(current, [])
            else:
                parts.setdefault(current, []).append(line)
        return {k: "\n".join(v) for k, v in parts.items()}

    def _apply_sections(self, spec: SpecDoc, sections: Dict[str, str]) -> None:
        acceptance_buffer: List[str] = []
        for header, body in sections.items():
            if header == "_preamble":
                continue
            if _H_GOAL.search(header):
                items = _list_items(body)
                if items:
                    for item in items:
                        spec.features.append(Feature(
                            name=item[:60],
                            description=item,
                            priority=_feature_priority(item),
                        ))
                elif body.strip():
                    spec.project.name = body.strip().splitlines()[0][:80]
            elif _H_REQUIREMENTS.search(header):
                for item in _list_items(body):
                    spec.features.append(Feature(
                        name=item[:60],
                        description=item,
                        priority=_feature_priority(item),
                    ))
            elif _H_TECH.search(header):
                for item in _list_items(body):
                    m_lang = _LANGUAGE.search(item)
                    m_fw = _FRAMEWORK.search(item)
                    if m_lang and spec.project.language == "TODO":
                        spec.project.language = m_lang.group(1).lower()
                    elif m_fw and spec.project.framework == "TODO":
                        spec.project.framework = _normalise_framework(m_fw.group(1))
                    else:
                        spec.technical.dependencies.append(item)
                if body.strip():
                    spec.technical.architecture_notes = body.strip()[:500]
            elif _H_CONSTRAINTS.search(header):
                for item in _list_items(body):
                    if _SECURITY_WORDS.search(item):
                        spec.constraints.security.append(item)
                    else:
                        spec.constraints.performance.append(item)
            elif _H_ACCEPTANCE.search(header):
                acceptance_buffer.extend(_list_items(body))

        if acceptance_buffer and spec.features:
            spec.features[-1].acceptance_criteria = acceptance_buffer

    # ── Keyword heuristics ─────────────────────────────────────────────────────

    def _apply_heuristics(self, spec: SpecDoc, text: str) -> None:
        if spec.project.language == "TODO":
            m = _LANGUAGE.search(text)
            if m:
                spec.project.language = m.group(1).lower()

        if spec.project.framework == "TODO":
            m = _FRAMEWORK.search(text)
            if m:
                spec.project.framework = _normalise_framework(m.group(1))

        if spec.project.type == "TODO":
            for ptype, pattern in _PROJECT_TYPES:
                if pattern.search(text):
                    spec.project.type = ptype
                    break

        if not spec.features:
            for item in _list_items(text):
                spec.features.append(Feature(
                    name=item[:60],
                    description=item,
                    priority=_feature_priority(item),
                ))

        if not spec.features and text.strip():
            spec.features.append(Feature(
                name=text.strip()[:60],
                description=text.strip()[:200],
            ))
            spec.warnings.append(
                "No structured features found — entire input used as single feature description"
            )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _number_features(self, spec: SpecDoc) -> None:
        for i, feature in enumerate(spec.features, start=1):
            feature.id = f"F{i:03d}"

    def _add_missing_warnings(self, spec: SpecDoc) -> None:
        if spec.project.name == "TODO":
            spec.warnings.append("project.name could not be determined — set manually")
        if spec.project.language == "TODO":
            spec.warnings.append("project.language could not be determined — set manually")
        if spec.project.type == "TODO":
            spec.warnings.append("project.type could not be determined — set manually")
        if not spec.features:
            spec.warnings.append("No features extracted — add feature descriptions to input")
