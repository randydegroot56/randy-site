"""
agents/test_generator/analyzer.py
====================================
CodeAnalyzer — extracts function signatures from Python and TypeScript/JavaScript.

Python:  ast.parse() — reliable, zero extra dependencies.
TypeScript/JS: regex patterns — best-effort; ambiguous signatures get '...args'.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FunctionInfo:
    """Signature of a single function or method."""
    name: str
    params: List[str]
    is_async: bool
    is_method: bool
    class_name: Optional[str]
    return_hint: str
    raises: List[str]
    line: int


@dataclass
class AnalyzedModule:
    """All extracted metadata for one source file."""
    path: Path
    language: str                          # "python" | "typescript"
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    has_tests: bool = False


EXTENSION_MAP: Dict[str, str] = {
    ".py":  "python",
    ".ts":  "typescript",
    ".tsx": "typescript",
    ".js":  "typescript",
    ".jsx": "typescript",
}


class CodeAnalyzer:
    """Extracts function signatures from Python and TypeScript/JavaScript source files."""

    def analyze(self, path: Path) -> AnalyzedModule:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        language = EXTENSION_MAP.get(path.suffix.lower())
        if language is None:
            raise ValueError(
                f"Unsupported file type '{path.suffix}'. Supported: {sorted(EXTENSION_MAP)}"
            )
        return self._analyze_python(path) if language == "python" else self._analyze_typescript(path)

    # ── Python ──────────────────────────────────────────────────────────────

    def _analyze_python(self, path: Path) -> AnalyzedModule:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ValueError(f"Python syntax error in {path}: {exc}") from exc

        functions: List[FunctionInfo] = []
        classes: List[str] = []
        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module.split(".")[0])

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._make_py_function(node, is_method=False, class_name=None))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(self._make_py_function(child, is_method=True, class_name=node.name))

        return AnalyzedModule(
            path=path,
            language="python",
            functions=functions,
            classes=classes,
            imports=list(dict.fromkeys(imports)),
            has_tests=self._has_tests(path, "python"),
        )

    def _make_py_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_method: bool,
        class_name: Optional[str],
    ) -> FunctionInfo:
        params = [arg.arg for arg in node.args.args]
        if is_method and params and params[0] in ("self", "cls"):
            params = params[1:]

        return_hint = "unknown"
        if node.returns:
            try:
                return_hint = ast.unparse(node.returns)
            except Exception:
                pass

        raises: List[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                exc = child.exc
                if isinstance(exc, ast.Call):
                    func = exc.func
                    name = (
                        func.id if isinstance(func, ast.Name)
                        else func.attr if isinstance(func, ast.Attribute)
                        else None
                    )
                elif isinstance(exc, ast.Name):
                    name = exc.id
                else:
                    name = None
                if name and name not in raises:
                    raises.append(name)

        return FunctionInfo(
            name=node.name,
            params=params,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            class_name=class_name,
            return_hint=return_hint,
            raises=raises,
            line=node.lineno,
        )

    # ── TypeScript / JavaScript (regex, best-effort) ─────────────────────────

    _FN_NAMED = re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
        re.MULTILINE,
    )
    _FN_ARROW = re.compile(
        r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)"
        r"\s*(?::\s*[\w<>\[\],\s|]+)?\s*=>",
        re.MULTILINE,
    )
    _FN_METHOD = re.compile(
        r"^\s{2,}(?:(?:public|private|protected|static|async|override|readonly|abstract)\s+)*"
        r"(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w<>\[\],\s|]+)?\s*\{",
        re.MULTILINE,
    )
    _CLASS = re.compile(r"\bclass\s+(\w+)")
    _IMPORT_STR = re.compile(r"""['"]([@\w][^'"]*?)['"]""")
    _SKIP_NAMES = frozenset({"if", "for", "while", "switch", "catch", "constructor", "return"})

    def _analyze_typescript(self, path: Path) -> AnalyzedModule:
        source = path.read_text(encoding="utf-8")

        class_lines: List[tuple[int, str]] = []
        for m in self._CLASS.finditer(source):
            class_lines.append((source[: m.start()].count("\n") + 1, m.group(1)))

        imports: List[str] = []
        for line in source.splitlines():
            if line.strip().startswith("import"):
                for m in self._IMPORT_STR.finditer(line):
                    mod = m.group(1).lstrip("./").split("/")[0]
                    if mod:
                        imports.append(mod)

        functions: List[FunctionInfo] = []
        seen: set[tuple[str, int]] = set()

        for pattern, method_hint in [
            (self._FN_NAMED, False),
            (self._FN_ARROW, False),
            (self._FN_METHOD, True),
        ]:
            for m in pattern.finditer(source):
                name = m.group(1)
                if name in self._SKIP_NAMES:
                    continue
                line = source[: m.start()].count("\n") + 1
                if (name, line) in seen:
                    continue
                seen.add((name, line))

                params = self._parse_ts_params(m.group(2))
                window = source[max(0, m.start() - 5): m.end()]
                is_async = bool(re.search(r"\basync\b", window))

                is_method, class_name = False, None
                if method_hint:
                    for cls_line, cls_name in reversed(class_lines):
                        if cls_line < line:
                            is_method, class_name = True, cls_name
                            break

                functions.append(FunctionInfo(
                    name=name,
                    params=params,
                    is_async=is_async,
                    is_method=is_method,
                    class_name=class_name,
                    return_hint="unknown",
                    raises=[],
                    line=line,
                ))

        functions.sort(key=lambda f: f.line)
        return AnalyzedModule(
            path=path,
            language="typescript",
            functions=functions,
            classes=[c for _, c in class_lines],
            imports=list(dict.fromkeys(imports)),
            has_tests=self._has_tests(path, "typescript"),
        )

    def _parse_ts_params(self, raw: str) -> List[str]:
        if not raw.strip():
            return []
        params: List[str] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            name = part.split(":")[0].strip().split("=")[0].strip()
            if name:
                params.append(name)
        return params or ["...args"]

    def _has_tests(self, path: Path, language: str) -> bool:
        if language == "python":
            return (
                (path.parent / f"test_{path.name}").exists()
                or (path.parent / "tests" / f"test_{path.name}").exists()
            )
        stem = path.stem
        return (
            (path.parent / f"{stem}.test{path.suffix}").exists()
            or (path.parent / f"{stem}.spec{path.suffix}").exists()
        )
