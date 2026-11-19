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
    lines = path.read_text(encoding="utf-8").splitlines()
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


def doc_files(root: Path, doc_globs=DEFAULT_DOC_GLOBS) -> list[Path]:
    found: set[Path] = set()
    for pattern in doc_globs:
        found.update(p for p in root.glob(pattern) if p.is_file())
    return sorted(found)


def collect(root: Path, doc_globs=DEFAULT_DOC_GLOBS, example_globs=DEFAULT_EXAMPLE_GLOBS) -> list[Snippet]:
    """Collect Python and shell snippets from docs plus whole example programs."""

    seen: set[Path] = set()
    out: list[Snippet] = []
    for pattern in doc_globs:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            out.extend(s for s in blocks_from_markdown(path, root) if s.kind != "other")
    for pattern in example_globs:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            rel = _rel(path, root)
            out.append(Snippet(id=f"{rel}:1", path=rel, line=1, lang="python", code=path.read_text(encoding="utf-8")))
    return out
