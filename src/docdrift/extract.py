"""Pull runnable snippets out of Markdown docs and example files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)")
SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "powershell", "ps1"}
PYTHON_LANGS = {"python", "py", "python3"}

# Docs that describe the repo's own maintainer tooling rather than the
# published package. Commands there run from a source checkout, so they are
# out of scope for "does the installed SDK match its docs".
DEFAULT_DOC_GLOBS = ("README.md", "API_COMPATIBILITY.md", "docs/**/*.md", "examples/**/*.md")
DEFAULT_EXAMPLE_GLOBS = ("examples/sdk/*.py", "examples/starter/*.py")


@dataclass(frozen=True)
class Snippet:
    """One code block (or whole example file) with its source location."""

    id: str
    path: str
    line: int
    lang: str
    code: str

    @property
    def kind(self) -> str:
        if self.lang in PYTHON_LANGS:
            return "python"
        if self.lang in SHELL_LANGS:
            return "shell"
        return "other"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def blocks_from_markdown(path: Path, root: Path) -> list[Snippet]:
    """Return fenced code blocks with the 1-based line of their first code line."""

    snippets: list[Snippet] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        match = FENCE.match(lines[i])
        if not match:
            i += 1
            continue
        fence, lang = match.group(2), match.group(3).lower()
        start = i + 1
        j = start
        while j < len(lines) and not lines[j].strip().startswith(fence):
            j += 1
        code = "\n".join(lines[start:j])
        rel = _rel(path, root)
        snippets.append(Snippet(id=f"{rel}:{start + 1}", path=rel, line=start + 1, lang=lang, code=code))
        i = j + 1
    return snippets


@dataclass(frozen=True)
class Profile:
    """Which files count as docs and which as code for a given kind of repo."""

    name: str
    doc_globs: tuple[str, ...]
    code_globs: tuple[str, ...]


# The OpenMinion repo itself: its docs, plus the example programs it ships.
OPENMINION = Profile("openminion", DEFAULT_DOC_GLOBS, DEFAULT_EXAMPLE_GLOBS)
# Any project built on OpenMinion: README/docs snippets plus all of its Python.
PROJECT = Profile("project", ("*.md", "docs/**/*.md", "examples/**/*.md"), ("**/*.py",))

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "site-packages", "build", "dist",
    "__pycache__", ".tox", ".cache", ".mypy_cache", ".pytest_cache", ".openminion", ".ruff_cache",
}
MAX_FILE_BYTES = 500_000


def detect_profile(root: Path) -> Profile:
    return OPENMINION if (root / "src" / "openminion").is_dir() else PROJECT


def _matches(root: Path, pattern: str) -> list[Path]:
    out = []
    for path in root.glob(pattern):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
            continue
        if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES:
            out.append(path)
    return sorted(out)


def doc_files(root: Path, profile: Profile | None = None) -> list[Path]:
    profile = profile or detect_profile(root)
    found: set[Path] = set()
    for pattern in profile.doc_globs:
        found.update(_matches(root, pattern))
    return sorted(found)


def collect(root: Path, profile: Profile | None = None) -> list[Snippet]:
    """Collect Python and shell snippets from docs plus whole Python files."""

    profile = profile or detect_profile(root)
    seen: set[Path] = set()
    out: list[Snippet] = []
    for path in doc_files(root, profile):
        seen.add(path)
        out.extend(s for s in blocks_from_markdown(path, root) if s.kind != "other")
    for pattern in profile.code_globs:
        for path in _matches(root, pattern):
            if path in seen:
                continue
            seen.add(path)
            rel = _rel(path, root)
            code = path.read_text(encoding="utf-8", errors="replace")
            out.append(Snippet(id=f"{rel}:1", path=rel, line=1, lang="python", code=code))
    return out
