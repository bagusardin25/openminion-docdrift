"""Check Python snippets against the installed `openminion` package.

Static only: snippets are parsed, never executed. The checker resolves
`openminion` imports, then checks attribute access and keyword arguments on the
objects those imports bind, including instances created with `x = Cls(...)` or
`with Cls(...) as x`.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any

from .extract import Snippet


@dataclass
class PyCandidate:
    snippet_id: str
    path: str
    line: int
    code_line: str
    kind: str  # syntax_error | missing_module | missing_name | missing_attribute | unknown_kwarg
    detail: str
    suggestions: list[str]


def _public(obj: Any) -> list[str]:
    return [n for n in dir(obj) if not n.startswith("_")]


def _resolve_from(module: str, name: str) -> tuple[bool, Any]:
    mod = importlib.import_module(module)
    if hasattr(mod, name):
        return True, getattr(mod, name)
    try:
        return True, importlib.import_module(f"{module}.{name}")
    except ImportError:
        return False, mod


def _accepts_kwarg(func: Any, name: str) -> tuple[bool, list[str]]:
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return True, []
    params = sig.parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True, []
    accepted = [
        n
        for n, p in params.items()
        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY) and n != "self"
    ]
    return name in accepted, accepted


class _Visitor(ast.NodeVisitor):
    def __init__(self, snippet: Snippet, lines: list[str]):
        self.snippet = snippet
        self.lines = lines
        self.bound: dict[str, Any] = {}  # local name -> imported openminion object
        self.instances: dict[str, type] = {}  # local name -> class it was built from
        self.found: list[PyCandidate] = []

    # --- helpers -------------------------------------------------------
    def _add(self, node: ast.AST, kind: str, detail: str, suggestions: list[str] | None = None) -> None:
        lineno = getattr(node, "lineno", 1)
        code_line = self.lines[lineno - 1].strip() if 0 < lineno <= len(self.lines) else ""
        self.found.append(
            PyCandidate(
                snippet_id=self.snippet.id,
                path=self.snippet.path,
                line=self.snippet.line + lineno - 1,
                code_line=code_line,
                kind=kind,
                detail=detail,
                suggestions=suggestions or [],
            )
        )

    def _object_for(self, node: ast.expr) -> Any | None:
        if isinstance(node, ast.Name):
            return self.bound.get(node.id)
        if isinstance(node, ast.Attribute):
            base = self._object_for(node.value)
            if base is not None and inspect.ismodule(base):
                return getattr(base, node.attr, None)
        return None

    def _track_instance(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, ast.Name) and isinstance(value, ast.Call):
            cls = self._object_for(value.func)
            if inspect.isclass(cls):
                self.instances[target.id] = cls

    # --- imports -------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] != "openminion":
                continue
            try:
                mod = importlib.import_module(alias.name)
            except ImportError as exc:
                self._add(node, "missing_module", f"`import {alias.name}` fails: {exc}")
                continue
            if alias.asname:
                self.bound[alias.asname] = mod
            else:
                self.bound["openminion"] = importlib.import_module("openminion")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module.split(".")[0] != "openminion" or node.level:
            return
        try:
            mod = importlib.import_module(module)
        except ImportError as exc:
            parent = module.rsplit(".", 1)[0]
            siblings: list[str] = []
            try:
                siblings = _public(importlib.import_module(parent))
            except ImportError:
                pass
            self._add(
                node,
                "missing_module",
                f"`from {module} import ...` fails: {exc}",
                get_close_matches(module.rsplit(".", 1)[-1], siblings, n=3),
            )
            return
        for alias in node.names:
            if alias.name == "*":
                continue
            ok, obj = _resolve_from(module, alias.name)
            if not ok:
                self._add(
                    node,
                    "missing_name",
                    f"`{module}` has no `{alias.name}`",
                    get_close_matches(alias.name, _public(mod), n=3),
                )
                continue
            self.bound[alias.asname or alias.name] = obj

    # --- usage ---------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._track_instance(target, node.value)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._track_instance(item.optional_vars, item.context_expr)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            name = node.value.id
            owner = self.instances.get(name) or self.bound.get(name)
            if owner is not None and (inspect.isclass(owner) or inspect.ismodule(owner)):
                if not hasattr(owner, node.attr) and not self._is_instance_field(owner, node.attr):
                    label = owner.__name__
                    self._add(
                        node,
                        "missing_attribute",
                        f"`{label}` has no attribute `{node.attr}`",
                        get_close_matches(node.attr, _public(owner), n=3),
                    )
        self.generic_visit(node)

    @staticmethod
    def _is_instance_field(cls: Any, attr: str) -> bool:
        """Dataclass/pydantic fields and __init__-assigned attributes are not on the class."""

        for source in ("__dataclass_fields__", "model_fields", "__annotations__"):
            if attr in (getattr(cls, source, None) or {}):
                return True
        try:
            init_src = inspect.getsource(cls.__init__)
        except (OSError, TypeError):
            return True  # cannot tell, so do not report
        return f"self.{attr}" in init_src

    def visit_Call(self, node: ast.Call) -> None:
        func_obj: Any | None = None
        label = ""
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            owner = self.instances.get(node.func.value.id)
            if owner is not None and hasattr(owner, node.func.attr):
                func_obj = getattr(owner, node.func.attr)
                label = f"{owner.__name__}.{node.func.attr}"
        if func_obj is None:
            func_obj = self._object_for(node.func)
            label = getattr(func_obj, "__qualname__", "") or getattr(func_obj, "__name__", "")
        if func_obj is not None and callable(func_obj):
            target = func_obj.__init__ if inspect.isclass(func_obj) else func_obj
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                ok, accepted = _accepts_kwarg(target, kw.arg)
                if not ok:
                    self._add(
                        node,
                        "unknown_kwarg",
                        f"`{label}()` does not accept keyword `{kw.arg}`",
                        get_close_matches(kw.arg, accepted, n=3),
                    )
        self.generic_visit(node)


def check_snippet(snippet: Snippet) -> list[PyCandidate]:
    code = snippet.code
    lines = code.splitlines()
    if "openminion" not in code:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        # Prompts and elided bodies are documentation style, not drift.
        if ">>>" in code:
            return []
        return [
            PyCandidate(
                snippet_id=snippet.id,
                path=snippet.path,
                line=snippet.line + (exc.lineno or 1) - 1,
                code_line=(exc.text or "").strip(),
                kind="syntax_error",
                detail=f"snippet does not parse: {exc.msg}",
                suggestions=[],
            )
        ]
    visitor = _Visitor(snippet, lines)
    visitor.visit(tree)
    return visitor.found
