"""Find OPENMINION_* environment variables that docs mention but the package never reads.

For each such variable we also record, deterministically, where the source
checkout does use it (tests/, scripts/, .github/ ...), including names built from
a prefix constant such as ``APPROVAL_PREFIX = "OPENMINION_..._APPROVED_"``.
That fact is what decides "repo-only setting" vs "drift", so the model is
handed it instead of being asked to find it.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import openminion

ENV_NAME = re.compile(r"\bOPENMINION_[A-Z0-9_]*[A-Z0-9]\b")
ENV_LITERAL = re.compile(r"""["'](OPENMINION_[A-Z0-9_]+)["']""")
CODE_GLOBS = ("*.py", "*.sh", "*.yml", "*.yaml", "*.toml", "Makefile", "*.mk")


@lru_cache(maxsize=1)
def package_text() -> str:
    root = Path(openminion.__file__).parent
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in root.rglob("*.py"))


@dataclass
class EnvUsage:
    name: str
    used_in: list[str] = field(default_factory=list)  # top-level dirs, e.g. ["tests", ".github"]
    via_prefix: str = ""  # "file:line" of a prefix constant that builds this name


@lru_cache(maxsize=4)
def _checkout_index(root: Path) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    """Map exact env names -> top-level dirs, plus (prefix, location) constants."""

    exact: dict[str, set[str]] = defaultdict(set)
    prefixes: list[tuple[str, str]] = []
    for glob in CODE_GLOBS:
        for path in root.rglob(glob):
            rel = path.relative_to(root)
            if rel.parts[0] in {".git", "docs"} or "__pycache__" in rel.parts:
                continue
            top = rel.parts[0] if len(rel.parts) > 1 else "."
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name in ENV_NAME.findall(text):
                exact[name].add(top)
            for no, line in enumerate(text.splitlines(), 1):
                for literal in ENV_LITERAL.findall(line):
                    if literal.endswith("_"):
                        prefixes.append((literal, f"{rel.as_posix()}:{no}"))
    return dict(exact), prefixes


def usage_in_checkout(root: Path, name: str) -> EnvUsage:
    exact, prefixes = _checkout_index(root.resolve())
    usage = EnvUsage(name=name, used_in=sorted(exact.get(name, set())))
    if usage.used_in:
        return usage  # exact use found; a prefix match would only add noise
    for prefix, where in prefixes:
        # Short shared prefixes such as "OPENMINION_TEST_" match too much.
        if prefix.count("_") >= 4 and name.startswith(prefix) and name != prefix:
            usage.via_prefix = where
            top = where.split("/", 1)[0]
            if top not in usage.used_in:
                usage.used_in.append(top)
            break
    return usage


def unknown_env_vars(root: Path, doc_paths: list[Path]) -> dict[str, list[EnvUsage]]:
    """Map doc path -> usages of env vars that appear nowhere in the installed package."""

    source = package_text()
    out: dict[str, list[EnvUsage]] = defaultdict(list)
    for path in doc_paths:
        names = sorted(set(ENV_NAME.findall(path.read_text(encoding="utf-8", errors="replace"))))
        for name in names:
            if name not in source:
                out[path.relative_to(root).as_posix()].append(usage_in_checkout(root, name))
    return dict(out)


def summarize(usages: list[EnvUsage]) -> str:
    """One line of deterministic evidence for the triage agent and the report."""

    groups: dict[str, list[str]] = defaultdict(list)
    prefix_notes = set()
    for u in usages:
        key = ", ".join(f"{d}/" for d in u.used_in) if u.used_in else "nowhere in the checkout"
        groups[key].append(u.name)
        if u.via_prefix:
            prefix_notes.add(u.via_prefix)
    parts = [f"{len(v)} used in {k}" for k, v in sorted(groups.items())]
    note = f" (some names are built from a prefix constant at {', '.join(sorted(prefix_notes))})" if prefix_notes else ""
    return "; ".join(parts) + note
