"""OpenMinion tools the DocDrift agents use to gather evidence.

Every evidence tool is declared READ_ONLY + idempotent, so the default action
policy runs it without a prompt. The one write tool (issue drafts) is left at
the default WRITE_SAFE scope, so OpenMinion asks the operator before it runs.
"""

from __future__ import annotations

import importlib
import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path

import openminion
from openminion import tool

from . import cli_check

PACKAGE_ROOT = Path(openminion.__file__).parent
MAX_OUT = 6000
SAFE_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass
class ToolContext:
    """Paths the tools are allowed to read or write. Set once by the CLI."""

    docs_root: Path = Path(".")
    out_dir: Path = Path("out")
    calls: list[str] = field(default_factory=list)


CTX = ToolContext()


def _clip(text: str) -> str:
    return text if len(text) <= MAX_OUT else text[:MAX_OUT] + f"\n... [truncated {len(text) - MAX_OUT} chars]"


def _confined(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise ValueError(f"path escapes {root}: {rel}")
    return target


def _search(root: Path, pattern: str, globs: tuple[str, ...], max_hits: int) -> str:
    if not pattern or len(pattern) > 120:
        return "pattern must be 1-120 characters"
    hits: list[str] = []
    for glob in globs:
        for path in sorted(root.rglob(glob)):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for no, line in enumerate(lines, 1):
                if pattern in line:
                    hits.append(f"{path.relative_to(root).as_posix()}:{no}: {line.strip()[:200]}")
                    if len(hits) >= max_hits:
                        return "\n".join(hits) + f"\n... stopped at {max_hits} hits"
    if hits:
        return "\n".join(hits)
    if len(pattern.split()) > 3:
        return (
            f"no matches for {pattern!r}. Source code rarely contains doc sentences: "
            "search for identifiers, setting names, error strings or numbers instead "
            "(for example 'max_length=128', '12_000', 'TASK_CONTEXT', 'timeout_seconds')."
        )
    return f"no matches for {pattern!r}"


@tool(min_scope="READ_ONLY", idempotent=True)
def cli_help(command: str) -> str:
    """Return `openminion <command> --help` from the installed CLI.

    `command` is the subcommand path without the leading `openminion`, for
    example "setup" or "config init". Use an empty string for the root help.
    """

    CTX.calls.append(f"cli_help({command!r})")
    tokens = command.split()
    if len(tokens) > 4 or not all(SAFE_TOKEN.match(t) for t in tokens):
        return "refused: only up to 4 plain subcommand words are allowed"
    info = cli_check.help_for(tuple(tokens))
    return _clip(info.raw if info.raw else "no help output")


@tool(min_scope="READ_ONLY", idempotent=True)
def inspect_symbol(dotted_path: str) -> str:
    """Describe an object in the installed `openminion` package.

    `dotted_path` looks like "openminion.Agent" or
    "openminion.Agent.run". Returns its kind, signature, docstring and
    public members.
    """

    CTX.calls.append(f"inspect_symbol({dotted_path!r})")
    if not dotted_path.startswith("openminion"):
        return "refused: only openminion.* symbols can be inspected"
    parts = dotted_path.split(".")
    obj = None
    for i in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:i]))
        except ImportError:
            continue
        try:
            for attr in parts[i:]:
                obj = getattr(obj, attr)
        except AttributeError as exc:
            return f"not found: {exc}"
        break
    if obj is None:
        return f"not found: cannot import any prefix of {dotted_path}"
    lines = [f"kind: {type(obj).__name__}"]
    try:
        lines.append(f"signature: {inspect.signature(obj)}")
    except (TypeError, ValueError):
        pass
    try:
        lines.append(f"defined in: {Path(inspect.getfile(obj)).relative_to(PACKAGE_ROOT.parent).as_posix()}")
    except (TypeError, ValueError):
        pass
    doc = inspect.getdoc(obj)
    if doc:
        lines.append("doc:\n" + doc[:2000])
    members = [n for n in dir(obj) if not n.startswith("_")]
    if members and not isinstance(obj, (str, int, float)):
        lines.append("public members: " + ", ".join(members[:80]))
    return _clip("\n".join(lines))


