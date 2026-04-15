"""Tests for agents.test_generator.analyzer.CodeAnalyzer."""
import pytest
from pathlib import Path
from agents.test_generator.analyzer import CodeAnalyzer, FunctionInfo, AnalyzedModule


@pytest.fixture
def analyzer():
    return CodeAnalyzer()


# ── Python parsing ──────────────────────────────────────────────────────────

def test_analyze_python_top_level_function(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text("def greet(name, greeting='Hello'):\n    return f'{greeting}, {name}'\n")
    module = analyzer.analyze(src)
    assert module.language == "python"
    assert len(module.functions) == 1
    fn = module.functions[0]
    assert fn.name == "greet"
    assert fn.params == ["name", "greeting"]
    assert fn.is_async is False
    assert fn.is_method is False
    assert fn.class_name is None


def test_analyze_python_async_function(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text("async def fetch(url):\n    pass\n")
    module = analyzer.analyze(src)
    assert module.functions[0].is_async is True


def test_analyze_python_class_method(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text(
        "class MyService:\n"
        "    def create(self, name):\n"
        "        pass\n"
        "    def delete(self, id):\n"
        "        pass\n"
    )
    module = analyzer.analyze(src)
    assert "MyService" in module.classes
    methods = [f for f in module.functions if f.is_method]
    assert len(methods) == 2
    assert methods[0].class_name == "MyService"
    assert "self" not in methods[0].params


def test_analyze_python_raises_detection(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text(
        "def divide(a, b):\n"
        "    if b == 0:\n"
        "        raise ValueError('zero')\n"
        "    return a / b\n"
    )
    module = analyzer.analyze(src)
    assert "ValueError" in module.functions[0].raises


def test_analyze_python_imports(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text("import os\nfrom pathlib import Path\ndef f(): pass\n")
    module = analyzer.analyze(src)
    assert "os" in module.imports
    assert "pathlib" in module.imports


def test_analyze_python_syntax_error(tmp_path, analyzer):
    src = tmp_path / "bad.py"
    src.write_text("def broken(\n")
    with pytest.raises(ValueError, match="syntax error"):
        analyzer.analyze(src)


def test_analyze_missing_file_raises(tmp_path, analyzer):
    with pytest.raises(FileNotFoundError):
        analyzer.analyze(tmp_path / "nonexistent.py")


def test_analyze_unsupported_extension(tmp_path, analyzer):
    src = tmp_path / "foo.rb"
    src.write_text("puts 'hello'\n")
    with pytest.raises(ValueError, match="Unsupported file type"):
        analyzer.analyze(src)


def test_has_tests_false_when_no_test_file(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text("def f(): pass\n")
    module = analyzer.analyze(src)
    assert module.has_tests is False


def test_has_tests_true_when_test_file_exists(tmp_path, analyzer):
    src = tmp_path / "foo.py"
    src.write_text("def f(): pass\n")
    (tmp_path / "test_foo.py").write_text("def test_f(): pass\n")
    module = analyzer.analyze(src)
    assert module.has_tests is True


# ── TypeScript parsing ──────────────────────────────────────────────────────

def test_analyze_typescript_named_function(tmp_path, analyzer):
    src = tmp_path / "foo.ts"
    src.write_text("export function greet(name: string): string {\n  return name;\n}\n")
    module = analyzer.analyze(src)
    assert module.language == "typescript"
    names = [f.name for f in module.functions]
    assert "greet" in names


def test_analyze_typescript_arrow_function(tmp_path, analyzer):
    src = tmp_path / "foo.ts"
    src.write_text("export const double = (n: number): number => n * 2;\n")
    module = analyzer.analyze(src)
    names = [f.name for f in module.functions]
    assert "double" in names


def test_analyze_typescript_async_function(tmp_path, analyzer):
    src = tmp_path / "foo.ts"
    src.write_text("export async function fetchData(url: string) {\n  return fetch(url);\n}\n")
    module = analyzer.analyze(src)
    fn = next(f for f in module.functions if f.name == "fetchData")
    assert fn.is_async is True


def test_parse_ts_params_strips_types(analyzer):
    params = analyzer._parse_ts_params("name: string, age: number, active: boolean")
    assert params == ["name", "age", "active"]


def test_parse_ts_params_empty(analyzer):
    assert analyzer._parse_ts_params("") == []


def test_parse_ts_params_with_default_values(analyzer):
    params = analyzer._parse_ts_params("x: number = 0, y: string = 'hi'")
    assert params == ["x", "y"]


def test_parse_ts_params_rest_param(analyzer):
    params = analyzer._parse_ts_params("...args: string[]")
    # rest params with '...' prefix are accepted as-is
    assert params == ["...args"]
