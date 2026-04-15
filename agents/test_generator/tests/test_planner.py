"""Tests for agents.test_generator.planner.TestPlanner."""
import pytest
from pathlib import Path
from agents.test_generator.analyzer import AnalyzedModule, FunctionInfo
from agents.test_generator.planner import TestPlanner, TestPlan, TestScenario


def make_module(tmp_path, functions=None, language="python"):
    src = tmp_path / "foo.py"
    src.write_text("")
    return AnalyzedModule(
        path=src,
        language=language,
        functions=functions or [],
        classes=[],
        imports=[],
        has_tests=False,
    )


def make_fn(name="greet", params=None, raises=None):
    return FunctionInfo(
        name=name,
        params=["name"] if params is None else params,
        is_async=False,
        is_method=False,
        class_name=None,
        return_hint="str",
        raises=raises or [],
        line=1,
    )


@pytest.fixture
def planner():
    return TestPlanner()


# ── from code ───────────────────────────────────────────────────────────────

def test_plan_from_code_produces_happy_path(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("greet")])
    plan = planner.plan(module=module)
    names = [s.name for s in plan.scenarios]
    assert any("happy_path" in n for n in names)


def test_plan_from_code_produces_edge_case_when_params(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("greet", params=["name"])])
    plan = planner.plan(module=module)
    types = [s.scenario_type for s in plan.scenarios]
    assert "edge_case" in types


def test_plan_from_code_no_edge_case_when_no_params(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("ping", params=[])])
    plan = planner.plan(module=module)
    types = [s.scenario_type for s in plan.scenarios]
    assert "edge_case" not in types


def test_plan_from_code_error_scenario_per_exception(tmp_path, planner):
    fn = make_fn("divide", params=["a", "b"], raises=["ValueError", "ZeroDivisionError"])
    module = make_module(tmp_path, [fn])
    plan = planner.plan(module=module)
    error_scenarios = [s for s in plan.scenarios if s.scenario_type == "error"]
    assert len(error_scenarios) == 2


def test_plan_skips_private_functions(tmp_path, planner):
    fns = [make_fn("_helper"), make_fn("public_fn")]
    module = make_module(tmp_path, fns)
    plan = planner.plan(module=module)
    names = [s.target_function for s in plan.scenarios]
    assert "_helper" not in names
    assert "public_fn" in names


def test_plan_tdd_pending_false_from_code(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("greet")])
    plan = planner.plan(module=module)
    assert all(not s.tdd_pending for s in plan.scenarios)


def test_plan_estimated_coverage_capped_at_90(tmp_path, planner):
    fns = [make_fn(f"fn_{i}") for i in range(3)]
    module = make_module(tmp_path, fns)
    plan = planner.plan(module=module)
    assert plan.estimated_coverage <= 90


def test_plan_output_path_python(tmp_path, planner):
    module = make_module(tmp_path, [make_fn()])
    plan = planner.plan(module=module)
    assert plan.output_path.name == "test_foo.py"
    assert "tests" in plan.output_path.parts


def test_plan_output_path_typescript(tmp_path, planner):
    src = tmp_path / "bar.ts"
    src.write_text("")
    module = AnalyzedModule(path=src, language="typescript", functions=[make_fn()],
                            classes=[], imports=[], has_tests=False)
    plan = planner.plan(module=module)
    assert plan.output_path.name == "bar.test.ts"


def test_plan_requires_at_least_one_input(planner):
    with pytest.raises(ValueError, match="At least one"):
        planner.plan()


# ── from spec ───────────────────────────────────────────────────────────────

def test_plan_from_spec_tdd_pending_true(planner):
    """All spec-derived scenarios are TDD pending."""
    from unittest.mock import MagicMock
    spec = MagicMock()
    spec.spec_id = "spec_20260415_001"
    feature = MagicMock()
    feature.name = "create user"
    feature.description = "Creates a new user account"
    feature.id = "F1"
    feature.acceptance_criteria = ["User is saved to database", "Returns user id"]
    spec.features = [feature]
    plan = planner.plan(spec=spec, spec_id="spec_20260415_001")
    assert all(s.tdd_pending for s in plan.scenarios)
    assert len(plan.scenarios) == 2


def test_plan_from_spec_output_path_uses_spec_id(planner):
    from unittest.mock import MagicMock
    spec = MagicMock()
    spec.spec_id = "spec_20260415_001"
    spec.features = []
    plan = planner.plan(spec=spec, spec_id="spec_20260415_001")
    assert "spec_20260415_001" in str(plan.output_path)


def test_plan_api_template_detection(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("get_user_endpoint")])
    plan = planner.plan(module=module)
    assert any(s.template == "api" for s in plan.scenarios)


def test_plan_database_template_detection(tmp_path, planner):
    module = make_module(tmp_path, [make_fn("save_to_database")])
    plan = planner.plan(module=module)
    assert any(s.template == "database" for s in plan.scenarios)