@tool(min_scope="READ_ONLY", idempotent=True)
def search_package_source(text: str, max_hits: int = 25) -> str:
    """Find a literal string in the installed openminion package's Python source.

    Returns `path:line: code` hits, with paths relative to site-packages.
    """

    CTX.calls.append(f"search_package_source({text!r})")
    limit = max(1, min(max_hits, 60))
    result = _search(PACKAGE_ROOT, text, ("*.py",), limit)
    grouped = _underscore_number(text)
    if grouped and grouped != text:
        # Docs write 12000; Python source often writes 12_000.
        result += f"\n--- also searched {grouped!r} ---\n" + _search(PACKAGE_ROOT, grouped, ("*.py",), limit)
    return _clip(result)


def _underscore_number(text: str) -> str | None:
    digits = text.replace(",", "").replace("_", "")
    if not digits.isdigit() or len(digits) < 4:
        return None
    return f"{int(digits):_}"


@tool(min_scope="READ_ONLY", idempotent=True)
def read_package_file(path: str, start_line: int = 1, end_line: int = 80) -> str:
    """Read a line range from a file inside the installed openminion package.

    `path` is relative to the package root, for example
    "modules/llm/config.py". At most 200 lines are returned.
    """

    CTX.calls.append(f"read_package_file({path!r}, {start_line}, {end_line})")
    try:
        target = _confined(PACKAGE_ROOT, path.removeprefix("openminion/"))
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except (ValueError, OSError) as exc:
        return f"cannot read: {exc}"
    start = max(1, start_line)
    end = min(len(lines), end_line, start + 199)
    return _clip("\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1)))


@tool(min_scope="READ_ONLY", idempotent=True)
def search_repo_checkout(text: str, max_hits: int = 25) -> str:
    """Find a literal string anywhere in the OpenMinion source checkout (docs, tests, scripts).

    Use this to tell whether something the docs mention lives only in the
    repository's test suite or maintainer scripts rather than the package.
    """

    CTX.calls.append(f"search_repo_checkout({text!r})")
    return _clip(_search(CTX.docs_root, text, ("*.py", "*.md", "*.toml", "*.json", "Makefile"), max(1, min(max_hits, 60))))


@tool(min_scope="READ_ONLY", idempotent=True)
def read_doc(path: str, start_line: int = 1, end_line: int = 80) -> str:
    """Read a line range from a file in the OpenMinion source checkout, e.g. "docs/getting-started.md"."""

    CTX.calls.append(f"read_doc({path!r}, {start_line}, {end_line})")
    try:
        target = _confined(CTX.docs_root, path)
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except (ValueError, OSError) as exc:
        return f"cannot read: {exc}"
    start = max(1, start_line)
    end = min(len(lines), end_line, start + 199)
    return _clip("\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1)))


@tool(description="Save a GitHub issue draft for one confirmed doc drift finding to the local out/issues folder.")
def write_issue_draft(finding_id: str, title: str, body_markdown: str) -> str:
    """Write out/issues/<finding_id>.md. Nothing is posted to GitHub."""

    CTX.calls.append(f"write_issue_draft({finding_id!r})")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", finding_id):
        return "refused: finding_id must be 1-40 letters, digits, '-' or '_'"
    target = CTX.out_dir / "issues" / f"{finding_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# {title.strip()}\n\n{body_markdown.strip()}\n", encoding="utf-8")
    return f"saved {target.as_posix()}"


EVIDENCE_TOOLS = [
    cli_help,
    inspect_symbol,
    search_package_source,
    read_package_file,
    search_repo_checkout,
    read_doc,
]
