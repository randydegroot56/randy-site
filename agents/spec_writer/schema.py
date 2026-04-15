"""
agents/spec_writer/schema.py
============================
Pydantic v2 models for the SpecDoc format.

All fields are Optional or have defaults so partial specs are valid.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class InputSection(BaseModel):
    raw_description: str = ""


class Feature(BaseModel):
    id: str = ""
    name: str = "TODO"
    description: str = "TODO"
    acceptance_criteria: List[str] = Field(default_factory=list)
    priority: Literal["must", "should", "could"] = "should"
    estimated_complexity: Literal["low", "medium", "high"] = "medium"


class ProjectSection(BaseModel):
    name: str = "TODO"
    type: str = "TODO"  # api|frontend|cli|library|fullstack|TODO
    language: str = "TODO"
    framework: str = "TODO"


class TechnicalSpec(BaseModel):
    dependencies: List[str] = Field(default_factory=list)
    architecture_notes: str = ""
    database_schema: Dict[str, Any] = Field(default_factory=dict)
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    file_structure: Dict[str, Any] = Field(default_factory=dict)


class Constraints(BaseModel):
    performance: List[str] = Field(default_factory=list)
    security: List[str] = Field(default_factory=list)
    compatibility: List[str] = Field(default_factory=list)


class ContextApplied(BaseModel):
    patterns_used: List[str] = Field(default_factory=list)
    decisions_referenced: List[str] = Field(default_factory=list)


class SpecDoc(BaseModel):
    spec_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: Literal["draft", "validated", "failed"] = "draft"
    input: InputSection = Field(default_factory=InputSection)
    project: ProjectSection = Field(default_factory=ProjectSection)
    features: List[Feature] = Field(default_factory=list)
    technical: TechnicalSpec = Field(default_factory=TechnicalSpec)
    constraints: Constraints = Field(default_factory=Constraints)
    context_applied: ContextApplied = Field(default_factory=ContextApplied)
    warnings: List[str] = Field(default_factory=list)
