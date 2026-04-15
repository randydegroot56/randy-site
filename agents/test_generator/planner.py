"""
agents/test_generator/planner.py
===================================
TestPlanner — maps a SpecDoc and/or AnalyzedModule to a list of test scenarios.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from agents.test_generator.analyzer import AnalyzedModule


@dataclass
class TestScenario:
    """A single test case to be generated."""
    name: str                    # Python-safe function name
    description: str
    target_function: str
    scenario_type: str           # "happy_path" | "edge_case" | "error" | "boundary"
    template: str                # "unit" | "api" | "database"
    source: str                  # "spec:<feature_id>" | "code:<function_name>"
    tdd_pending: bool


@dataclass
class TestPlan:
    """Complete plan for generating one test file."""
    module_path: Optional[Path]
    output_path: Path
    language: str
    scenarios: List[TestScenario] = field(default_factory=list)
    estimated_coverage: int = 0
    fixtures_needed: bool = False


_API_RE = re.compile(
    r"(?:^|_)(api|endpoint|route|handler|request|response|http|get|post|put|delete|patch)(?:_|\s|$)", re.I
)
_DB_RE = re.compile(
    r"(?:^|_)(db|database|crud|repository|repo|model|query|sql|table|record|persist|store)(?:_|\s|$)", re.I
)


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s]", "", text.lower())
    text = re.sub(r"\s+", "_", text.strip())
    return re.sub(r"_+", "_", text)[:60]


def _pick_template(name: str, description: str = "") -> str:
    combined = f"{name} {description}"
    if _API_RE.search(combined):
        return "api"
    if _DB_RE.search(combined):
        return "database"
    return "unit"


class TestPlanner:
    """Produces a TestPlan from a SpecDoc, AnalyzedModule, or both."""

    def plan(
        self,
        module: Optional[AnalyzedModule] = None,
        spec=None,
        spec_id: str = "",
    ) -> TestPlan:
        if module is None and spec is None:
            raise ValueError("At least one of 'module' or 'spec' must be provided")

        language = module.language if module else "python"
        sid = spec_id or (spec.spec_id if spec else "")
        output_path = self._output_path(module, sid)
        scenarios: List[TestScenario] = []

        if spec:
            scenarios.extend(self._plan_from_spec(spec))
        if module:
            scenarios.extend(self._plan_from_code(module))

        # Deduplicate by name (spec scenarios take priority)
        seen: set[str] = set()
        unique: List[TestScenario] = []
        for s in scenarios:
            if s.name not in seen:
                seen.add(s.name)
                unique.append(s)

        fn_count = (
            len([f for f in module.functions if not f.name.startswith("_")])
            if module else max(len(unique), 1)
        ) or 1  # guard against all-private modules
        coverage = min(90, int((len(unique) / fn_count) * 100)) if fn_count else 0

        return TestPlan(
            module_path=module.path if module else None,
            output_path=output_path,
            language=language,
            scenarios=unique,
            estimated_coverage=coverage,
            fixtures_needed=any(s.template in ("api", "database") for s in unique),
        )

    def _plan_from_spec(self, spec) -> List[TestScenario]:
        scenarios: List[TestScenario] = []
        for feature in spec.features:
            template = _pick_template(feature.name, feature.description)
            criteria = feature.acceptance_criteria or []
            if criteria:
                for i, criterion in enumerate(criteria):
                    slug = _slugify(criterion)
                    name = (
                        f"test_{_slugify(feature.name)}_{slug}"
                        if slug else
                        f"test_{_slugify(feature.name)}_{i + 1:02d}"
                    )
                    scenarios.append(TestScenario(
                        name=name,
                        description=criterion,
                        target_function=_slugify(feature.name),
                        scenario_type="happy_path",
                        template=template,
                        source=f"spec:{feature.id or feature.name}",
                        tdd_pending=True,
                    ))
            else:
                scenarios.append(TestScenario(
                    name=f"test_{_slugify(feature.name)}_happy_path",
                    description=f"{feature.name} — {feature.description}",
                    target_function=_slugify(feature.name),
                    scenario_type="happy_path",
                    template=template,
                    source=f"spec:{feature.id or feature.name}",
                    tdd_pending=True,
                ))
        return scenarios

    def _plan_from_code(self, module: AnalyzedModule) -> List[TestScenario]:
        scenarios: List[TestScenario] = []
        for fn in module.functions:
            if fn.name.startswith("_"):
                continue
            template = _pick_template(fn.name)
            prefix = f"test_{fn.name}"

            scenarios.append(TestScenario(
                name=f"{prefix}_happy_path",
                description=f"Happy path: {fn.name} returns expected result",
                target_function=fn.name,
                scenario_type="happy_path",
                template=template,
                source=f"code:{fn.name}",
                tdd_pending=False,
            ))

            if fn.params:
                scenarios.append(TestScenario(
                    name=f"{prefix}_empty_input",
                    description=f"Edge case: {fn.name} with empty or None input",
                    target_function=fn.name,
                    scenario_type="edge_case",
                    template=template,
                    source=f"code:{fn.name}",
                    tdd_pending=False,
                ))

            for exc_name in fn.raises:
                scenarios.append(TestScenario(
                    name=f"{prefix}_raises_{exc_name.lower()}",
                    description=f"Error: {fn.name} raises {exc_name} on invalid input",
                    target_function=fn.name,
                    scenario_type="error",
                    template=template,
                    source=f"code:{fn.name}",
                    tdd_pending=False,
                ))

        return scenarios

    def _output_path(self, module: Optional[AnalyzedModule], spec_id: str) -> Path:
        if module is None:
            sid = _slugify(spec_id) if spec_id else "generated"
            return Path("tests") / f"test_{sid}.py"
        if module.language == "python":
            return module.path.parent / "tests" / f"test_{module.path.name}"
        return module.path.parent / f"{module.path.stem}.test{module.path.suffix}"
